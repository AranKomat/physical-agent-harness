"""Optional GraspGenX adapter. No upstream import, download, or GPU use on import.

Audited API: NVlabs/GraspGenX b9429097728cb1c430dd78b92edf17ba318aad03
GraspGenXSampler.run_inference(object_pc, sampler, ...). R1Pro gripper assets,
frame transforms, checkpoints and licenses require separate local provisioning.
"""
from __future__ import annotations

import hashlib
import importlib
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .geometry import ObjectCloud, compose_tcp
from .types import Gripper, Intent, Parameters, Pose, Proposal, Verb, integer, number, text

AUDITED_REVISION = "b9429097728cb1c430dd78b92edf17ba318aad03"


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_files(root: Path, manifest: dict[str, str]) -> None:
    """Manifest generated after authorized provisioning, not proof of origin."""
    if not manifest:
        raise ValueError("Nonempty artifact hashes required")
    root = root.resolve(strict=True)
    for rel, expected in manifest.items():
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts or not p.parts:
            raise ValueError("Manifest path escapes root")
        path = root/p
        if path.is_symlink() or root not in path.resolve(strict=True).parents:
            raise ValueError("Manifest symlink/path escape")
        if len(expected) != 64 or _sha_file(path) != expected:
            raise ValueError("Artifact hash mismatch: "+rel)
        # Git-LFS pointers must not be mistaken for downloaded weights/assets.
        with path.open("rb") as stream:
            if stream.read(64).startswith(b"version https://git-lfs.github.com/spec"):
                raise ValueError("Unmaterialized Git-LFS pointer: "+rel)


@dataclass(frozen=True)
class LocalAssets:
    source: Path
    checkpoint_root: Path
    gripper_root: Path
    assets_dir: Path
    gripper_name: str
    generator_file: str
    discriminator_file: str
    source_revision: str = AUDITED_REVISION

    def __post_init__(self):
        for key in ("source", "checkpoint_root", "gripper_root", "assets_dir"):
            if not isinstance(getattr(self, key), Path):
                raise ValueError("Explicit local paths required")
        for key in ("gripper_name", "generator_file", "discriminator_file", "source_revision"):
            text(getattr(self, key))
        for name in (self.gripper_name, self.generator_file, self.discriminator_file):
            if Path(name).name != name or name in {".", ".."}:
                raise ValueError("Simple local asset names required")


class GraspGenXAdapter:
    """Proposal-only adapter; model execution is separate from motor control.

    Construct with an explicitly loaded sampler. infer can be injected for tests.
    It is the *same audited upstream callable*, not a fabricated network endpoint.
    Run the loaded adapter inside a supervised, no-egress worker for hard timeouts.
    """
    def __init__(self, sampler, gripper: Gripper, *, infer, revision: str,
                 model_digest: str, gripper_name: str, allow_inference: bool = False,
                 clock=time.monotonic):
        if type(allow_inference) is not bool:
            raise ValueError("Explicit inference permission required")
        if not callable(infer) or not callable(clock):
            raise ValueError("Inference callable and clock required")
        self.sampler, self.gripper, self.infer = sampler, gripper, infer
        self.revision, self.model_digest = text(revision), text(model_digest)
        self.gripper_name = text(gripper_name)
        self.allowed, self.clock = allow_inference, clock
        self.calls = 0
        self.wall_s = 0.

    def propose(self, cloud: ObjectCloud, *, deadline: float, num_grasps: int = 64,
                top_k: int = 8) -> tuple[Proposal, ...]:
        if not self.allowed:
            raise PermissionError("Grasp inference is disabled")
        number(deadline, low=0)
        integer(num_grasps, low=1, high=256)
        integer(top_k, low=1, high=min(num_grasps, 32))
        if self.clock() >= deadline:
            raise TimeoutError("Grasp request deadline")
        import numpy as np
        points = np.asarray(cloud.points, dtype=np.float32)
        if len(points) < 32:
            raise ValueError("Insufficient observed points for configured grasp backend")
        start = self.clock()
        self.calls += 1
        try:
            # Single generation attempt; no hidden retry budget or TensorRT fallback.
            poses, scores = self.infer(points, self.sampler, grasp_threshold=-1.0,
                                       num_grasps=num_grasps, topk_num_grasps=top_k,
                                       min_grasps=1, max_tries=1, remove_outliers=False)
        finally:
            self.wall_s += self.clock()-start
        if self.clock() >= deadline:
            raise TimeoutError("Discard late grasp proposals")
        def array(value):
            if hasattr(value, "detach"):
                value = value.detach().cpu().numpy()
            return np.asarray(value)
        poses, scores = array(poses), array(scores)
        if poses.size == 0 and scores.size == 0:
            return ()
        if poses.ndim != 3 or poses.shape[1:] != (4, 4) or scores.shape != (len(poses),):
            raise ValueError("Unexpected GraspGenX output schema")
        if len(poses) > num_grasps or not np.isfinite(poses).all() or not np.isfinite(scores).all():
            raise ValueError("Invalid/unbounded grasp model output")
        output = []
        for i in sorted(range(len(scores)), key=lambda n: (-float(scores[n]), n))[:top_k]:
            grasp = Pose(cloud.basis.frame, tuple(float(v) for v in poses[i].ravel()))
            tcp = compose_tcp(grasp, self.gripper.grasp_to_tcp)
            output.append(Proposal(Intent(Verb.GRASP, cloud.entity, cloud.part), cloud.basis,
                                   Parameters(tcp, opening_m=self.gripper.max_opening_m),
                                   self.gripper.fingerprint, "GraspGenX",
                                   self.revision+":"+self.model_digest, cloud.evidence_ids,
                                   float(scores[i]), "graspgenx_discriminator_uncalibrated"))
        return tuple(output)


def load_local(assets: LocalAssets, gripper: Gripper, *,
               checkpoint_manifest: dict[str, str], gripper_manifest: dict[str, str],
               allow_inference: bool = False, licenses_accepted: bool = False,
               expected_gripper_fingerprint: str) -> GraspGenXAdapter:
    """Explicit worker startup only; never call this in the executive process.

    The audited upstream package auto-downloads at import when paths are absent.
    We verify populated directories and files, set BOTH upstream overrides first,
    and use an explicitly pinned source checkout. A no-egress OS container remains
    required for defense in depth
    environment variables are not a network sandbox.
    """
    if allow_inference is not True or licenses_accepted is not True:
        raise PermissionError("Inference and artifact-license acceptance must be explicit")
    if assets.source_revision != AUDITED_REVISION:
        raise ValueError("Unreviewed GraspGenX revision; audit before updating this adapter")
    if expected_gripper_fingerprint != gripper.fingerprint:
        raise PermissionError("R1Pro gripper calibration/configuration mismatch")
    head = subprocess.check_output(["git", "-C", str(assets.source), "rev-parse", "HEAD"],
                                   text=True, timeout=10).strip()
    dirty = subprocess.check_output(["git", "-C", str(assets.source), "status", "--porcelain",
                                     "--untracked-files=no"], text=True, timeout=10).strip()
    if head != assets.source_revision or dirty:
        raise PermissionError("Clean pinned GraspGenX source required")
    for path in (assets.source, assets.checkpoint_root, assets.gripper_root, assets.assets_dir):
        if not path.is_dir() or not any(path.iterdir()):
            raise FileNotFoundError("Provision local assets before upstream import: "+str(path))
    required = {"gen/config.yaml", "dis/config.yaml",
                "gen/"+assets.generator_file, "dis/"+assets.discriminator_file}
    if not required <= checkpoint_manifest.keys():
        raise ValueError("Manifest must cover exact selected model/config files")
    config_rel = "x_grippers/"+assets.gripper_name+"/config.json"
    # Asset manifest is relative to assets_dir and must include every gripper file.
    if config_rel not in gripper_manifest:
        raise ValueError("Manifest lacks selected gripper config")
    selected = assets.assets_dir/"x_grippers"/assets.gripper_name
    if not selected.is_dir():
        raise FileNotFoundError("Selected gripper assets missing")
    expected_files = {str(p.relative_to(assets.assets_dir)) for p in selected.rglob("*") if p.is_file()}
    if not expected_files <= gripper_manifest.keys():
        raise ValueError("Gripper manifest does not cover all selected meshes/URDFs")
    from .types import digest
    if digest(gripper_manifest) != gripper.asset_digest:
        raise PermissionError("Loaded gripper manifest does not match calibrated profile")
    verify_files(assets.checkpoint_root, checkpoint_manifest)
    verify_files(assets.assets_dir, gripper_manifest)
    if "graspgenx" in sys.modules:
        raise RuntimeError("Use a clean dedicated worker; upstream already imported")
    os.environ["GRASPGENX_CHECKPOINT_DIR"] = str(assets.checkpoint_root.resolve())
    os.environ["GRASPGENX_GRIPPER_CFG_DIR"] = str(assets.gripper_root.resolve())
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, str(assets.source.resolve()))
    upstream = importlib.import_module("graspgenx.grasp_server")
    loader = importlib.import_module("graspgenx.utils.checkpoint_io")
    cfg = loader.load_model_cfg(str(assets.checkpoint_root/"gen"),
                                str(assets.checkpoint_root/"dis"),
                                assets.generator_file, assets.discriminator_file)
    sampler = upstream.GraspGenXSampler(cfg, assets.gripper_name,
                                       assets_dir=str(assets.assets_dir), use_tensorrt=False)
    return GraspGenXAdapter(sampler, gripper, infer=upstream.GraspGenXSampler.run_inference,
                           revision=assets.source_revision,
                           model_digest=digest(checkpoint_manifest), gripper_name=assets.gripper_name,
                           allow_inference=True)
