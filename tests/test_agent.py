"""
╔══════════════════════════════════════════════════════════════╗
║  Smart-Grid Agent — Unit Test Suite                          ║
║  Covers: Collector, Brain, Executor Security, Action Log     ║
║                                                              ║
║  Run: pytest tests/test_agent.py -v                          ║
║  sys.path is configured automatically via conftest.py        ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import unittest
from pathlib import Path
from unittest.mock import patch

# Set environment for tests before any imports
os.environ["AGENT_MODE"] = "demo"
os.environ["GEMINI_API_KEY"] = "test-key-placeholder"

# Backend imports — resolved via conftest.py sys.path setup
from collector import get_collector, DemoCollector, DynatraceCollector, DynatraceMCPContext  # noqa: E402
from brain import GeminiBrain  # noqa: E402
from executor import ExecutorModule, PROTECTED_SERVICES  # noqa: E402
import action_log  # noqa: E402


# ─────────────────────────────────────────────
#  Collector Tests
# ─────────────────────────────────────────────
class TestDemoCollector(unittest.TestCase):
    """Test the demo metrics collector (psutil + simulated services)."""

    def setUp(self):
        from collector import DemoCollector
        self.collector = DemoCollector()

    def test_collect_returns_mcp_context(self):
        """collect() must return a DynatraceMCPContext object."""
        from collector import DynatraceMCPContext
        ctx = self.collector.collect()
        self.assertIsInstance(ctx, DynatraceMCPContext)

    def test_metrics_contain_required_fields(self):
        """Metrics dict must contain all required fields."""
        ctx = self.collector.collect()
        required = ["cpu", "memory", "status", "services",
                    "disk_io_read", "disk_io_write"]
        for field in required:
            self.assertIn(field, ctx.metrics, f"Missing field: {field}")

    def test_cpu_within_valid_range(self):
        """CPU usage must be between 0 and 100."""
        ctx = self.collector.collect()
        self.assertGreaterEqual(ctx.metrics["cpu"], 0)
        self.assertLessEqual(ctx.metrics["cpu"], 100)

    def test_memory_within_valid_range(self):
        """Memory usage must be between 0 and 100."""
        ctx = self.collector.collect()
        self.assertGreaterEqual(ctx.metrics["memory"], 0)
        self.assertLessEqual(ctx.metrics["memory"], 100)

    def test_status_is_one_of_valid_values(self):
        """Status must be one of: idle, normal, busy, critical."""
        ctx = self.collector.collect()
        self.assertIn(ctx.metrics["status"], ["idle", "normal", "busy", "critical"])

    def test_services_is_a_list(self):
        """Services field must be a list."""
        ctx = self.collector.collect()
        self.assertIsInstance(ctx.metrics["services"], list)

    def test_mcp_context_string_contains_markers(self):
        """MCP context string must contain required format markers."""
        ctx = self.collector.collect()
        context_str = ctx.to_context_string()
        self.assertIn("DYNATRACE_MCP_CONTEXT", context_str)
        self.assertIn("cpu_usage_percent", context_str)
        self.assertIn("memory_usage_percent", context_str)
        self.assertIn("SYSTEM METRICS", context_str)

    def test_stop_service_removes_it_from_future_collections(self):
        """Stopping a service should exclude it from subsequent collect() calls."""
        ctx_before = self.collector.collect()
        services_before = [s["name"] for s in ctx_before.metrics["services"]]

        if services_before:
            target = services_before[0]
            self.collector.stop_service(target)

            ctx_after = self.collector.collect()
            services_after = [s["name"] for s in ctx_after.metrics["services"]]
            self.assertNotIn(target, services_after,
                             f"Service '{target}' should be absent after stop()")

    def test_to_dict_is_json_serializable(self):
        """MCP context must be fully JSON-serializable."""
        ctx = self.collector.collect()
        d = ctx.to_dict()
        serialized = json.dumps(d)  # Must not raise
        self.assertIsInstance(serialized, str)
        self.assertGreater(len(serialized), 100)

    def test_multiple_ticks_increment(self):
        """Each collect() call should increment the internal tick."""
        collector_fresh = __import__("collector").DemoCollector()
        self.assertEqual(collector_fresh._tick, 0)
        collector_fresh.collect()
        self.assertEqual(collector_fresh._tick, 1)
        collector_fresh.collect()
        self.assertEqual(collector_fresh._tick, 2)


# ─────────────────────────────────────────────
#  Brain Tests
# ─────────────────────────────────────────────
class TestGeminiBrain(unittest.TestCase):
    """Test the Gemini Brain decision engine (local fallback mode)."""

    def setUp(self):
        from brain import GeminiBrain
        self.brain = GeminiBrain(api_key="placeholder-no-real-key")
        self.brain._available = False  # Force local rule engine

    def _get_decision(self):
        from collector import DemoCollector
        ctx = DemoCollector().collect()
        return self.brain.analyze(ctx)

    def test_analyze_returns_dict(self):
        """analyze() must return a dictionary."""
        result = self._get_decision()
        self.assertIsInstance(result, dict)

    def test_decision_has_all_required_keys(self):
        """Decision output must contain all required top-level keys."""
        result = self._get_decision()
        required_keys = ["analysis", "risk_level", "actions",
                         "confidence", "brain", "timestamp",
                         "estimated_total_savings", "recommendation"]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_risk_level_is_valid(self):
        """risk_level must be one of: low, medium, high."""
        result = self._get_decision()
        self.assertIn(result["risk_level"], ["low", "medium", "high"])

    def test_confidence_is_between_0_and_1(self):
        """confidence must be a float in [0.0, 1.0]."""
        result = self._get_decision()
        conf = result.get("confidence", -1)
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

    def test_actions_field_is_a_list(self):
        """actions must be a list."""
        result = self._get_decision()
        self.assertIsInstance(result["actions"], list)

    def test_each_action_has_required_fields(self):
        """Every action item must have service, action, reason, and priority."""
        result = self._get_decision()
        for action in result.get("actions", []):
            for field in ["service", "action", "reason", "priority"]:
                self.assertIn(field, action, f"Action missing field: {field}")

    def test_estimated_savings_structure(self):
        """estimated_total_savings must have cpu_percent and memory_mb keys."""
        result = self._get_decision()
        savings = result.get("estimated_total_savings", {})
        self.assertIsInstance(savings, dict)
        self.assertIn("cpu_percent", savings)
        self.assertIn("memory_mb", savings)
        self.assertIn("cost_per_hour_usd", savings)

    def test_savings_are_non_negative(self):
        """All savings estimates must be non-negative numbers."""
        result = self._get_decision()
        savings = result.get("estimated_total_savings", {})
        self.assertGreaterEqual(savings.get("cpu_percent", 0), 0)
        self.assertGreaterEqual(savings.get("memory_mb", 0), 0)
        self.assertGreaterEqual(savings.get("cost_per_hour_usd", 0), 0)

    def test_brain_field_identifies_engine(self):
        """brain field must be set to 'local-rule-engine' in fallback mode."""
        result = self._get_decision()
        self.assertEqual(result["brain"], "local-rule-engine")


# ─────────────────────────────────────────────
#  Executor Security Tests
# ─────────────────────────────────────────────
class TestExecutorSecurity(unittest.TestCase):
    """
    Critical security tests for the executor module.
    These tests verify that the Human-in-the-Loop gate cannot be bypassed.
    """

    def setUp(self):
        from executor import ExecutorModule
        self.executor = ExecutorModule(dry_run=True, demo_mode=True)

    def test_protected_services_are_blocked(self):
        """All entries in PROTECTED_SERVICES must be flagged as protected."""
        from executor import PROTECTED_SERVICES
        for svc in PROTECTED_SERVICES:
            self.assertTrue(
                self.executor._is_protected(svc),
                f"SECURITY FAILURE: '{svc}' should be protected but is not!"
            )

    def test_non_critical_services_are_allowed(self):
        """Non-critical background services must NOT be flagged as protected."""
        allowed = [
            "baloo_file_indexer",
            "tracker-miner-fs",
            "packagekitd",
            "evolution-addressbook",
        ]
        for svc in allowed:
            self.assertFalse(
                self.executor._is_protected(svc),
                f"'{svc}' should NOT be protected!"
            )

    def test_dry_run_never_calls_subprocess(self):
        """In dry-run mode, stop_service must never call subprocess.run."""
        with patch("subprocess.run") as mock_run:
            success, output = self.executor._stop_service("baloo_file_indexer")
            mock_run.assert_not_called()
            self.assertTrue(success)
            self.assertIn("SIMULATED", output)

    def test_queue_rejects_protected_service(self):
        """queue_actions_from_decision must silently skip protected services."""
        decision = {
            "actions": [
                {
                    "service": "sshd",
                    "action": "stop",
                    "reason": "Security test — should be blocked",
                    "estimated_cpu_save": 1.0,
                    "estimated_memory_save_mb": 10,
                    "priority": "low",
                }
            ]
        }
        ids = self.executor.queue_actions_from_decision(decision)
        self.assertEqual(
            len(ids), 0,
            "SECURITY FAILURE: Protected service 'sshd' must not be queued!"
        )

    def test_queue_rejects_networkmanager(self):
        """NetworkManager must never be queued regardless of context."""
        decision = {
            "actions": [
                {
                    "service": "NetworkManager",
                    "action": "stop",
                    "reason": "test",
                    "estimated_cpu_save": 0.5,
                    "estimated_memory_save_mb": 5,
                    "priority": "low",
                }
            ]
        }
        ids = self.executor.queue_actions_from_decision(decision)
        self.assertEqual(len(ids), 0)

    def test_non_critical_service_gets_queued(self):
        """A low-criticality service action must be successfully queued."""
        decision = {
            "actions": [
                {
                    "service": "baloo_file_indexer",
                    "action": "stop",
                    "reason": "Idle CPU, service consuming resources",
                    "estimated_cpu_save": 4.2,
                    "estimated_memory_save_mb": 85,
                    "priority": "high",
                }
            ]
        }
        ids = self.executor.queue_actions_from_decision(decision)
        self.assertGreater(len(ids), 0,
                           "baloo_file_indexer should be successfully queued")

    def test_executor_status_returns_dict(self):
        """get_status() must return a complete status dict."""
        status = self.executor.get_status()
        self.assertIn("mode", status)
        self.assertIn("demo", status)
        self.assertIn("protected_services_count", status)
        self.assertIn("pending_actions", status)
        self.assertEqual(status["mode"], "dry-run")


# ─────────────────────────────────────────────
#  Action Log Tests
# ─────────────────────────────────────────────
class TestActionLog(unittest.TestCase):
    """Test the persistent action logging and savings accumulation system."""

    def setUp(self):
        """Redirect log to a temp file for test isolation."""
        import action_log
        import tempfile
        self.tmp = tempfile.mktemp(suffix=".json")
        action_log.LOG_FILE = Path(self.tmp)

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def _create_test_action(self, service="test-service", cpu=2.0, mem=50):
        import action_log
        return action_log.create_action(
            service=service,
            action_type="stop",
            reason="Unit test action",
            estimated_cpu_save=cpu,
            estimated_memory_save_mb=mem,
        )

    def test_create_action_returns_string_id(self):
        """create_action() must return a non-empty string ID."""
        action_id = self._create_test_action()
        self.assertIsInstance(action_id, str)
        self.assertGreater(len(action_id), 0)

    def test_created_action_appears_in_pending(self):
        """A newly created action must appear in get_pending_actions()."""
        import action_log
        action_id = self._create_test_action()
        pending_ids = [a["id"] for a in action_log.get_pending_actions()]
        self.assertIn(action_id, pending_ids)

    def test_approve_action_moves_out_of_pending(self):
        """Approving an action must remove it from the pending list."""
        import action_log
        action_id = self._create_test_action()
        success = action_log.approve_action(action_id, approved_by="unit-test")
        self.assertTrue(success)

        pending_ids = [a["id"] for a in action_log.get_pending_actions()]
        self.assertNotIn(action_id, pending_ids)

    def test_reject_action_removes_from_pending(self):
        """Rejecting an action must remove it from the pending list."""
        import action_log
        action_id = self._create_test_action()
        action_log.reject_action(action_id, reason="Test rejection")

        pending_ids = [a["id"] for a in action_log.get_pending_actions()]
        self.assertNotIn(action_id, pending_ids)

    def test_cannot_approve_already_rejected_action(self):
        """An already-rejected action must not be approvable."""
        import action_log
        action_id = self._create_test_action()
        action_log.reject_action(action_id)
        result = action_log.approve_action(action_id)
        self.assertFalse(result)

    def test_savings_accumulate_after_execution(self):
        """Executing an action must increase cumulative savings totals."""
        import action_log
        action_id = self._create_test_action(cpu=5.0, mem=100)
        action_log.approve_action(action_id)
        action_log.mark_executed(action_id, success=True)

        summary = action_log.get_savings_summary()
        self.assertGreater(summary["cumulative_savings"]["cpu_percent_hours"], 0)
        self.assertGreater(summary["cumulative_savings"]["memory_mb_hours"], 0)
        self.assertGreater(summary["cumulative_savings"]["cost_usd"], 0)

    def test_failed_execution_does_not_accumulate_savings(self):
        """A failed execution must not add to cumulative savings."""
        import action_log
        action_id = self._create_test_action(cpu=5.0, mem=100)
        action_log.approve_action(action_id)
        action_log.mark_executed(action_id, success=False, actual_output="timeout")

        summary = action_log.get_savings_summary()
        self.assertEqual(summary["cumulative_savings"]["cost_usd"], 0.0)

    def test_get_savings_summary_structure(self):
        """get_savings_summary() must return a complete summary structure."""
        import action_log
        summary = action_log.get_savings_summary()
        required_keys = [
            "total_actions", "total_approved", "total_rejected",
            "total_executed", "cumulative_savings", "session_start",
            "actions_by_status"
        ]
        for key in required_keys:
            self.assertIn(key, summary, f"Missing summary key: {key}")


# ─────────────────────────────────────────────
#  Collector Factory Tests
# ─────────────────────────────────────────────
class TestCollectorFactory(unittest.TestCase):
    """Test that the factory function returns the correct collector type."""

    def test_demo_mode_returns_demo_collector(self):
        """get_collector('demo') must return a DemoCollector instance."""
        from collector import get_collector, DemoCollector
        c = get_collector("demo")
        self.assertIsInstance(c, DemoCollector)

    def test_live_mode_returns_dynatrace_collector(self):
        """get_collector('live') must return a DynatraceCollector instance."""
        from collector import get_collector, DynatraceCollector
        c = get_collector("live")
        self.assertIsInstance(c, DynatraceCollector)

    def test_default_mode_is_demo(self):
        """Without AGENT_MODE set, get_collector() must default to demo mode."""
        from collector import get_collector, DemoCollector
        env_backup = os.environ.pop("AGENT_MODE", None)
        try:
            c = get_collector()
            self.assertIsInstance(c, DemoCollector)
        finally:
            if env_backup:
                os.environ["AGENT_MODE"] = env_backup


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  Smart-Grid Agent — Unit Test Suite")
    print("=" * 65 + "\n")
    unittest.main(verbosity=2)
