"""
╔══════════════════════════════════════════════════════════════╗
║  Smart-Grid Agent - Main Orchestrator Loop                   ║
║  Connects: Collector → Brain → Executor → Action Log         ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import signal
import logging
import colorlog
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from collector import get_collector
from brain import GeminiBrain
from executor import ExecutorModule
import action_log

from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────
#  Logging Configuration
# ─────────────────────────────────────────────
def setup_logging():
    """Configure colorized console logging and persistent file logging."""
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(name)-22s] %(levelname)s%(reset)s %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG":    "cyan",
                "INFO":     "green",
                "WARNING":  "yellow",
                "ERROR":    "red",
                "CRITICAL": "bold_red",
            },
        )
    )

    # Persistent file log
    log_dir = Path(__file__).parent.parent / "data"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "agent.log")
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.addHandler(handler)
    root.addHandler(file_handler)
    root.setLevel(logging.INFO)


logger = logging.getLogger("SmartGrid.Main")


# ─────────────────────────────────────────────
#  Orchestrator
# ─────────────────────────────────────────────
class SmartGridOrchestrator:
    """
    Main orchestrator that runs the continuous agent loop.

    Each cycle:
        1. Collect Dynatrace metrics (via MCP context)
        2. Send to Gemini Brain for FinOps analysis
        3. Queue recommended actions for human approval
        4. Execute any previously approved actions
        5. Update and report savings log
    """

    def __init__(self):
        self.mode = os.getenv("AGENT_MODE", "demo")
        self.interval = int(os.getenv("CHECK_INTERVAL", "30"))
        self._running = False
        self._tick = 0
        self._last_decision = None
        self._last_metrics = None

        logger.info("=" * 60)
        logger.info("  Smart-Grid Agent: Autonomous FinOps Orchestrator")
        logger.info("=" * 60)
        logger.info(f"  Mode           : {self.mode.upper()}")
        logger.info(f"  Check interval : {self.interval}s")
        logger.info(f"  Log file       : data/agent.log")
        logger.info("=" * 60)

        # Initialize components
        self.collector = get_collector(self.mode)
        self.brain = GeminiBrain()
        self.executor = ExecutorModule(
            dry_run=(self.mode == "demo"),
            demo_mode=(self.mode == "demo"),
        )
        self.executor.set_demo_collector(
            self.collector if self.mode == "demo" else None
        )

    def run_cycle(self) -> dict:
        """
        Execute one complete agent cycle.

        Returns:
            dict summarizing the cycle results
        """
        self._tick += 1
        cycle_start = datetime.now(timezone.utc)

        logger.info(f"{'─' * 55}")
        logger.info(
            f"Cycle #{self._tick} | {cycle_start.strftime('%H:%M:%S UTC')}"
        )

        # ── Step 1: Collect Metrics ──────────────────────────────
        try:
            mcp_context = self.collector.collect()
            self._last_metrics = mcp_context.metrics
            m = mcp_context.metrics

            # Structured JSON output (Day 1 deliverable)
            output_json = {
                "cpu": round(m["cpu"], 2),
                "memory": round(m["memory"], 2),
                "disk_io_read_mbps": round(m.get("disk_io_read", 0), 3),
                "disk_io_write_mbps": round(m.get("disk_io_write", 0), 3),
                "network_in_mbps": round(m.get("network_in", 0), 3),
                "status": m["status"],
                "services_monitored": len(m.get("services", [])),
                "tick": self._tick,
                "timestamp": cycle_start.isoformat(),
            }
            logger.info(
                f"Metrics: {json.dumps(output_json, separators=(',', ':'))}"
            )

        except Exception as e:
            logger.error(f"Collector failed: {e}")
            return {"success": False, "error": str(e)}

        # ── Step 2: Brain Analysis ───────────────────────────────
        try:
            decision = self.brain.analyze(mcp_context)
            self._last_decision = decision
            proposed = len(decision.get("actions", []))
            savings = decision.get("estimated_total_savings", {})
            logger.info(
                f"Brain: {proposed} actions proposed | "
                f"Risk: {decision.get('risk_level', '?')} | "
                f"Est. CPU save: {savings.get('cpu_percent', 0):.1f}%"
            )
        except Exception as e:
            logger.error(f"Brain analysis failed: {e}")
            decision = {"actions": []}

        # ── Step 3: Queue Actions for Human Approval ─────────────
        new_action_ids = []
        if decision.get("actions"):
            cpu = m.get("cpu", 100)
            # Only queue when system is actually idle
            if cpu < 15 or decision.get("risk_level") == "high":
                new_action_ids = self.executor.queue_actions_from_decision(decision)
                if new_action_ids:
                    logger.info(
                        f"{len(new_action_ids)} actions queued — awaiting human approval"
                    )
            else:
                logger.info(
                    f"CPU at {cpu:.1f}% — no urgent actions this cycle"
                )

        # ── Step 4: Execute Approved Actions ─────────────────────
        executed_results = self.executor.execute_approved_actions()
        if executed_results:
            for r in executed_results:
                status = "OK" if r.get("success") else "FAIL"
                logger.info(
                    f"[{status}] Executed: {r.get('action_type', '?').upper()} "
                    f"'{r.get('service', '?')}'"
                )

        # ── Step 5: Savings Summary ──────────────────────────────
        summary = action_log.get_savings_summary()
        cum = summary["cumulative_savings"]
        logger.info(
            f"Savings: CPU={cum['cpu_percent_hours']:.2f}% | "
            f"RAM={cum['memory_mb_hours']:.0f}MB | "
            f"Cost=${cum['cost_usd']:.6f}/hr"
        )

        duration_ms = (datetime.now(timezone.utc) - cycle_start).total_seconds() * 1000

        return {
            "success": True,
            "tick": self._tick,
            "timestamp": cycle_start.isoformat(),
            "metrics": output_json,
            "decision": decision,
            "new_actions_queued": new_action_ids,
            "executed": executed_results,
            "savings": summary,
            "duration_ms": round(duration_ms, 1),
        }

    def start(self):
        """Start the continuous orchestrator loop (runs until Ctrl+C)."""
        self._running = True

        def shutdown(sig, frame):
            logger.info("Shutdown signal received. Stopping agent gracefully...")
            self._running = False
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        logger.info(
            f"Agent started. Running every {self.interval}s. Press Ctrl+C to stop."
        )

        while self._running:
            self.run_cycle()
            if self._running:
                logger.info(f"Next cycle in {self.interval}s...")
                time.sleep(self.interval)

    def run_once(self) -> dict:
        """Execute a single cycle (used by API server)."""
        return self.run_cycle()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    setup_logging()

    orchestrator = SmartGridOrchestrator()

    if "--once" in sys.argv:
        # Single cycle mode (useful for testing)
        result = orchestrator.run_once()
        print(json.dumps(result, indent=2, default=str))
    else:
        # Continuous loop mode
        orchestrator.start()
