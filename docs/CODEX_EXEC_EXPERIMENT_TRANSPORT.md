# Codex exec experiment transport

The deployable model path remains the Responses/Chat `JsonModel`. For bounded,
offline experiments, `CodexExecJsonModel` can instead invoke a locally installed
Codex CLI authenticated with ChatGPT. This consumes the signed-in account's
Codex allowance, not an OpenAI API-key balance. It is not a general Responses
API replacement and does not make computation free.

Use it as the preferred development transport for trace analysis, replay QA,
judging, planning, and sparse simulator-paused executive/verifier calls. The
same adapter satisfies the harness model interface for either role. Keep the API
transport for third-party deployment, experiments specifically testing API or
Flex behavior, benchmark-grade dollar accounting, high concurrency, and
latency-critical control. Never place either remote model transport in a dense
motor loop.

The account owner must run:

```bash
codex login
codex login status
```

Do not copy or share `~/.codex/auth.json`. The adapter removes API-key and access-
token environment variables, requires `Logged in using ChatGPT`, runs every call
ephemerally in an isolated temporary directory with a read-only sandbox, passes
only explicit image files, validates the final JSON against the supplied schema,
and never retries automatically.

The journal records the model, role, request hash, image provenance, token usage,
wall time, and ambiguous failures. It records zero API microdollars because no
API tariff is available, with an explicit `chatgpt_subscription` billing route.
That zero must not be interpreted as zero subscription usage or zero compute.

Before adopting this path for a large workload, compare it with the API transport
on a small sequential pilot:

1. Two text-only structured calls.
2. Two calls with three current images.
3. Two calls with seven current/historical images.

Record total wall time, token usage, schema-valid completion rate, failures, and
throttling. Run sequentially first. Codex process and agent-runtime overhead make
this path unsuitable for high-frequency control.

On 2026-09-19, Codex CLI 0.155.1 completed two GPT-6 Astra low-effort smoke tests
using ChatGPT authentication:

| Input | Wall time | Input tokens | Output tokens | Result |
|---|---:|---:|---:|---|
| Text-only schema | 5.74 s | 14,515 | 21 | Valid structured output |
| One retained 480x480 radio frame | 7.93 s | 14,923 | 39 | Valid visual structured output |

These are transport checks, not quality or load tests. The roughly 14.5k-token
runtime prefix makes this inefficient for trivial micro-calls even when it avoids
API charges. Subscription allowance, throttling, and model availability remain
external limits. Codex CLI 0.144.1 was rejected as too old for GPT-6 Astra in the
same environment.

The transport intentionally has no deployment-configuration switch yet.
Instantiate it in a private development experiment script so a stored deployment
configuration cannot silently change billing or execution semantics.
