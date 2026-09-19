"""Resolve evidence to actual pixels, not filenames pretending to be model inputs."""
from __future__ import annotations

import base64
import hashlib
from dataclasses import asdict, dataclass
from io import BytesIO

from PIL import Image

from ..memory.schemas import Cutoff
from .validation import number, text


@dataclass(frozen=True)
class ImageInput:
    id: str
    episode: str
    uri: str
    captured_at: float
    camera: str
    width: int
    height: int
    data: bytes
    role: str = "current"
    parent_id: str = ""

    def metadata(self) -> dict:
        return {k: v for k, v in asdict(self).items() if k != "data"}

    def data_url(self) -> str:
        media = "image/png" if self.uri.endswith(".png") else "image/jpeg"
        return f"data:{media};base64," + base64.b64encode(self.data).decode("ascii")


def image_geometry(data: bytes) -> tuple[int, int, str]:
    if not isinstance(data, bytes) or not data or len(data) > 16_000_000:
        raise ValueError("Bounded nonempty image bytes required")
    with Image.open(BytesIO(data)) as image:
        if image.format not in {"PNG", "JPEG"} or image.width * image.height > 16_000_000:
            raise ValueError("Only bounded PNG/JPEG images supported")
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError("Animated images are not supported")
        image.load()
        return image.width, image.height, ".png" if image.format == "PNG" else ".jpg"


class ImageResolver:
    def __init__(self, world, blobs, memory=None):
        self.world, self.blobs, self.memory = world, blobs, memory

    def current(self, identifier: str, now: float, *, role: str = "current",
                max_age_s: float | None = None) -> ImageInput:
        evidence = self.world._evidence(text(identifier))
        at = number(evidence["sim_time"])
        age = number(now) - at
        if evidence["kind"] != "perception" or age < 0:
            raise ValueError("Image requires nonfuture observational evidence")
        if max_age_s is not None and age > number(max_age_s):
            raise ValueError("Image evidence is stale")
        from .validation import loads
        meta = loads(evidence["payload"])
        if meta.get("media_type") != "image" or not isinstance(meta.get("camera"), str):
            raise ValueError("Evidence is not a registered image")
        data = self.blobs.read(evidence["uri"])
        w, h, _ = image_geometry(data)
        if [w, h] != [meta.get("width"), meta.get("height")]:
            raise ValueError("Evidence image dimensions changed")
        return ImageInput(identifier, self.world.episode, evidence["uri"], at,
                          meta["camera"], w, h, data, role)

    def historical(self, asset_id: str, cutoff: Cutoff) -> ImageInput:
        if self.memory is None or cutoff.episode_id != self.world.episode:
            raise ValueError("Historical image requires matching memory episode")
        asset = self.memory.asset(asset_id, cutoff)
        if asset.kind not in {"image", "crop"}:
            raise ValueError("Only historical still images are sent to models")
        data = self.memory.read_asset(asset_id, cutoff)
        w, h, _ = image_geometry(data)
        if (w, h) != (asset.width, asset.height):
            raise ValueError("Historical image geometry mismatch")
        return ImageInput(asset_id, asset.episode_id, asset.uri, asset.observed_end,
                          asset.camera, w, h, data, "historical", asset.parent_id)

    def context(self, context: dict, now: float, cutoff: Cutoff | None = None) -> list[ImageInput]:
        if context.get("episode") != self.world.episode:
            raise ValueError("Foreign context episode")
        result = []
        for entry in context.get("current_images", context.get("images", [])):
            image = self.current(entry["id"], now)
            if entry["uri"] != image.uri or entry["sim_time"] != image.captured_at:
                raise ValueError("Context image descriptor was altered")
            result.append(image)
        if "episodic_memory" in context:
            if cutoff is None:
                raise ValueError("Historical imagery requires a recorded causal cutoff")
            for entry in context["episodic_memory"].get("images", []):
                image = self.historical(entry["asset_id"], cutoff)
                if entry["uri"] != image.uri:
                    raise ValueError("Historical URI was altered")
                result.append(image)
        return result

    def validate_after(self, identifier, request, now: float, after_floor: float) -> bool:
        try:
            if identifier not in request.after_evidence_ids:
                return False
            image = self.current(identifier, now, max_age_s=5)
            return image.captured_at >= after_floor
        except (ValueError, OSError):
            return False


def validate_images(images: list[ImageInput], episode: str, *, max_images: int,
                    max_pixels: int) -> None:
    if len(images) > max_images or sum(i.width * i.height for i in images) > max_pixels:
        raise ValueError("Image count/pixel budget exceeded")
    ids = set()
    for image in images:
        if image.id in ids or image.episode != episode:
            raise ValueError("Duplicate image ID or foreign image")
        ids.add(image.id)
        if hashlib.sha256(image.data).hexdigest() != image.uri.split(".")[0]:
            raise ValueError("Image bytes differ from source hash")
        w, h, _ = image_geometry(image.data)
        if (w, h) != (image.width, image.height):
            raise ValueError("Image metadata differs from pixels")
