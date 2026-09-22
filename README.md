# Skills & Unified Cognition

An agent workbench with two complementary parts: reusable **operational skills** and an experimental **Unified Cognition System (UCS)** for coordinating reasoning, memory and verification.

The operational skills define repeatable working procedures: each one tries to define **when it applies, what evidence counts, what must not be damaged, how to verify success, and how to hand work off cleanly**.

[`UnifiedCognitionSystem.py`](UnifiedCognitionSystem.py) adds executable machinery: a bounded expert deliberation loop, SQLite memory, verifiable rewards, a learned expert-selection policy, document extraction, and a PauseLang VM with framed proposal transport. The model is supplied through a callback, so the same orchestration can work with a local model, hosted model, or test fixture.

## Start here

| What you need | Where to start | Dependencies |
| --- | --- | --- |
| Procedures for an existing agent | [Included skills](#included-skills) and [Using the skills](#using-the-skills) | Only the selected skill's requirements |
| Run or embed the cognition prototype | [UCS quick start](#running-unified-cognition) and [runtime guide](docs/unified-cognition.md) | Python 3.12 and `requirements-ucs.txt` |
| Understand how the parts fit | [Architecture and current boundaries](docs/unified-cognition.md#architecture-and-current-boundaries) | No setup required |

The skills remain independently usable. UCS now selectively loads relevant skill instructions, recalls prior SQLite memories, and saves a durable report for every solve. Pass an existing `blackboard_path` to read its constraints and publish typed inference/evidence. Skill scripts and tool permissions remain under the host runtime's control.

## Running Unified Cognition

From the repository root, create an isolated environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-ucs.txt
python UnifiedCognitionSystem.py
```

The demo uses a temporary memory database and a fixed seed. It exercises offline coordination, an executable addition test, and three cognition-loop steps, then cleans up. It needs no model server, API key, GPU, or PDF collection. Python 3.12 is the CI target; the runtime dependencies are unnecessary when you only want the skills.

For CPU-only PyTorch, install `torch` from its CPU wheel index **before** installing the requirements:

```bash
python -m pip install 'torch>=2.2,<3' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-ucs.txt
```

Without an injected model, the experts produce built-in procedural drafts. Default embeddings are deterministic hash vectors, live fact checking requires an external adapter, and the fractal subsystem's training/validation figures are simulated. The smoke test demonstrates working plumbing and its supplied test case; it does not measure general intelligence or real-world task success. See the [runtime guide](docs/unified-cognition.md) for model injection, persistence, verification scope and transport details.

## Use a local model and keep continuity

After installing UCS dependencies, point the text-only client at your running model server. Replace the example model name with the one your server exposes:

```bash
mkdir -p "$HOME/.local/share/ucs"
python scripts/run_ucs.py \
  --memory "$HOME/.local/share/ucs/memory.db" \
  --base-url http://127.0.0.1:8080/v1 --model your-model \
  --skill invariant-guarded-debugging \
  --task "Investigate why the service fails after a restart"
```

The command produces a JSON report, not automatic shell actions. Add `--board /path/to/board.json` to use an existing typed board. Set `UCS_API_KEY` if the endpoint requires authentication. With no endpoint, it uses offline procedural drafts.

Read saved continuity without calling a model:

```bash
python scripts/run_ucs.py --memory "$HOME/.local/share/ucs/memory.db" --handover
```

See the [integration guide](docs/unified-cognition.md#skills-memory-and-the-durable-board) for context budgets, verifier configuration and recovering a board publication conflict without repeating work.

## Included skills

| Skill | Purpose |
| --- | --- |
| `blackboard` | Typed shared state for multi-model or multi-agent work, with provenance, ownership and verification. |
| `chatterbox-tts-recovery` | Restore and verify the Chatterbox browser/OpenAI-compatible TTS stack using the canonical add-on repository. |
| `check-notes-first` | Reuse structurally similar prior solutions as hypotheses, verify them against current state, and record only the reusable delta. |
| `council-blackboard` | Visible OpenClaw/Open WebUI council rooms backed by the typed blackboard. |
| `invariant-guarded-debugging` | Debugging workflow that protects known-good state and tests falsifiable hypotheses. |
| `local-model-runtime-profiler` | Benchmark and validate workload-specific local-model runtime profiles with reproducible receipts, context proof, lifecycle states, and real acceptance runs. |
| `minimum-sufficient-change` | Prevent over-solving by using the smallest plausible fix, proving it end to end, and escalating only when evidence requires it. |
| `openwebui-regression-test` | Test Open WebUI through the real user-visible browser path rather than config-only checks. |
| `privileged-operations` | Keep Linux root elevation narrow, visible and interactively approved by the user. |
| `risk-aware-retry` | Decide when to retry transient failures, change tactic, or stop based on risk and reversibility. |
| `session-handover` | Compact shift-style continuity notes with receipts, hazards, protected targets and next action. |
| `symlink-space-saver` | Safely reclaim duplicate storage with verified symlink, hard-link, or reflink decisions and real consumer acceptance tests. |
| `video-clip-editor` | Deterministic `ffmpeg`/`ffprobe` clipping with exact-boundary verification. |

## Using the skills

1. Pick the skill whose trigger matches the work you are doing.
2. Copy or expose that whole `skills/<name>/` directory to your agent runtime. Keep any sibling `scripts/` or `references/` directories with its `SKILL.md`.
3. Read the skill's frontmatter and requirements before invoking it. Some skills are pure operating procedures; others include executable helpers or assume particular local software.
4. Let the skill control the workflow rather than copying isolated commands out of context. In particular, preserve its inspection, safety, verification and rollback steps.
5. Run the skill's real canary or acceptance check where one is provided. A successful configuration change is not automatically a successful outcome.

Do **not** preload the whole collection into model context. Keep the skill registry/frontmatter available, then load the triggered skill and only the references needed for the current phase. Detailed examples, old receipts, and specialist reference material are durable knowledge, not default working-set context.

Agent runtimes discover skills differently, so there is intentionally no single hard-coded install path here. Point your runtime at the copied skill directory using that runtime's normal skill/plugin mechanism.

To sanity-check a checkout of this repository itself:

```bash
python scripts/check_repo.py
python -m compileall -q UnifiedCognitionSystem.py ucs_runtime.py skills scripts tests
```

With UCS dependencies installed, also run:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs repository structure checks, Python compilation, shell syntax checks, and blackboard safety-invariant canaries. A separate CPU job runs the UCS demo, integration checks and embedded PauseLang suite on pushes and pull requests.

## Layout

Each skill lives under `skills/<name>/` and has a `SKILL.md`. Some include scripts or reference material alongside it.

```text
UnifiedCognitionSystem.py
ucs_runtime.py
requirements-ucs.txt
docs/
  unified-cognition.md
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
  run_ucs.py
tests/
  test_ucs.py
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

Setup-specific skills use environment variables and normal home-relative defaults where practical. UCS takes explicit paths for its memory database and PDF input directory; choose these for your installation.

Some skills still describe particular software stacks or GNU/Linux tooling. Treat those as reference implementations and adjust service names, local paths, commands and platform-specific flags for your environment.

`privileged-operations` is intentionally opinionated about the **human approval boundary**, not one universal elevation command. Root work stays unprivileged until necessary, the exact privileged action and reason should be visible to the user, and authentication must happen through an interactive path the user can see and control. It prefers `pkexec` on graphical desktops and permits `sudo`/`doas` only when their terminal prompt is genuinely user-visible.

`symlink-space-saver` treats deduplication as a dependency change rather than a housekeeping trick. It checks whether apparent duplicates already share physical storage, identifies the lifecycle owner of the canonical copy, preserves rollback, and requires the real consumer to work before redundant storage is reclaimed.

## Runtime data and local configuration

Live blackboards, council transcripts/state, lock files, backups, and `.env` files are intentionally excluded from this repository. The checked-in blackboard code creates runtime state as needed; do not commit an existing `blackboards/` directory from a working agent installation.

For UCS, use a dedicated directory outside the checkout for persistent memory and exported audits/documents. The default `LLM_Memory.db`, its SQLite sidecars, default UCS exports, and local virtual environments are ignored as a precaution. UCS persists memories and per-run reports in SQLite and can append to a durable typed board. Its expert policy, confidence counters, concept graphs and internal blackboards currently live in process memory.

Council tooling assumes an OpenClaw/Open WebUI installation and should be configured with the environment variables documented in that skill.

The Chatterbox recovery skill deliberately does **not** duplicate backend source. Its canonical executable implementation is maintained in `pinguy/chatterbox-tts-addon`; the skill contains recovery invariants and acceptance checks only.

## Security note

Review any skill before giving an agent write access to a machine.

UCS executable verifiers run commands and may execute candidate code under the current account. A temporary directory, timeout and `shell=False` are **not a security sandbox**. Use trusted fixtures for the demo; run untrusted generated code in a separately restricted execution environment. PauseLang CRC checks detect corruption, not sender identity or authorisation.

For privileged Linux work, never give the agent your password. The agent should expose the root-requiring action first, then let a trusted graphical authentication dialog or visible terminal prompt collect credentials directly from you. Hidden password capture, password piping, passwordless rules added for convenience, and silent broad root shells are outside the intended model.

## Licence

Licensed under the **Apache License 2.0**. See `LICENSE` for the full terms.
