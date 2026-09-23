# Integration Status

| Adapter | Status | Missing qualification |
| --- | --- | --- |
| BEHAVIOR/R1Pro | Public matched driver and private native experiments | Reliable task completion, motor, clearance/localization/stopping |
| SAM 3.1 | Corrected private streaming path; public offline adapter | Similar-object loss/reacquisition, live source association |
| GLM discovery | Retained inventory comparison; strict transport | New delta prompt and live inventory publication |
| GraspGenX | Lazy worker/client and checkpoint guards | Installed qualified assets, current legal geometry and native execution |
| cuRobo | Pinned API adapter, mock tests | Robot/tool config, collision world, independent FK/swept checks |
| Frozen VLA | Several tested interfaces; optional specialist | Reliable broad motor competence; checkpoint/interface fit |

Vendor-specific code belongs under `physical_harness.integrations`, not a new
versioned runtime. Task-specific native drivers stay under `experiments/behavior`.
No adapter is automatically enabled by import or package installation.

The new single-GPU host has code and retained evidence but does not yet have all
model weights, policy runtimes or simulator assets restored. Host-specific paths,
credentials, provisioning receipts and restricted images remain in the private lab.

Current templates are organized by `configs/behavior`, `models`, `planners`,
`planning`, `qualifications`, and `reasoning`. They are templates, not approved
deployments. Synthetic doctor and SAM prefix-replay configs live in
`experiments/fixtures/configs`, outside the deployment templates.
