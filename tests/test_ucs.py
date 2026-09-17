"""Offline integration checks using trusted fixtures and temporary state."""

import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest

from UnifiedCognitionSystem import (
    AgentResponse,
    Blackboard,
    EnhancedMemorySystem,
    LiveRealityChecker,
    OP_MAP,
    PauseLangBridge,
    PauseLangBridgeConfig,
    TortureTests,
    UnifiedCognitionSystem,
    VerifiableRewardEngine,
)


class UCSIntegrationTests(unittest.TestCase):
    def test_model_callback_and_persisted_synthesis(self):
        prompts = []

        def fixture(prompt):
            prompts.append(prompt)
            return "42"

        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / "memory.db")
            ucs = UnifiedCognitionSystem(
                memory_db_path=database, pdf_dir=directory,
                agent_callable=fixture, random_seed=7,
            )
            problem = "What is six times seven?"
            try:
                report = ucs.solve_with_abm(
                    problem, context={"rlvr": {"expected_numeric": 42}},
                    return_report=True,
                )
                self.assertEqual(report.answer, "42")
                self.assertTrue(report.hard_verifiers_passed)
                self.assertTrue(report.outcome_verifiers_passed)
                self.assertGreater(report.outcome_verifiers_run, 0)
                self.assertLessEqual(report.rounds, ucs.abm_orchestrator.max_rounds)
                self.assertEqual(len(prompts), 4 * report.rounds)
                self.assertTrue(all(problem in prompt for prompt in prompts))
            finally:
                ucs.shutdown()

            reopened = EnhancedMemorySystem(database)
            try:
                row = reopened.conn.execute(
                    "SELECT content FROM memories WHERE topic = ?", (problem,)
                ).fetchone()
                self.assertEqual(row, ("42",))
            finally:
                reopened.conn.close()

    def test_no_adapter_does_not_claim_live_evidence(self):
        result = LiveRealityChecker().check_fact("fixture topic")
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["source"])

    def test_content_constraints_do_not_claim_outcome_evidence(self):
        response = AgentResponse("fixture", "test", "Acceptance tests and rollback")
        VerifiableRewardEngine().evaluate(response, "fixture", {
            "rlvr": {"required_substrings": ["Acceptance tests", "rollback"]},
        })
        self.assertTrue(response.constraint_verifiers_passed)
        self.assertEqual(response.outcome_verifiers_run, 0)
        self.assertFalse(response.outcome_verifiers_passed)
        self.assertIsNone(response.outcome_reward)

    def test_executable_verifier_accepts_correct_and_rejects_wrong_code(self):
        config = {"rlvr": {"executable_tests": [{
            "name": "addition", "answer_file": "solution.py",
            "files": {"check.py": (
                "from solution import add\n"
                "assert add(20, 22) == 42\n"
                "assert add(-3, 2) == -1\n"
                "print('PASS')\n"
            )},
            "command": ["{python}", "check.py"],
            "stdout_regex": "PASS", "timeout": 5, "hard": True,
        }]}}
        for operator, expected in (("+", True), ("-", False)):
            with self.subTest(operator=operator):
                response = AgentResponse(
                    "fixture", "test", f"def add(a, b):\n    return a {operator} b\n",
                )
                _, hard_ok, results = VerifiableRewardEngine().evaluate(
                    response, "Implement addition", config,
                )
                self.assertEqual(hard_ok, expected)
                self.assertEqual(response.outcome_verifiers_passed, expected)
                outcome = next(r for r in results if r.verifier == "outcome.executable.addition")
                self.assertEqual(outcome.passed, expected)
                self.assertIn("returncode", outcome.details)

    def test_multiframe_unicode_round_trip_out_of_order(self):
        board = Blackboard()
        bridge = PauseLangBridge(PauseLangBridgeConfig(jitter_seconds=0), board)
        message = "Memory receipt: café — verified. " * 30
        packets = bridge.compile_proposal(OP_MAP["MEMORY"], 7, message, 90, 4)
        self.assertGreater(len(packets), 1)
        received = []
        for packet in reversed(packets):
            proposal = bridge.receive_packet(packet)
            if proposal is not None:
                received.append(proposal)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].message, message)
        self.assertEqual(received[0].agent_id, 7)
        self.assertEqual(board.get_latest_proposal(), received[0])
        self.assertIsNone(bridge.last_error)

    def test_corrupt_frame_is_rejected_without_posting(self):
        board = Blackboard()
        bridge = PauseLangBridge(PauseLangBridgeConfig(jitter_seconds=0), board)
        packet = copy.deepcopy(bridge.compile_proposal(
            OP_MAP["LOGIC"], 1, "trusted fixture", 90, 4,
        )[0])
        # Two SYNC instructions precede CONST/STORE pairs for the header/payload.
        # Alter the first payload byte, leaving the original CRC intact.
        packet.data_stream[2 + 2 * bridge.HEADER_SLOTS] ^= 1
        self.assertIsNone(bridge.receive_packet(packet))
        self.assertIsNone(board.get_latest_proposal())
        self.assertIn("frame CRC mismatch", bridge.last_error)

    def test_embedded_pauselang_suite(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            passed, failed = TortureTests.run_all()
        self.assertGreater(passed, 0, output.getvalue())
        self.assertEqual(failed, 0, output.getvalue())


if __name__ == "__main__":
    unittest.main()
