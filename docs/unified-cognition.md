# Unified Cognition System

[`UnifiedCognitionSystem.py`](../UnifiedCognitionSystem.py) is a single-file experimental runtime. It combines model-independent expert coordination, persistent memory, verification and temporal-message experiments. The [README](../README.md#running-unified-cognition) covers installation and the offline demo.

## Architecture and current boundaries

| Component | Current behaviour | Boundary |
| --- | --- | --- |
| Operational skills | Procedures, invariants, helpers and acceptance checks under `skills/` | Loaded by the host agent; UCS has no skill loader |
| `ABM_Orchestrator` | Popper, Polya, Feynman and Wiener roles contribute to bounded rounds, critique and synthesis | Built-in drafts unless a model callback is supplied; all four roles use the same callback by default |
| `VerifiableRewardEngine` | Scores process, constraint and outcome checks; retains an exportable audit trace | A pass establishes only what the configured verifier checked |
| Expert policy | A PyTorch replay learner with `gamma=0` learns reward estimates and influences expert ranking | Does not train the injected language model; every expert still contributes each round |
| `EnhancedMemorySystem` | Stores memory records in SQLite with TF-IDF-based support for memory operations | This is not automatic retrieval-augmented prompting; `solve_with_abm()` stores its synthesis but does not fetch old memories into the prompt |
| `RSCI_Enhanced` | Maintains a concept graph with embedding-based operations | Defaults to hash vectors; supply a trained Word2Vec-compatible model for semantic embeddings |
| `SingularityMind` and trust-flow | Update concept dynamics and calculate flow state | Fractal training/validation metrics are simulated; the flow model is not a benchmark of agent reliability |
| PDF processor | Extracts text and detects possible book/section boundaries | Explicit `process_pdfs()` call; extracted documents are not automatically ingested into memory or model context |
| PauseLang bridge | Compiles proposals into temporal VM frames, validates CRCs, reassembles UTF-8 messages | Local queue or injected streams; no automatic network/audio receiver |
| `LiveRealityChecker` | Calls a supplied fact-checking adapter | Returns `unavailable` when none is configured; no built-in web search |

There are three separate blackboard uses here:

- `ucs.abm_orchestrator.blackboard` holds scored expert contributions and synthesis in memory.
- `ucs.blackboard` receives PauseLang proposals in memory.
- [`skills/blackboard`](../skills/blackboard/SKILL.md) provides the durable typed board with provenance, ownership, protected-target checks and completion gates.

These do not share storage or automatically enforce one another's rules. A host integration must explicitly transfer records and preserve provenance and permission boundaries. The council skill is an existing host-facing integration with the file-backed board, not a UCS adapter.

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

The callback contract is synchronous `prompt: str -> str`. UCS supplies role, task, context, prior answer and a local draft. Configure endpoint, credentials, token limits and request timeout in your model client. The default round limit is four; it does not impose a timeout on a blocking callback. A callback exception or empty response falls back to the local draft and records a risk in that contribution. Inspect `report.contributions` when diagnosing a model connection.

Use `ucs.set_agent_callable(your_callable)` to replace the callback after construction. A `live_query_function(topic)` can separately return a dictionary containing `status`, `summary`, `source` and `timestamp`; source quality remains the adapter's responsibility.

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

Call `ucs.export_rlvr_audit(path)` to save the full verifier trace. Keep the report or audit with a result when its verification scope matters: the synthesis's SQLite memory metadata currently preserves only selected report fields.

## Persistence and lifecycle

Pass an explicit `memory_db_path` to retain memory between instances, and create its parent directory first. With no path, UCS writes `LLM_Memory.db` in the working directory. The demonstration's temporary directory is intentionally discarded.

Only the SQLite memory is persisted automatically. Concept graphs, blackboards, confidence counts, audit log and expert-policy weights are in memory. Restarting UCS does not resume those components. Export audits before shutdown when needed, and keep runtime output outside the checkout.

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
python -m compileall -q UnifiedCognitionSystem.py skills scripts tests
python UnifiedCognitionSystem.py
python -m unittest discover -s tests -v
```

The test suite checks callback integration, memory reopening, unavailable fact checking, evidence separation, passing and failing executable verifiers, PauseLang message reconstruction and corruption rejection. It also runs the embedded VM torture suite and fails if that suite reports any failure.

The demo prints diagnostic text around its JSON summary; its entire stdout is not one JSON document. CI runs it separately from the assertions. These checks cover runtime plumbing and selected failure paths, not model quality, autonomous task success or scientific claims about cognition.
