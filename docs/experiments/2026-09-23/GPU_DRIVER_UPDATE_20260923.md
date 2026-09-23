# GPU Host Automatic Driver Update

At the next physical-qualification preflight, `nvidia-smi` failed with
`Driver/library version mismatch`. Read-only inspection established:

- Loaded NVIDIA kernel module: 580.95.05.
- Installed NVML/CUDA driver libraries: 580.178.04.
- Ubuntu unattended upgrades began at 06:35:45 UTC.
- NVIDIA packages were replaced around 06:42 UTC and configured at 06:45 UTC.
- Updated NVIDIA DKMS modules are installed for the available kernels.
- The package manager remains active; reboot is not yet performed.

User explicitly approved reboot **after** updates finish and important artifacts
are verified locally. This does not authorize destroying/stopping the rental or
changing automatic security-update settings. All remote run files were copied
locally where absent, then checksum compared: no content differences, only two
timestamps. Update logs are retained privately under
`runs/host-driver-update-20260923-r1`. No active experiment workers were found
in the process listing. NVML cannot currently establish GPU process state.

The private stationary runner now checks for active package changes and records
a fingerprint of loaded driver version, boot identity and CUDA/NVML library
hashes through its existing pre/post integrity checks. It fails closed on a
mismatch or inaccessible GPU. Focused tests: 42 passed. Full private suite:
882 passed, one existing skip. No new inference, motion or driver mutation.

Pending recovery: wait for the active package process to exit, inspect dpkg
health, recheck backups, perform the approved reboot, and verify a changed boot
ID, functioning NVML and CUDA in the restored environments before GPU trials.
This incident is an infrastructure interruption, not a model or controller failure.

## Recovery Completed

Unattended upgrades reported all upgrades installed at 07:07:05 UTC and completed
cleanup. No updater/dpkg processes remained; `dpkg --audit` was empty. Rechecked
remote run backups: content matched, with only timestamp differences. The approved
`systemctl reboot` completed without stopping or destroying the Vast rental.

New boot ID: `c4ee625f-8142-4eb4-9a60-f4116d4e84bb`; kernel
`6.8.0-138-generic`; loaded and user-space NVIDIA driver `580.178.04`.
NVML works. CUDA tensor creation/reduction/synchronization passes separately in
SAM (Torch 2.7.1+cu126), cuRobo and native (both Torch 2.7.0+cu128) environments.
This is not a fresh simulator-render or SAM accuracy qualification after upgrade.
The read-only environment guard is synchronized to the host. No security-update
settings were changed. The subsequent single-arm FK run passes under unchanged
pre/post source and driver/library fingerprints; GPU compute workers are absent
after exit. See [single-arm FK results](CUROBO_SINGLE_ARM_FK_20260923.md).
