"""Behavioural checks across skill routing, restarts and typed-board boundaries."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest

from UnifiedCognitionSystem import ABM_Orchestrator, UnifiedCognitionSystem
from ucs_runtime import DurableBlackboard, FrameworkPolicy, SkillRegistry


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "memory.db"
        self.skills = self.root / "skills"
        for name, desc in (("debug-retry", "Debug network retry failures"),
                           ("video-edit", "Edit video clips and audio")):
            folder = self.skills / name
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text(
                f'---\nname: "{name}"\ndescription: "{desc}"\n---\n'
                f"# {name}\nUse a falsifiable test. Marker: {name}.\n"
            )

    def ucs(self, **kwargs):
        return UnifiedCognitionSystem(
            memory_db_path=str(self.db), skills_dir=self.skills, **kwargs,
        )

    def board(self):
        path = self.root / "board.json"
        adapter = DurableBlackboard(path)
        args = adapter.helper.parser().parse_args([
            "init", str(path), "--goal", "Debug network retry failures", "--model", "test/host",
        ])
        with contextlib.redirect_stdout(io.StringIO()):
            args.fn(args)
        return adapter

    def command(self, adapter, *args):
        parsed = adapter.helper.parser().parse_args(list(args))
        with contextlib.redirect_stdout(io.StringIO()):
            parsed.fn(parsed)

    def test_selective_skills_and_recalled_memory_reach_model_after_restart(self):
        first = self.ucs(agent_callable=lambda prompt: "Use the known socket timeout fix.")
        try:
            prior = first.solve_with_abm("Debug network retry failures", return_report=True)
            self.assertEqual(prior.verification_scope, "process")
        finally:
            first.shutdown()
        prompts = []
        second = self.ucs(agent_callable=lambda prompt: prompts.append(prompt) or "Inspect timeout logs.")
        try:
            current = second.solve_with_abm("Debug network retry failures again", return_report=True)
            self.assertTrue(prompts)
            self.assertIn("Holistic Context", prompts[0])
            self.assertIn("Hold Your Ground", prompts[0])
            self.assertIn("Marker: debug-retry", prompts[0])
            self.assertNotIn("Marker: video-edit", prompts[0])
            self.assertIn("known socket timeout fix", prompts[0])
            self.assertIsNotNone(current.context_sources["framework"])
            self.assertEqual(len(current.context_sources["framework"]["sha256"]), 64)
            self.assertEqual(current.context_sources["memories"][0]["run_id"], prior.run_id)
            self.assertEqual(current.context_sources["memories"][0]["verification_scope"], "process")
            saved = second.run_journal.get(prior.run_id)
            self.assertEqual(saved["report"]["answer"], prior.answer)
            self.assertEqual(len(second.get_handover()["runs"]), 2)
        finally:
            second.shutdown()

    def test_framework_is_baseline_bounded_and_explicitly_disableable(self):
        custom = self.root / "core.md"
        custom.write_text(
            "# Fixture Framework\n"
            "FRAMEWORK-MARKER\n"
            "## Precedence\n"
            "### 1. Holistic Context\n"
            "### 2. Egalitarianism\n"
            "### 3. Beneficence\n"
            "### 4. Don’t Be a Fucking Cunt\n"
            "### 5. Hold Your Ground\n"
            "### Advise, don’t decide\n"
            "## Decision and authority gates\n"
            "## Source trust and instruction boundaries\n"
            "## Tool and mutation discipline\n"
            "## Response closure\n"
        )
        policy = FrameworkPolicy(custom)
        loaded = policy.load()
        self.assertEqual(loaded["instructions"], custom.read_text())
        self.assertEqual(len(loaded["sha256"]), 64)
        self.assertEqual(loaded["contract"]["rules"], list(FrameworkPolicy.RULE_ORDER))
        self.assertEqual(loaded["contract"]["sha256"], loaded["sha256"])
        with self.assertRaisesRegex(ValueError, "context budget"):
            FrameworkPolicy(custom, max_chars=5).load()

        prompts = []
        ucs = self.ucs(
            framework_path=custom,
            agent_callable=lambda prompt: prompts.append(prompt) or "fixture",
        )
        try:
            report = ucs.solve_with_abm("Debug network retry failures", return_report=True)
            self.assertIn("FRAMEWORK-MARKER", prompts[0])
            self.assertEqual(report.context_sources["framework"]["sha256"], loaded["sha256"])
            self.assertEqual(
                report.context_sources["framework"]["contract"]["rules"],
                list(FrameworkPolicy.RULE_ORDER),
            )
        finally:
            ucs.shutdown()

        disabled_prompts = []
        disabled = self.ucs(
            enable_framework_context=False,
            agent_callable=lambda prompt: disabled_prompts.append(prompt) or "fixture",
        )
        try:
            report = disabled.solve_with_abm("Debug network retry failures", return_report=True)
            self.assertIsNone(report.context_sources["framework"])
            self.assertNotIn("Holistic Context", disabled_prompts[0])
        finally:
            disabled.shutdown()

    def test_framework_rejects_missing_or_reordered_invariants(self):
        missing = self.root / "missing-core.md"
        missing.write_text("# nope\n")
        with self.assertRaisesRegex(ValueError, "missing required boundary"):
            FrameworkPolicy(missing).load()

        reordered = self.root / "reordered-core.md"
        reordered.write_text(
            "## Precedence\n"
            "### 2. Egalitarianism\n"
            "### 1. Holistic Context\n"
            "### 3. Beneficence\n"
            "### 4. Don’t Be a Fucking Cunt\n"
            "### 5. Hold Your Ground\n"
            "### Advise, don’t decide\n"
            "## Decision and authority gates\n"
            "## Source trust and instruction boundaries\n"
            "## Tool and mutation discipline\n"
            "## Response closure\n"
        )
        with self.assertRaisesRegex(ValueError, "five-rule order"):
            FrameworkPolicy(reordered).load()

    def test_registry_budget_and_path_boundaries(self):
        registry = SkillRegistry(self.skills)
        with self.assertRaisesRegex(ValueError, "unknown skills"):
            registry.select("task", ["../outside"])
        with self.assertRaisesRegex(ValueError, "budget"):
            registry.select("task", ["debug-retry"], max_chars=10)
        selected, omitted = registry.select("debug network retry", max_chars=10)
        self.assertEqual(selected, [])
        self.assertEqual(omitted, ["debug-retry"])
        outside = self.root / "outside.md"
        outside.write_text("private")
        entry = self.skills / "debug-retry/SKILL.md"
        entry.unlink()
        entry.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "escapes"):
            registry.select("task", ["debug-retry"])

    def test_board_constraints_reach_prompt_and_self_report_cannot_complete(self):
        board = self.board()
        self.command(board, "add", str(board.path), "user_decisions", "--content",
                     "DO_NOT_TOUCH: /protected", "--model", "user/host", "--kind", "user",
                     "--source", "authenticated test fixture")
        prompts = []
        ucs = self.ucs(blackboard_path=board.path,
                       agent_callable=lambda prompt: prompts.append(prompt) or "42")
        try:
            report = ucs.solve_with_abm("What is six times seven?",
                        {"rlvr": {"expected_numeric": 42}}, return_report=True)
            self.assertIn("DO_NOT_TOUCH: /protected", prompts[0])
            saved = board.helper.load(board.path)
            self.assertEqual(saved["status"], "active")
            self.assertEqual(len(saved["inferences"]), 1)
            self.assertEqual(len(saved["evidence"]), 1)
            self.assertEqual(len(saved["user_decisions"]), 1)
            self.assertEqual(saved["test_results"], [])
            self.assertFalse(board.helper.independent_pass(saved))
            self.assertEqual(board.helper.validate(saved), [])
            self.assertTrue(ucs.publish_run(report.run_id, saved["revision"])["duplicate"])
            self.assertEqual(board.helper.load(board.path)["revision"], saved["revision"])
            with self.assertRaises(SystemExit):
                self.command(board, "status", str(board.path), "completed", "--model", "ucs/runtime")
        finally:
            ucs.shutdown()

    def test_changed_board_preserves_report_and_republish_does_not_rerun(self):
        board = self.board()
        ucs = self.ucs(blackboard_path=board.path, agent_callable=lambda prompt: "42")
        ucs.abm_orchestrator.max_rounds = 1
        # A deterministic verifier models an external update during the solve.
        changed = []
        def concurrent_update(response, problem, context):
            if not changed:
                self.command(board, "add", str(board.path), "open_questions", "--content",
                             "Host changed the task", "--model", "test/host", "--kind", "tool",
                             "--source", "test fixture")
                changed.append(True)
            return True, "fixture checked"
        ucs.register_rlvr_verifier("concurrent_update", concurrent_update)
        try:
            with self.assertRaisesRegex(RuntimeError, "saved but blackboard publication failed"):
                ucs.solve_with_abm("Debug network retry failures", return_report=True)
            report = ucs.last_abm_report
            self.assertEqual(ucs.run_journal.get(report.run_id)["status"], "finished")
            self.assertEqual(board.helper.load(board.path)["inferences"], [])
            ucs.set_agent_callable(lambda prompt: self.fail("must not rerun model"))
            revision = board.helper.load(board.path)["revision"]
            self.assertTrue(ucs.publish_run(report.run_id, revision)["ok"])
            altered = report.as_dict()
            altered["answer"] = "different result"
            with self.assertRaisesRegex(ValueError, "different report"):
                board.publish(altered, revision + 1)
        finally:
            ucs.shutdown()

    def test_paused_board_blocks_model_calls(self):
        board = self.board()
        self.command(board, "add", str(board.path), "open_questions", "--content",
                     "Awaiting a user decision", "--model", "test/host", "--kind", "tool",
                     "--source", "test fixture")
        self.command(board, "status", str(board.path), "needs_user", "--model", "test/host")
        ucs = self.ucs(blackboard_path=board.path,
                      agent_callable=lambda prompt: self.fail("must not call model"))
        try:
            with self.assertRaisesRegex(ValueError, "needs_user"):
                ucs.solve_with_abm("Debug network retry failures")
            self.assertEqual(ucs.run_journal.recent(), [])
            self.assertEqual(ucs.get_handover()["current_board"]["status"], "needs_user")
        finally:
            ucs.shutdown()

    def test_learning_requires_outcome_and_hard_failure_gets_zero_reward(self):
        orchestrator = ABM_Orchestrator(model_callable=lambda prompt: "42", max_rounds=2)
        report = orchestrator.solve_with_report("What is six times seven?")
        self.assertEqual(report.rl_training_steps, 0)
        self.assertEqual(len(orchestrator.rl_policy.memory), 0)
        self.assertEqual(sum(orchestrator.confidence_system.successes.values()), 0)
        self.assertEqual(sum(orchestrator.confidence_system.failures.values()), 0)
        checked = orchestrator.solve_with_report("What is six times seven?", {
            "rlvr": {"expected_numeric": 42, "forbidden_substrings": ["42"]},
        })
        self.assertFalse(checked.hard_verifiers_passed)
        self.assertGreater(checked.rl_training_steps, 0)
        self.assertTrue(all(item[2] == 0 for item in orchestrator.rl_policy.memory))
        steps = checked.rl_training_steps
        unchecked = orchestrator.solve_with_report("Another task without outcome checks")
        self.assertEqual(unchecked.rl_training_steps, steps)

    def test_failed_run_and_model_fallback_are_visible(self):
        ucs = self.ucs(agent_callable=lambda prompt: (_ for _ in ()).throw(ConnectionError("offline")))
        try:
            report = ucs.solve_with_abm("Debug network retry failures", return_report=True)
            self.assertTrue(report.integration_warnings)
            self.assertTrue(any(c.generation_source == "fallback" for c in report.contributions))
            original = ucs.abm_orchestrator.solve_with_report
            def broken(*args, **kwargs):
                raise RuntimeError("fixture internal failure")
            ucs.abm_orchestrator.solve_with_report = broken
            with self.assertRaisesRegex(RuntimeError, "fixture internal failure"):
                ucs.solve_with_abm("Debug retry another task")
            ucs.abm_orchestrator.solve_with_report = original
            recent = ucs.run_journal.recent(1)[0]
            self.assertEqual(recent["status"], "failed")
            self.assertIn("fixture internal failure", recent["error"])
        finally:
            ucs.shutdown()

    def test_cli_endpoint_and_handover_with_no_additional_model_calls(self):
        requests = []
        response_text = ["42"]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append((self.path, payload))
                body = json.dumps({"choices": [{"message": {"content": response_text[0]}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        script = Path(__file__).resolve().parents[1] / "scripts/run_ucs.py"
        base = [sys.executable, str(script), "--memory", str(self.db)]
        context = self.root / "context.json"
        context.write_text(json.dumps({"rlvr": {"expected_numeric": 42}}))
        try:
            task_args = [
                "--task", "What is six times seven?", "--base-url",
                f"http://127.0.0.1:{server.server_port}/v1", "--model", "fixture",
                "--context", str(context),
            ]
            completed = subprocess.run(base + task_args, text=True, capture_output=True, timeout=30)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertTrue(report["outcome_verifiers_passed"])
            self.assertTrue(requests)
            self.assertTrue(all(path == "/v1/chat/completions" for path, _ in requests))
            self.assertTrue(all(item["model"] == "fixture" for _, item in requests))
            count = len(requests)
            handover = subprocess.run(base + ["--handover"], text=True, capture_output=True, timeout=30)
            self.assertEqual(handover.returncode, 0, handover.stderr)
            self.assertEqual(json.loads(handover.stdout)["runs"][0]["run_id"], report["run_id"])
            self.assertEqual(len(requests), count)
            response_text[0] = None
            failed = subprocess.run(base + task_args, text=True, capture_output=True, timeout=30)
            self.assertEqual(failed.returncode, 2, failed.stderr)
            self.assertTrue(json.loads(failed.stdout)["integration_warnings"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
