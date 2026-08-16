---
name: "qwen27-ground-check"
description: "Use local Qwen 27B as a slow sanity-check circuit breaker for overconfident claims."
---

# Qwen 27B Ground Check

Use this skill when the user asks to ground, wobble-check, sanity-check, or make sure an answer is not just clever, especially with a local Qwen 27B-class model. Use it sparingly for claims or judgements where a slow independent local pass is worth the delay.

## Role

Treat Qwen 27B as a circuit breaker, not an oracle. Its job is to add friction, catch overconfident phrasing, and force a second look at unsupported claims. Do not outsource judgement to it.

Default Ollama model name:

```text
qwen3-6-27b:latest
```

Override it with `QWEN27_MODEL` when the local model uses a different tag.

Operational notes:

- Treat this as a deliberately slow second-model check; latency depends heavily on local hardware and load.
- Keep answers short by default so the checker remains a circuit breaker rather than a second full reasoning pass.
- The bundled `scripts/qwen27_raw_chat.py` calls Ollama's raw generate API and avoids relying on the normal chat/template path.
- Override the wrapper with `QWEN27_WRAPPER` only when a separately validated local wrapper is preferred.
- Keep context small unless a larger context is genuinely needed; this checker should receive only the evidence needed for the claim under review.

## When To Use

Use Qwen 27B when one or more apply:

- The user explicitly says `ground`, `check with Qwen`, `wobble`, `not just being clever`, or similar.
- The primary agent is about to make an absolute, historical, niche, reputational, or technical claim.
- The answer sounds too polished relative to the evidence.
- The decision touches memory, agency, ethics, trust, public claims, or durable system changes.
- A second local model pass is useful and the delay is acceptable.

Avoid Qwen 27B when:

- The task is urgent or latency matters.
- A deterministic source check is available and faster.
- The prompt would require dumping large private context. Summarize only the minimum needed.
- The model is already busy; do not start competing local generations.

## Procedure

1. Compress the issue into a small prompt.
   - Include the claim, proposed answer, or decision.
   - Include the evidence boundary: what is known, what is unverified, and what wording is being considered.
   - Ask for a gate: `ALLOW`, `ESCALATE`, or `REFUSE`.

2. Ask Qwen for critique, not agreement.
   - Tell it it is not a cheerleader.
   - Ask it to name failure modes and safer wording when needed.
   - Keep the output cap tight, normally 24-64 generated tokens unless the delay is worth it.

3. Wait for one clean result.
   - Do not launch another heavy local model while it runs.
   - If it times out, leaks scratchpad, or gives generic fluff, mark the grounding pass weak and do not rely on it.
   - If live chat responsiveness matters, cap output tightly or use a smaller/faster model; Qwen 27B is a brake, not a conversational bot.

4. Compare Qwen's answer against source evidence and the primary agent's own judgement.
   - If Qwen agrees but gives no evidence, treat that as weak agreement.
   - If Qwen disagrees on a high-risk claim, use cautious wording or investigate further.
   - If Qwen catches an absolute claim, prefer narrowing the claim unless primary sources prove it.

5. Report honestly.
   - Tell the user that Qwen was consulted.
   - Quote or summarize Qwen's useful point.
   - State the primary agent's final judgement separately.

## Prompt Template

```text
You are being used as a slow local grounding check for another agent, not as a cheerleader. Be blunt and cautious.

Issue:
[compact claim, draft answer, or decision]

Known evidence:
[brief facts already checked]

Task:
1. Identify overconfidence, missing caveats, unsupported absolutes, or factual risks.
2. Gate the wording as ALLOW, ESCALATE, or REFUSE.
3. Give safer wording if needed.
4. Name any failure modes in your own judgement.

Return a short final answer only.
```

## Command Pattern

Use the bundled helper:

```bash
printf '%s\n' '<issue text>' | bash scripts/qwen27_ground_check.sh
```

Or call the bundled raw wrapper directly:

```bash
python3 scripts/qwen27_raw_chat.py '<short prompt>'
```

Useful overrides:

```bash
QWEN27_MODEL='another-local-tag' \
QWEN27_MAX_TOKENS=64 \
QWEN27_TEMP=0.2 \
bash scripts/qwen27_ground_check.sh '<claim or issue>'
```

`OLLAMA_HOST` defaults to `http://127.0.0.1:11434`. If the raw wrapper returns an empty answer or an unterminated `<think>`/`<analysis>` block, treat the grounding pass as failed rather than accepting hidden-reasoning leakage as a result.

## Validation Note

Validation should use a deliberately overconfident factual claim with incomplete evidence. The desired behaviour is to flag unsupported absolutes and force narrower wording without treating the checker model as truth.
