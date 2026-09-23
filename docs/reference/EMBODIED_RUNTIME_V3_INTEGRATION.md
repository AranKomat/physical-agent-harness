# Embodied Runtime V3 Integration

Integrated on 2026-09-23 into the actual checkout at `10b58fe`, from
`physical_agent_harness_embodied_v3_20260923.zip`. The bundle reviewed `1077839`;
all 18 pinned reused-interface Git blob hashes still matched. Its guarded
installer verified payload SHA-256 values and added 37 files without replacing
existing source. The original bundle, installer, manifest, and author validation
report remain in the private lab's incoming directory.

## Local Validation

| Check | Result |
| --- | --- |
| New V3 suite in the actual checkout | 174 passed |
| Full repository suite, including V3 | 1,408 passed |
| Separate bundle installer suite | 22 passed |
| Repository Ruff check | Passed |
| Synthetic CLI | Passed; zero model calls and zero native robot actions |
| New host, V3 suite and repository Ruff | 174 passed; Ruff clean |
| Private SAM streaming/GLM/LocateAnything regression subset | 25 passed |

Tests were run with `python -m pytest` from the repository root. Installer tests
are not included in the 1,408 repository count. The demo executes one synthetic
counted step through the existing executor, reports external verification still
required, leaves zero unresolved robot owners, and keeps all six macros
unpromoted. Mock planner tests do not qualify cuRobo or R1Pro collision geometry.

Merge corrections were limited to Ruff import ordering and an explicit failure
when the demo's discovery request is not admitted. README links and this report
were added. The archived installer manifest describes the original payload,
not these lint/integration edits; do not reapply it over edited files or weaken
its conflict checks.

## Reconciliation With Recent Perception Work

The bundle predates the latest discovery reports, which remain unchanged:

- [Matched GLM/VLX inventory](../experiments/2026-09-23/GLM_VLX_MATCHED_INVENTORY_20260923.md): GLM is a
  candidate for occasional semantic discovery, not a qualified source of poses.
- [VLX-to-SAM handoff](../experiments/2026-09-23/VLX_BLIND_SAM_HANDOFF_20260923.md): bounded box-seeded
  tracking passed, but identity confusions and missing occlusion qualification
  remain. The corrected private `sam31_streaming.py` was not changed or replaced.
- [LocateAnything smoke test](../experiments/2026-09-23/LOCATEANYTHING_SMOKE_20260923.md): fast description
  grounding is not a replacement for category inventory; its failure cases and
  non-commercial license restrictions remain relevant.

V3 uses normalized 0..1 xyxy proposals, while the latest GLM inventory test used
native pixel coordinates. Those saved packets are not interchangeable. A replay
bridge must convert using the recorded source dimensions and retain provenance;
it must not silently guess coordinate conventions or reuse an old box on a new
frame. V3's bounded delta schema and prompt have not yet been evaluated with the
live GLM endpoint. Earlier inventory accuracy/latency cannot be claimed for them.

No paid-call limit, unresolved billing hold, motion gate, tracking reset/session
rule, or existing memory default changed. No live worker was enabled and no
planner, policy, or segmentation weights were downloaded by this integration.

## Next Qualification

Start with no-motion replay of retained packets through the new discovery,
historical inventory, and compact-context boundaries. Keep the corrected SAM
worker and explicitly validate source-frame/camera/session association. Compare
the new delta prompt only with a separately authorized model-call budget.

Native paths still require calibrated R1Pro codecs, current collision scenes,
localization, stopping checks, and independent verification. This merge provides
opt-in software adapters, not a deployed closed-loop V3 runtime or evidence of
task-level improvement. The handoff's experiment sequence is guidance, not an
authorization to launch new inference or motion.
