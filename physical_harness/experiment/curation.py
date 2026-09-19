"""Live crop/place curation from supplied detections; this is not a detector or ReID model."""
from __future__ import annotations

from dataclasses import asdict

from ..context_rich import CoverageNote
from ..memory.media import make_crop
from ..memory.schemas import Card, stable_id
from .native import Observation
from .validation import dumps


class VisualCurator:
    def __init__(self, memory, blobs, *, minimum_interval_s: float = 10):
        self.memory, self.blobs = memory, blobs
        self.minimum_interval_s = minimum_interval_s
        self.last: dict[tuple[str, str], float] = {}

    def ingest(self, observation: Observation, assets_by_camera: dict) -> list[str]:
        if observation.episode != self.memory.episode_id:
            raise ValueError("Foreign curation episode")
        created = []
        for detection in observation.boxes:
            parent = assets_by_camera[detection.camera]
            if parent.observation_id != observation.id or parent.observed_end != observation.sim_time:
                raise ValueError("Detection is detached from its source observation")
            key = ("entity", detection.entity)
            if observation.sim_time - self.last.get(key, float("-inf")) < self.minimum_interval_s:
                continue
            crop = make_crop(self.memory, parent.asset_id, detection.box, self.blobs.put,
                             self.memory.cutoff(observation.sim_time))
            card_id = stable_id("entity-view", [observation.id, detection.entity, crop.asset_id])
            # Candidate IDs are kept as ambiguous retrieval aliases, never silently merged.
            aliases = tuple(dict.fromkeys((detection.entity, *detection.identity_candidates)))
            summary = (f"Observed appearance: {detection.label}. Tracker ID {detection.entity}. "
                       f"Identity candidates: {list(detection.identity_candidates)}. "
                       "This crop does not establish containment or task success.")
            self.memory.add_card(Card(
                card_id, observation.episode, "entity_view", card_id, "object_sighting",
                observation.sim_time, observation.sim_time, (crop.asset_id, parent.asset_id),
                aliases, (observation.place_id,) if observation.place_id else (), summary))
            self.last[key] = observation.sim_time
            created.append(card_id)
        if observation.place_id:
            key = ("place", observation.place_id)
            if observation.sim_time - self.last.get(key, float("-inf")) >= self.minimum_interval_s:
                parent = assets_by_camera.get("head", next(iter(assets_by_camera.values())))
                card_id = stable_id("place-view", [observation.id, observation.place_id])
                summary = (f"View associated with {observation.place_id}. "
                           "Description is advisory, not metric geometry: "
                           + (observation.place_description or "No description supplied."))
                self.memory.add_card(Card(
                    card_id, observation.episode, "place_view", card_id, "place_entered",
                    observation.sim_time, observation.sim_time, (parent.asset_id,), (),
                    (observation.place_id,), summary))
                self.last[key] = observation.sim_time
                created.append(card_id)
        return created


def validated_coverage(observation: Observation, evidence_by_camera: dict, world) -> list[CoverageNote]:
    notes = []
    for scan in observation.coverage:
        ids = tuple(evidence_by_camera[c] for c in scan.cameras)
        for identifier in ids:
            evidence = world._evidence(identifier)
            if evidence["kind"] != "perception" or evidence["sim_time"] != observation.sim_time:
                raise ValueError("Coverage must use same-episode, same-capture visual evidence")
        coverage = "high" if scan.measured_fraction >= .9 else (
            "medium" if scan.measured_fraction >= .5 else "low")
        notes.append(CoverageNote(
            scan.scope, observation.sim_time, coverage, scan.result, ids,
            "Advisory scoped non-detection, not proof of absence elsewhere. "
            + dumps(asdict(scan)).decode()))
    return notes
