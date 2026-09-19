# Codex exec experiment transport

The deployable model path remains the Responses/Chat `JsonModel`. For bounded,
offline experiments, `CodexExecJsonModel` can instead invoke a locally installed
Codex CLI authenticated with ChatGPT. This consumes the signed-in account's
Codex allowance, not an OpenAI API-key balance. It is not a general Responses
API replacement and does not make computation free.

Use it for offline trace analysis, replay QA, judging, and development-only
executive/verifier checks. Do not use it for live motor control, latency-critical
loops, benchmark-grade dollar accounting, high concurrency, or deployment.

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

Before adopting this path for a workload, compare it with the API transport on a
small sequential pilot:

1. Two text-only structured calls.
2. Two calls with three current images.
3. Two calls with seven current/historical images.

Record total wall time, token usage, schema-valid completion rate, failures, and
throttling. Run sequentially first. Codex process and agent-runtime overhead make
this path unsuitable for the live loop unless measurements prove otherwise.

The transport intentionally has no CLI configuration switch yet. Instantiate it
only in a private experiment script so a stored deployment configuration cannot
silently change billing or execution semantics.
