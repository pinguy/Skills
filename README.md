# Skills

Reusable agent skills for reliability-first technical work, multi-agent coordination, debugging, regression testing, privilege boundaries, handovers, and media operations.

These are operational skills rather than prompt snippets: each one tries to define **when it applies, what evidence counts, what must not be damaged, how to verify success, and how to hand work off cleanly**.

## Included skills

| Skill | Purpose |
| --- | --- |
| `blackboard` | Typed shared state for multi-model or multi-agent work, with provenance, ownership and verification. |
| `chatterbox-tts-recovery` | Restore and verify the Chatterbox browser/OpenAI-compatible TTS stack using the canonical add-on repository. |
| `check-notes-first` | Reuse structurally similar prior solutions as hypotheses, verify them against current state, and record only the reusable delta. |
| `council-blackboard` | Visible OpenClaw/Open WebUI council rooms backed by the typed blackboard. |
| `invariant-guarded-debugging` | Debugging workflow that protects known-good state and tests falsifiable hypotheses. |
| `openwebui-regression-test` | Test Open WebUI through the real user-visible browser path rather than config-only checks. |
| `privileged-operations` | Keep Linux root elevation narrow, visible and interactively approved by the user. |
| `qwen27-ground-check` | Use a local Qwen 27B-class model as a cautious second-model circuit breaker, not an oracle. |
| `risk-aware-retry` | Decide when to retry transient failures, change tactic, or stop based on risk and reversibility. |
| `session-handover` | Compact shift-style continuity notes with receipts, hazards, protected targets and next action. |
| `video-clip-editor` | Deterministic `ffmpeg`/`ffprobe` clipping with exact-boundary verification. |

## Using the skills

1. Pick the skill whose trigger matches the work you are doing.
2. Copy or expose that whole `skills/<name>/` directory to your agent runtime. Keep any sibling `scripts/` or `references/` directories with its `SKILL.md`.
3. Read the skill's frontmatter and requirements before invoking it. Some skills are pure operating procedures; others include executable helpers or assume particular local software.
4. Let the skill control the workflow rather than copying isolated commands out of context. In particular, preserve its inspection, safety, verification and rollback steps.
5. Run the skill's real canary or acceptance check where one is provided. A successful configuration change is not automatically a successful outcome.

Agent runtimes discover skills differently, so there is intentionally no single hard-coded install path here. Point your runtime at the copied skill directory using that runtime's normal skill/plugin mechanism.

To sanity-check a checkout of this repository itself:

```bash
python scripts/check_repo.py
```

GitHub Actions also runs repository structure checks, Python compilation, shell syntax checks, and a real blackboard initialise/validate canary on pushes and pull requests.

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
scripts/
  check_repo.py
```

## Design principles

The common thread across the collection is simple:

- configuration is not proof that something works;
- preserve known-good state explicitly;
- separate observations, inferences, decisions and tests;
- make the smallest reversible change that can test a hypothesis;
- use receipts such as logs, hashes, screenshots, traces and real test runs;
- verify through the actual user-facing path when that is what matters;
- treat remembered notes and model reasoning as hypotheses rather than authority;
- stop or hand over with enough state that the next agent does not repeat failed work.

## Portability

Machine-specific paths and account identifiers are intentionally not included. Setup-specific skills use environment variables and normal home-relative defaults where practical.

Some skills still describe particular software stacks (for example Open WebUI or a local Qwen checker). Treat those as reference implementations and adjust model IDs, service names and local paths for your environment.

`privileged-operations` is intentionally opinionated about the **human approval boundary**, not one universal elevation command. Root work stays unprivileged until necessary, the exact privileged action and reason should be visible to the user, and authentication must happen through an interactive path the user can see and control. It prefers `pkexec` on graphical desktops and permits `sudo`/`doas` only when their terminal prompt is genuinely user-visible.

## Runtime data and local configuration

Live blackboards, council transcripts/state, lock files, backups, and `.env` files are intentionally excluded from this repository. The checked-in blackboard code creates runtime state as needed; do not commit an existing `blackboards/` directory from a working agent installation.

The bundled Qwen ground-check wrapper uses only the Python standard library and expects an Ollama-compatible `/api/generate` endpoint. Council tooling additionally assumes an OpenClaw/Open WebUI installation and should be configured with the environment variables documented in that skill.

The Chatterbox recovery skill deliberately does **not** duplicate backend source. Its canonical executable implementation is maintained in `pinguy/chatterbox-tts-addon`; the skill contains recovery invariants and acceptance checks only.

## Security note

Review any skill before giving an agent write access to a machine.

For privileged Linux work, never give the agent your password. The agent should expose the root-requiring action first, then let a trusted graphical authentication dialog or visible terminal prompt collect credentials directly from you. Hidden password capture, password piping, passwordless rules added for convenience, and silent broad root shells are outside the intended model.

## Licence

Licensed under the **Apache License 2.0**. See `LICENSE` for the full terms.
