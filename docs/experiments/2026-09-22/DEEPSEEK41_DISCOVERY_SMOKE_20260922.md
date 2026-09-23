# DeepSeek V4.1 Flash single-frame smoke test

Endpoint `deepseek/deepseek-v4.1-flash`, provider `deepinfra/fp8`, requested
low reasoning effort. One call on retained frame 448 with the exact earlier
label-blind discovery instruction and PNG. This used the final call allowed
under the existing 4100-call ceiling; no larger comparison or retry was run.

The provider returned finish reason `length` after 45.335 seconds, reporting
502 input tokens and 2048 completion tokens, all 2048 classified as reasoning.
No completed discovery answer was available. Cost $0.00093044 settled.
The transport completed, but the output contract failed. This is a failure
under the tested low-effort/2048-token configuration, not evidence of poor
visual recognition. Disabled reasoning and a larger output budget were not
tested and must not be inferred from this result.

Private artifacts: `deepseek41-discovery-20260922-r1`, including exact request,
endpoint metadata, response, report, and audit. Five focused tests and Ruff
pass. No GPU/simulator actions, policy changes, retries or fallback requests.
All prior unresolved billing holds retained. Shared call count is now 4100/4100;
further paid calls require an explicit extension of that count ceiling.

The saved requests also confirm both the original GLM Flash trial and its
repeat used `reasoning: {effort: low}`. No GLM medium-effort comparison has
been performed in this discovery series.
