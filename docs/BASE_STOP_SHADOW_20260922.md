# Base Stop Shadow: 2026-09-22

## Scope and Method

Offline analysis of retained simulator head-depth captures from the r2 diagnostic: 384 policy actions followed by 60 zero-base holds. No new motion, inference, API calls, or oracle state reads were performed. This report contains no private paths or asset contents.

Each predeclared pair was independently registered using unchanged `experiments.behavior.head_depth_shadow.point_to_plane` and its existing fit gates, without alternate initialization retries or outcome-based pair selection. Robot-only FK compensates camera articulation:

`T_baseA_baseB = E_A @ inverse(T_cameraB_cameraA) @ inverse(E_B)`

Here `E = T_base_camera` maps camera-optical points into the instantaneous base frame using robot-only FK, the configured camera offset and optical-axis conversion. No world-pose integration or local map is used. Rates are full 3D translation norm and absolute Euler yaw change divided by simulated duration, not capture wall time. Candidate limits remain **0.002 m/s translation** and **0.005 rad/s yaw**. Rejected fits are unknown, never zero motion.

Capture episode/time identities, content hashes, calibration stamps, intrinsics, and robot-file hashes were checked. All 61 dense-hold capture identities were checked. These checks establish retained-input consistency, not real-sensor calibration accuracy.

## Results

| Sample set | Pair duration | Accepted fits | Stationary candidates | Nonstationary | Unknown |
| --- | --- | --- | --- | --- | --- |
| 12 sparse hold pairs: (384,389) through (439,444) | 5/30 s | 12 | 11 | 1 | 0 |
| 12 policy pairs: (0,32) through (352,384) | 32/30 s | 10 | 1 | 9 | 2 |
| 60 dense hold pairs: (384,385) through (443,444) | 1/30 s | 60 | 59 | 1 | 0 |

The policy pairs are a lower-temporal-resolution contrast, **not equivalent stop qualification**. Fits for policy pairs 224->256 and 256->288 were rejected.

Dense pair 384->385 measured **0.050731 m/s translation** and **0.263160 rad/s absolute yaw**, exceeding both limits. Across the remaining 59 pairs, maximum rates were **0.000229 m/s** and **0.000462 rad/s**.

Dense causal windows take the maximum translation rate and maximum absolute yaw rate over five adjacent pairs, not a net five-tick displacement. The first four outputs are `not_ready`; unknown fits invalidate a window. Of 56 full windows, the window ending at 389 was nonstationary and **55 windows ending at 390 through 444 were candidates**. No padding, future samples, or moving-phase samples were used. Dense execution took 55.5 seconds under a 170-second cap and two-thread limits; the default sparse output was preserved.

Pair minimum information eigenvalues ranged from **24,864.6 to 25,081.9**. These are descriptive estimator outputs only; no observability threshold or qualification is inferred.

## Interpretation and Limits

The retained data support an initial hold transient followed by likely-still endpoint estimates. Dense maxima reduce cancellation across control intervals but cannot exclude motion within a single 1/30-second interval. ICP acceptance does not establish absolute alignment accuracy, scene-motion observability, or certified stopping, and does not resolve native velocity-feedback semantics.

**Dense hold evidence does not prequalify moving tracking.** It provides no local-map, clearance, online freshness, real-sensor, or real-robot qualification. Any exploratory simulator use must remain explicitly labeled experimental; strict mode, its stop requirements, and thresholds remain unchanged. This offline analysis does not authorize motion or replace strict gates.

## Source Identity

Attested BEHAVIOR revision: `b1979916ec1549b10a4e65e630bc6504a9af1b00`.
SHA-256 identities below identify the analyzed inputs and code without publishing private artifacts or licensed content.

| Role | SHA-256 |
| --- | --- |
| Retained r2 capture audit | `8de795100e4e061649770100f456824aaba72bc8ed0db44a5c4bbdcaeb1e9e66` |
| Retained r2 feedback packet | `dcd6b948ca9a55aac7952ca8cd04c4e3fc1a2580af00775e0516fd5320dc9c1c` |
| Robot-only processed URDF | `b0d76760cbedfbcbe1ddc280380dd5f497bbca380313bc096d7239a2c50dae61` |
| Robot source configuration | `d3eb97811138d00edd83bc2be23f8d1d2e2b17c1bbea237a7cf2f9f89752524e` |
| Point-to-plane source module | `21813f61e0d9c03fa37b617af389cabae753c7b56eebff4798fff8b61ccba248` |
| Robot FK helper | `f0b34e967a16f4e718758db5ec6d5855f23aa544d8c26fe081e71a05d6fc6f48` |
| Sparse analysis script at execution | `a177bd0912bb127e1db1bfa01c2ae0e82c32c41d4d7580e476692838d24f1516` |
| Dense analysis script at execution | `fb8ab8513b2605255dc4aa602f18ae3da2a302da62cb156d2cf443be84f518ae` |
