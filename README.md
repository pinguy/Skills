# Skills

Reusable agent skills for reliability-first technical work, multi-agent coordination, debugging, regression testing, privilege boundaries, handovers, and media operations.

These are operational skills rather than prompt snippets: each one tries to define **when it applies, what evidence counts, what must not be damaged, how to verify success, and how to hand work off cleanly**.

## Included skills

| Skill | Purpose |
| --- | --- |
| `blackboard` | Typed shared state for multi-model or multi-agent work, with provenance, ownership and verification. |
| `council-blackboard` | Visible OpenClaw/Open WebUI council rooms backed by the typed blackboard. |
| `invariant-guarded-debugging` | Debugging workflow that protects known-good state and tests falsifiable hypotheses. |
| `openwebui-chatterbox-recovery` | Restore and verify Chatterbox TTS semantics after Open WebUI upgrades. |
| `openwebui-regression-test` | Test Open WebUI through the real user-visible browser path rather than config-only checks. |
| `privileged-operations` | Least-privilege Linux operations using `pkexec` for the narrow commands that actually require root. |
| `qwen27-ground-check` | Use a local Qwen 27B-class model as a cautious second-model circuit breaker, not an oracle. |
| `risk-aware-retry` | Decide when to retry transient failures, change tactic, or stop based on risk and reversibility. |
| `session-handover` | Compact shift-style continuity notes with receipts, hazards, protected targets and next action. |
| `video-clip-editor` | Deterministic `ffmpeg`/`ffprobe` clipping with exact-boundary verification. |

## Layout

Each skill lives under `skills/<name>/` and has a `SKILL.md`. Some include scripts or reference material alongside it.

```text
skills/
  blackboard/
    SKILL.md
    scripts/
    references/
  privileged-operations/
    SKILL.md
  ...
```

## Design principles

The common thread across the collection is simple:

- configuration is not proof that something works;
- preserve known-good state explicitly;
- separate observations, inferences, decisions and tests;
- make the smallest reversible change that can test a hypothesis;
- use receipts such as logs, hashes, screenshots, traces and real test runs;
- verify through the actual user-facing path when that is what matters;
- stop or hand over with enough state that the next agent does not repeat failed work.

## Portability

Machine-specific paths and account identifiers are intentionally not included. Setup-specific skills use environment variables and normal home-relative defaults where practical.

Some skills still describe particular software stacks (for example Open WebUI or a local Qwen checker). Treat those as reference implementations and adjust model IDs, service names and local paths for your environment.

## Security note

`privileged-operations` deliberately requires `pkexec` for root elevation and keeps builds, downloads and exploratory work unprivileged. Review any skill before giving an agent write access to a machine.

## Licence

No licence has been selected for this repository yet. Unless and until one is added, normal copyright rules apply.
