# Unified Cognition System

[`UnifiedCognitionSystem.py`](../UnifiedCognitionSystem.py) is an experimental runtime, with context and persistence adapters in [`ucs_runtime.py`](../ucs_runtime.py). It combines model-independent expert coordination, persistent memory, verification and temporal-message experiments. The [README](../README.md#running-unified-cognition) covers installation and the offline demo.

## Architecture and current boundaries

| Component | Current behaviour | Boundary |
| --- | --- | --- |
| Operational framework | Loads [`framework/CORE.md`](../framework/CORE.md) into every solve and records its SHA-256 in the run receipt | Baseline policy context only; it cannot grant tool permission or replace host/runtime safety boundaries |
| Operational skills | Procedures, invariants, helpers and acceptance checks under `skills/` | UCS selects and loads entrypoints; the host executes tools and scripts |
| `ABM_Orchestrator` | Popper, Polya, Feynman and Wiener roles contribute to bounded rounds, critique and synthesis | Built-in drafts unless a model callback is supplied; all four roles use the same callback by default |
| `VerifiableRewardEngine` | Scores process, constraint and outcome checks; retains an exportable audit trace | A pass establishes only what the configured verifier checked |
| Expert policy | A PyTorch replay learner with `gamma=0` learns from outcome-checked contributions and influences expert ranking | Does not train the injected language model; every expert still contributes each round |
| `EnhancedMemorySystem` | Stores memory in SQLite and recalls relevant priors before a solve | Bounded lexical retrieval over the newest 500 memories; historical content is labelled as fallible |
| `RSCI_Enhanced` | Maintains a concept graph with embedding-based operations | Defaults to hash vectors; supply a trained Word2Vec-compatible model for semantic embeddings |
| `SingularityMind` and trust-flow | Update concept dynamics and calculate flow state | Fractal training/validation metrics are simulated; the flow model is not a benchmark of agent reliability |
| PDF processor | Extracts text and detects possible book/section boundaries | Explicit `process_pdfs()` call; extracted documents are not automatically ingested into memory or model context |
| PauseLang bridge | Compiles proposals into temporal VM frames, validates CRCs, reassembles UTF-8 messages | Local queue or injected streams; no automatic network/audio receiver |
| `LiveRealityChecker` | Calls a supplied fact-checking adapter | Returns `unavailable` when none is configured; no built-in web search |

There are three separate blackboard uses here:

- `ucs.abm_orchestrator.blackboard` holds scored expert contributions and synthesis in memory.
- `ucs.blackboard` receives PauseLang proposals in memory.
- [`skills/blackboard`](../skills/blackboard/SKILL.md) provides the durable typed board with provenance, ownership, protected-target checks and completion gates.

Pass an existing typed board as `blackboard_path` to import current constraints and bounded recent context, then append the final synthesis and receipts through the board helper. Internal working boards stay in memory. PauseLang proposals remain transport data and are not promoted into user decisions or automatically acted on. A council host can pass its board through the same adapter; route ownership and the visible room transcript remain host responsibilities.

## Embed the runtime

Run this from the repository root in the UCS environment. It exercises the real callback path using a deliberately trivial fixture; replace `answer_fixture` with your model client when integrating.

```python
import tempfile
from pathlib import Path

from UnifiedCognitionSystem import UnifiedCognitionSystem


def answer_fixture(prompt: str) -> str:
    # Test fixture only: no language model is called here.
    return "42"


with tempfile.TemporaryDirectory(prefix="ucs_example_") as directory:
    ucs = UnifiedCognitionSystem(
        memory_db_path=str(Path(directory) / "memory.db"),
        pdf_dir=directory,
        agent_callable=answer_fixture,
        random_seed=7,
    )
    try:
        report = ucs.solve_with_abm(
            "What is 6 multiplied by 7? Return only the number.",
            context={"rlvr": {"expected_numeric": 42}},
            return_report=True,
        )
        print(report.answer)
        print(report.verification_scope, report.outcome_verifiers_passed)
        assert report.answer == "42"
        assert report.outcome_verifiers_passed
    finally:
        ucs.shutdown()
```

The callback contract is synchronous `prompt: str -> str`. UCS supplies role, task, context, prior answer and a local draft. Configure endpoint, credentials, token limits and request timeout in your model client. The default round limit is four; it does not impose a timeout on a blocking callback. A callback exception or empty response falls back to the local draft and records a risk, `generation_source="fallback"`, and a report warning. The CLI exits nonzero on fallback. Inspect `report.contributions` when diagnosing a model connection.

Use `ucs.set_agent_callable(your_callable)` to replace the callback after construction. A `live_query_function(topic)` can separately return a dictionary containing `status`, `summary`, `source` and `timestamp`; source quality remains the adapter's responsibility.

The CLI accepts `--context /path/to/context.json` for the same task context. For example, `{"rlvr": {"expected_numeric": 42}}` checks a numerical fixture. Treat context files containing executable verifiers as trusted code configuration. The client accepts `--timeout` and `--max-tokens`; without explicit outcome checks the report correctly remains process-only.

## Skills, memory and the durable board

`solve_with_abm()` prepares context before any model call:

1. Load the bounded operational core. It is a separate baseline layer, not a selectable skill.
2. Read and validate the attached typed board. `needs_user`, `blocked` and `completed` prevent new work; protected board targets are rejected.
3. Select up to two skills by lexical overlap with their names/descriptions and load their full `SKILL.md` bodies. Scripts/references are not automatically executed or loaded.
4. Retrieve up to three relevant memories, with source IDs, dates, run IDs and evidence labels.
5. Pass this context to every expert, then save the final report and append inference/evidence to the attached board.

Use `skill_names=["check-notes-first", "invariant-guarded-debugging"]` on a solve to choose exact procedures. `skill_names=[]` disables selection for that call. `enable_skill_context=False` and `enable_memory_recall=False` disable the respective features at construction. The default registry is the repository's `skills/`; `skills_dir` can select another compatible registry.

The framework has its own 12,000-character budget and defaults to `framework/CORE.md`. Supply `framework_path=/path/to/core.md` to use an explicit compatible policy file. Compatibility is structural: the loader requires the ordered five-rule pipeline plus the precedence, human-agency, source-trust, mutation and response-closure boundaries. Missing or reordered invariants fail before model invocation rather than silently weakening policy. `enable_framework_context=False` is an explicit opt-out for hosts that supply an equivalent baseline elsewhere.

Skill bodies share a 24,000-character budget. Automatic selections that do not fit are named in `context_sources.omitted_skills` and report warnings; an explicit selection that cannot fit raises before model invocation. Memory recall has a 6,000-character budget, with 2,000 characters per content excerpt. Read a truncated prior through `retrieve_memory()` and its originating run receipt before reusing a procedure. Registry routing and memory recall are lexical heuristics, not semantic classification guarantees.

Board context has a 16,000-character budget. User decisions, policy and active route ownership are preserved together; if they cannot fit, the solve fails rather than silently dropping constraints. Up to three recent entries from each relevant typed collection are included when they fit. Prompt instructions are not a replacement for a tool executor's permission checks.

The runtime adds `_ucs` to a copy of the caller's context, leaving the supplied dictionary unchanged. `_ucs.framework` carries the baseline policy; `_ucs.precedence` states how framework, authenticated task constraints, skills and fallible history relate. `report.context_sources` records the framework path/hash and its machine-readable contract receipt, selected skill paths/hashes, memory IDs/timestamps and the input board revision. Model-generated text is never promoted into authenticated user decisions.

### Board publication and recovery

Create a board using the existing helper, then supply its path to UCS:

```bash
python skills/blackboard/scripts/blackboard.py init /path/to/board.json \
  --goal "Investigate service restart failures" --model host/router
python scripts/run_ucs.py --memory /path/to/memory.db --board /path/to/board.json \
  --task "Investigate service restart failures"
```

Publication atomically appends a proposal to `inferences` and a receipt to `evidence`; hard verification failures also enter `failed_attempts`. It does not create an independent `PASS:`, change the task's status, claim a route, or bypass existing ownership/approval rules. The same mechanism works on council boards without posting to the visible room.

The run is saved before publication. If the board revision changes during generation, UCS raises with the saved run ID. Inspect the changed board and reconcile whether the answer still applies, then call `ucs.publish_run(run_id, expected_revision=current_revision)`. This does not call the model or re-execute tests. An identical report/run ID is deduplicated; a conflicting report under that ID is rejected.

`ucs.get_handover()` returns recent run summaries, evidence and current board context. A `finished` run means the report was saved, not that acceptance tests passed. A `failed` run records its error; a `running` run after interruption requires checking actual worker/side-effect state before retry. There is no automatic resumption or claim that an interrupted worker is still alive.

### Learning and verification

Expert confidence and policy replay now update only when an outcome verifier ran. Process structure and substring constraints alone cannot earn a reliability update. A hard-check failure supplies zero policy reward even when another outcome check passes. The verifier's scope still matters: parsing code is a narrower outcome than executing meaningful task tests.

## Read the evidence correctly

`return_report=True` returns a `SolveReport`; `report.as_dict()` includes contributions, critiques, scores, verifier results and policy-training counters.

| Field or check | What it establishes |
| --- | --- |
| `converged` | Successive syntheses met the text-similarity/improvement stopping rule and applicable hard checks |
| `process_reward` | Basic response structure, such as non-empty text and declared tests/risks/assumptions |
| `constraint_reward` | Requested content constraints, such as required or forbidden text |
| `outcome_verifiers_run` / `outcome_verifiers_passed` | Whether configured outcome checks ran and all passed |
| `hard_verifiers_passed` | All checks marked hard passed; inspect which checks were configured |
| `rl_training_steps` | The expert-policy optimiser ran; does not demonstrate better task performance |

Convergence is a stopping condition, not proof of correctness. An outcome check can be narrow: Python syntax proves parsability, JSON-key checks prove shape, and the numeric matcher checks the last number in the answer. Choose a verifier that matches the actual acceptance criteria.

For deterministic task checks, use `ucs.register_rlvr_verifier(name, callback, hard=True)`. Its callback receives `(AgentResponse, problem, context)` and can return `(passed, details)`. Tests and expected results should come from a trusted task specification, not be accepted uncritically from the candidate being tested.

`context["rlvr"]["executable_tests"]` supports command lists, temporary fixture files, timeouts, expected exit codes and output patterns. Those commands can execute the candidate code with the current user's access and inherited environment. The runner is not a security sandbox. Use a restricted external executor for untrusted code; the bundled demo and regression checks use small trusted fixtures.

Call `ucs.export_rlvr_audit(path)` to save the full verifier trace. Every solve also saves its complete report, including all contribution verifier results, under a unique `run_id` in SQLite's `ucs_runs` table. `ucs.run_journal.get(run_id)` retrieves it. Memory metadata retains the run ID and final evidence scope/results.

## Persistence and lifecycle

Pass an explicit `memory_db_path` to retain memory between instances, and create its parent directory first. With no path, UCS writes `LLM_Memory.db` in the working directory. The demonstration's temporary directory is intentionally discarded.

SQLite memories and run reports are persisted automatically; an attached typed board is durable too. Concept graphs, internal blackboards, confidence counts, the in-memory audit log and expert-policy weights are not restored on restart. Saved reports preserve the verifier evidence from each solve. Export standalone audits when needed, and keep runtime output outside the checkout.

Use `try/finally` and call `ucs.shutdown()` to stop the transport receiver and close the database. Constructors seed Python, NumPy and PyTorch's global random generators; creating an instance can therefore affect other randomised work in the same process.

PDF processing is explicit:

```python
# On an existing UCS instance with pdf_dir set to your input directory:
results = ucs.process_pdfs()
ucs.save_pdf_results(results, output_file="/your/output/pdf_texts.json")
```

Choose an existing output directory. This saves extraction results, not a search index or an automatically populated memory corpus.

## PauseLang transport

The embedded VM and bridge use protocol version `714` (`v0.7.14-UCS`). This copy is maintained here; changes to the separate PauseLang repository do not automatically update it.

`compile_pauselang_message()` returns packets containing `pause_stream`, `data_stream`, labels and metadata. `inject_pauselang_stream()` executes and validates received frames, returning a proposal once the complete message has been assembled. Packets carry both duration and integer data streams; WAV export alone is not an implemented end-to-end audio decoder.

`send_pauselang_message()` delivers synchronously unless the receiver was started with `start_pauselang_bridge()`. In asynchronous mode a successful send means the frames were queued, not that the receiver accepted the complete message. CRC32 detects corruption; it does not authenticate senders or authorise their proposals.

The bridge supports gas limits, strict memory mode, frame/message CRCs and bounded frame counts. The checks exercise deterministic local frame delivery and rejection. They do not establish reliability over a real noisy network or audio link.

## Validation

From the repository root with UCS requirements installed:

```bash
python scripts/check_repo.py
python -m compileall -q UnifiedCognitionSystem.py ucs_runtime.py skills scripts tests
python UnifiedCognitionSystem.py
python -m unittest discover -s tests -v
```

The test suite checks always-on framework loading and hashing, selective skill loading, cross-session memory recall, board constraints and revision conflicts, retry-free receipt publication, outcome-only policy learning, a local HTTP model fixture, CLI handovers, callback integration, memory reopening, unavailable fact checking, evidence separation, passing and failing executable verifiers, PauseLang message reconstruction and corruption rejection. It also runs the embedded VM torture suite and fails if that suite reports any failure.

The demo prints diagnostic text around its JSON summary; its entire stdout is not one JSON document. CI runs it separately from the assertions. These checks cover runtime plumbing and selected failure paths, not model quality, autonomous task success or scientific claims about cognition.
