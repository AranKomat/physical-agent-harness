# Next Live Discovery Gate

## Verified Budget State

Read-only campaign-ledger inspection after the remote SAM test:

- Reservations/calls: 4,139, equal to the authorized cumulative call ceiling.
- Confirmed spending: $23.64500967140.
- Unresolved reservations: $34.955225022900, unchanged.
- Total exposure: $58.600234694300.
- Remaining under the $75 ceiling: $16.399765305700.

Unused dollars do not authorize new calls. No ledger entries, holds or limits
were changed by this check. Local SAM inference does not consume this paid-call
budget, and it cannot substitute for the planned GLM discovery test.

Proposed next scope, **not approved or dispatched**: up to six GLM calls, at most
$1 reserved exposure, cumulative call ceiling 4,145, with the $75 ceiling and
all existing holds unchanged. Endpoint/model/pricing validation and conservative
per-call reservations must fit within that scope before any request is sent.
No automatic retries or substitution of providers/models.

## Experiment To Unlock

Phase 3 must use fresh legal observations with real capture, submission,
completion and inventory-publication clocks. Keep one in-flight and one
coalesced pending discovery job. Preserve superseded/rejected/late requests,
source image hashes, structured request/result identities, token/cost records,
attention events and inventory changes. Late results may update historical
inventory, never current geometry. Shadow outputs must not affect actuators.

Use the existing V3 discovery coordinator, inventory and context interfaces.
Do not add another model search or tracking-only study as a substitute for this
experiment. Native motion must remain disabled unless separately qualified;
the six-call scope is not motor permission or a Phase 4 comparison budget.

## Transport Preparation Follow-Up

Private `scripts/glm_discovery_packet.py` now prepares original-image GLM V3
packets and provides a `GuardedGLMDiscovery` callback for the actual public
`AsyncDiscovery` worker. The response decoder returns a validated result, whereas
the worker expects raw JSON; the callback validates and returns the original
wire value for the worker's own parsing and durable publication.

Twelve targeted tests pass. They cover source bytes/dimensions/camera/time,
explicit normalized coordinates and strict schema, deadline expiry during image
preparation, detached deadlines, and valid/late/malformed/failed completions
through the real threaded worker and SQLite journal. Reserved requests cannot
be resent. Provider responses and clocks in these tests are fixtures, not live
model measurements.

The injected dispatch remains responsible for existing shared-ledger reservation
and bounded HTTP execution. No new paid call, credentials access, ledger mutation,
GPU job, or robot action was performed. This completes a transport integration
check, not Phase 3: the native capture-to-provider-to-inventory chain and actual
provider schema support still require the bounded live experiment above.

## Separate Physical Blockers

Phase 5 still needs defensible uncertainty/stop qualification and low-body
clearance. Phase 7 still needs external arm clearance and qualified stage/return.
The recent feature tracking and delayed-mask work did not resolve either gate.
Phases 6 and 8-14 therefore have not gained task-level qualification from these
perception diagnostics.

The immediate purpose of Phase 3 is to test the useful live semantic chain, not
claim task completion. A successful shadow test still leaves the physical and
independent-association requirements intact.
