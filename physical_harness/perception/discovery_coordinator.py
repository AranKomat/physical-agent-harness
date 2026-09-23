from __future__ import annotations

from physical_harness.core.actions import Basis, digest
from physical_harness.core.events import BoundaryEvent
from physical_harness.perception.contracts import DiscoveryRequest, RegionRef
from physical_harness.perception.keyframes import ViewSample


class DiscoveryCoordinator:
    """Main-thread owner for novelty -> async semantics -> historical inventory/events.

    No method commands motion, resets a policy, changes an IdentityLedger or
    mutates current metric world state. Main-thread poll is the only state writer.
    """
    def __init__(self, *, journal, keyframes, worker, inventory, executive_scheduler,
                 discovery_timeout_s=20.):
        from physical_harness.core.actions import number
        number(discovery_timeout_s, low=.01, high=300)
        self.journal, self.keyframes, self.worker = journal, keyframes, worker
        self.inventory, self.scheduler, self.timeout = inventory, executive_scheduler, discovery_timeout_s
        self.rooms_seen: set[str] = set()

    def observe(self, sample: ViewSample, *, now: float, task: str, task_revision: str,
                regions: tuple[RegionRef, ...] = (), room_id: str | None = None):
        reasons = self.keyframes.ingest(sample, now=now)
        if not reasons:
            return None
        frames = self.keyframes.select(sample.frame, now=now)
        selected_ids = {f.asset_id for f in frames}
        selected_regions = tuple(r for r in regions if r.frame_id in selected_ids)
        known, summary = self.inventory.known_summary(current=sample.frame.basis, now=now, task_revision=task_revision)
        first_room = room_id is not None and room_id not in self.rooms_seen
        request_id = digest([sample.frame.basis.episode, task_revision, [f.content_sha256 for f in frames],
                             sample.frame.basis.fingerprint, reasons])[:32]
        request = DiscoveryRequest(request_id, task, task_revision, sample.frame.basis, frames,
                                   selected_regions, known, self.inventory.revision, now, now+self.timeout,
                                   reasons, "room_initial" if first_room else "delta", known_summary_json=summary)
        accepted = self.worker.submit(request)
        self.journal.put("embodied_sampling", request_id, {"request_id": request_id, "accepted": accepted,
                         "buffer": self.keyframes.report(), "selected_frame_ids": list(selected_ids),
                         "region_count": len(selected_regions), "task_revision": task_revision})
        if accepted:
            self.keyframes.acknowledge_submission(frames)
            if first_room:
                self.rooms_seen.add(room_id)
            return request
        return None

    def poll(self, *, current: Basis, now: float, task_revision: str):
        if current.episode != self.journal.episode:
            raise PermissionError("Foreign discovery consumer")
        delivered = []
        for completion in self.worker.poll():
            result = completion.result
            if result is None:
                delivered.append({"request_id": completion.request_id, "error": completion.error_type})
                continue
            if result.request.current.sim_time > current.sim_time or result.completed_wall > now:
                raise PermissionError("Result isn't available at this consumer cutoff")
            for frame in result.request.frames:
                frame.available(current, now)
            item_ids = self.inventory.accept(result, received_wall=now, current_task_revision=task_revision)
            if result.request.task_revision == task_revision:
                for a in result.attention:
                    update = next(u for u in result.updates if u.local_id == a.local_id)
                    source = next(f for f in result.request.frames if f.asset_id == update.frame_id)
                    event = BoundaryEvent("discovery:"+result.request.id+":"+a.local_id,
                                          "relevant_discovery", source.basis, now, task_revision,
                                          source.basis.evidence_ids, a.significance)
                    self.scheduler.add(event, active_task_revision=task_revision)
            delivered.append({"request_id": completion.request_id, "items": item_ids,
                              "historical_only": True, "native_actions": 0})
        return tuple(delivered)
