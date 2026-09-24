"""Source-bound SAM surface proposal; no identity or motion authority."""

import hashlib
import io
import time
from pathlib import Path

import numpy as np


class SAMTransitTarget:
    """Pinned tracker selection for one exploratory probe; never reacquire silently."""

    def __init__(self, root, *, session, epoch, generation, tracker_id):
        self.root = root
        self.session, self.epoch = session, epoch
        self.generation, self.tracker_id = generation, tracker_id
        self.receipts = []

    def __call__(self, frame, row, output):
        obs = frame["obs"]
        if (obs.stamp.session, obs.stamp.epoch) != (self.session, self.epoch):
            raise ValueError("SAM selection belongs to another episode")
        proposal = surface_target(frame, row["sam_target_result"], self.root,
                                  generation=self.generation, tracker_id=self.tracker_id,
                                  now=time.monotonic())
        self.receipts.append(proposal)
        return np.asarray(proposal["surface_median_base_m"])


def surface_target(frame, result, root, *, generation, tracker_id, now):
    """Consume one current SAM archive without substituting an older frame/ID.

    Require a dominant connected surface (80% of valid support); never average
    disconnected surfaces. The caller binds the tracker generation to its task.
    """
    obs, depth, k = frame["obs"], frame["depth"], np.asarray(frame["k"])
    expected = dict(stamp=obs.stamp.model_dump(), rgb_id=obs.rgb["head"].id,
                    depth_id=obs.depth["head"].id, observed_at=obs.observed_at)
    if any(result.get(key) != value for key, value in expected.items()):
        raise ValueError("Detached SAM source")
    if (result.get("motion_authorized") is not False
            or type(generation) is not int or type(tracker_id) is not int
            or result.get("generation") != generation):
        raise ValueError("Invalid SAM authority or tracker generation")
    clocks = [obs.observed_at, result["published_at"], result["dequeued_at"],
              result["ready_at"], result["archive_finished_at"], now]
    if (not np.isfinite(clocks).all() or any(a > b for a, b in zip(clocks, clocks[1:]))
            or now - obs.observed_at > 2.):
        raise ValueError("Stale or noncausal SAM result")
    root = Path(root).resolve()
    path = (root / result["artifact"]).resolve()
    if path.parent != root or path.name != result["artifact"] or path.suffix != ".npz":
        raise ValueError("Unsafe SAM artifact")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != result["sha256"]:
        raise ValueError("Changed SAM archive")
    with np.load(io.BytesIO(content), allow_pickle=False) as archive:
        masks, ids, labels = archive["masks"], archive["ids"], archive["labels"]
        if (masks.dtype != np.bool_ or masks.shape != (len(ids), *depth.shape)
                or ids.ndim != 1 or ids.dtype.kind not in "iu" or len(ids) > 32
                or len(set(ids.tolist())) != len(ids) or ids.tolist() != result["ids"]
                or labels.shape != masks.shape or labels.dtype.kind not in "iu"):
            raise ValueError("Invalid SAM masks/IDs/partitions")
        selected = np.flatnonzero(ids == tracker_id)
        if len(selected) != 1:
            raise ValueError("Selected target lost")
        mask, partition = masks[selected[0]], labels[selected[0]]
        valid = mask & np.isfinite(depth) & (depth > 0) & (depth <= 10)
        if ((partition < 0).any() or not np.array_equal(partition > 0, valid)
                or valid.sum() < 16 or valid.sum() < .8 * mask.sum()):
            raise ValueError("Insufficient or split target surface")
        patch_ids, counts = np.unique(partition[valid], return_counts=True)
        largest = int(np.argmax(counts))
        fraction = float(counts[largest] / valid.sum())
        if fraction < .8:
            raise ValueError("Ambiguous split target surface")
        patch_id = int(patch_ids[largest])
        valid = valid & (partition == patch_id)
    if (k.shape != (3, 3) or not np.isfinite(k).all() or k[0, 0] <= 0
            or k[1, 1] <= 0 or not np.allclose(k[2], [0, 0, 1])):
        raise ValueError("Invalid intrinsics")
    from experiments.behavior.exploratory_transit import _rigid

    transform = _rigid(frame["extrinsic"])
    v, u = np.nonzero(valid)
    z = depth[v, u]
    camera = np.median(np.column_stack(((u-k[0, 2])*z/k[0, 0],
                                       (v-k[1, 2])*z/k[1, 1], z)), axis=0)
    point = (transform @ np.r_[camera, 1.])[:3]
    if (np.linalg.norm(point[:2]) < .10
            or min(np.linalg.norm(point-np.asarray(obs.proprio)[i:i+3])
                   for i in (17, 42)) < .18):
        raise ValueError("Near-hand or near-base target ambiguity")
    return dict(surface_median_base_m=point.tolist(), support=int(valid.sum()),
                patch_id=patch_id, dominant_support_fraction=fraction,
                generation=generation, tracker_id=tracker_id, **expected,
                mask_sha256=result["sha256"], consumed_at=now,
                motion_authorized=False, identity_verified=False,
                scope="visible_surface_candidate_not_object_center_or_clearance")
