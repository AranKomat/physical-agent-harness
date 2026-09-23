# Safety And Evidence Boundaries

- `core.actions.Basis` is the common current action/geometry lineage. FrameRefs,
  task facts and planner requests retain it rather than substituting confidence.
- Existing sensor Snapshot and episodic Cutoff records are input/history adapters,
  not competing current action authorities. Their clocks cannot be conflated.
- Source bytes, camera, frame, episode, localization epoch, geometry revision and
  actual availability must agree. A paused simulator does not make late inference
  available at an earlier decision boundary.
- GLM output, cached labels, predicted goals and learned completion are advisory.
  Physical identity, clearance, stopping and task success require their own checks.
- Unknown swept collision, command completion or stopped state rejects or latches
  the executor. It must not trigger a silent controller swap or retry.
- All physics-advancing operations count toward action budgets, including settling.
  Observation must not hide simulator steps.
- Historical imagery remains historical. No future frames, privileged object poses,
  challenge-only extra sensors or pre-mapped benchmark knowledge enter decisions.
- Provider calls require explicit opt-in, bounded transport and durable accounting.
  Incomplete reservations stay held; a thread cannot kill a hung native callback.

The same rules apply to classical, neural and mixed controllers. Existing
simulator-only exploratory exceptions remain labeled experiments, not default
permissions. Offline tests protect software contracts, not real-robot safety.
