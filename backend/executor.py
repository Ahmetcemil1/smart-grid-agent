"""
╔══════════════════════════════════════════════════════════════╗
║  Smart-Grid Agent - Autonomous Executor Module               ║
║  Day 3: Human-in-the-Loop Action Execution                   ║
║                                                              ║
║  Security Architecture:                                      ║
║  Brain Decision → Pending Queue → Human Approval → Execute  ║
║                                                              ║
║  "Security-First": No action executes without human sign-off ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import logging
import subprocess
import shlex
from datetime import datetime, timezone
from pathlib import Path
import action_log

logger = logging.getLogger("SmartGrid.Executor")

# ─────────────────────────────────────────────
#  Protected services — NEVER stopped by agent
# ─────────────────────────────────────────────
PROTECTED_SERVICES = {
    "NetworkManager",
    "sshd",
    "dbus",
    "systemd-logind",
    "display-manager",
    "gdm",
    "lightdm",
    "firewalld",
    "snapd",
    "polkit",
    "accounts-daemon",
    "rtkit-daemon",
    "udisks2",
    "upower",
    "avahi-daemon",
}

# Service display name → systemctl unit name mapping
SERVICE_UNIT_MAP = {
    "baloo_file_indexer": "baloo_file_extractor",
    "tracker-miner-fs": "tracker-miner-fs-3",
    "packagekitd": "packagekit",
    "evolution-addressbook": "evolution-addressbook-factory",
    "evolution-calendar": "evolution-calendar-factory",
    "gvfs-daemon": "gvfs",
    "colord": "colord",
    "cups": "cups",
    "bluetooth": "bluetooth",
}


class ExecutorModule:
    """
    Human-in-the-Loop Executor with Security-First design.

    Execution flow:
        1. Brain proposes actions → queued as 'pending'
        2. Dashboard displays pending actions to human operator
        3. Human approves or rejects via UI or CLI
        4. Only approved actions are executed via systemctl
        5. All execution is logged with full audit trail

    Security guarantees:
        - PROTECTED_SERVICES list is hardcoded and cannot be bypassed
        - All commands are pre-validated before subprocess execution
        - dry_run=True by default (safe for demo without real side effects)
    """

    def __init__(self, dry_run: bool = True, demo_mode: bool = True):
        """
        Args:
            dry_run: If True, simulate execution without running real commands
            demo_mode: If True, also update the demo collector's stopped state
        """
        self.dry_run = dry_run
        self.demo_mode = demo_mode
        self._demo_collector = None
        logger.info(
            f"Executor initialized | "
            f"{'DRY-RUN (safe simulation)' if dry_run else 'LIVE MODE (real commands)'} | "
            f"Protected services: {len(PROTECTED_SERVICES)}"
        )

    def set_demo_collector(self, collector):
        """Inject demo collector reference to simulate service stops visually."""
        self._demo_collector = collector

    def queue_actions_from_decision(self, decision: dict) -> list:
        """
        Convert brain decision into queued pending actions.

        Each action is validated against the protected services list
        before being added to the pending queue.

        Returns:
            List of created action IDs
        """
        actions = decision.get("actions", [])
        created_ids = []

        for a in actions:
            service = a.get("service", "unknown")

            # Safety gate: never queue protected services
            if self._is_protected(service):
                logger.warning(
                    f"SECURITY BLOCK: Cannot queue action for protected service: {service}"
                )
                continue

            action_id = action_log.create_action(
                service=service,
                action_type=a.get("action", "stop"),
                reason=a.get("reason", "AI recommendation"),
                estimated_cpu_save=a.get("estimated_cpu_save", 0),
                estimated_memory_save_mb=a.get("estimated_memory_save_mb", 0),
                priority=a.get("priority", "medium"),
                brain_decision=decision,
            )
            created_ids.append(action_id)

        if created_ids:
            logger.info(f"Queued {len(created_ids)} actions for human approval")
        return created_ids

    def execute_approved_actions(self) -> list:
        """
        Execute all human-approved actions.

        Only actions with status='approved' are executed.
        Returns list of execution result dicts.
        """
        approved = [
            a for a in action_log.get_all_actions()
            if a["status"] == "approved"
        ]

        results = []
        for action in approved:
            result = self._execute_action(action)
            results.append(result)

        return results

    def _execute_action(self, action: dict) -> dict:
        """Execute a single approved action with full safety validation."""
        action_id = action["id"]
        service = action["service"]
        action_type = action["action_type"]

        logger.info(
            f"Executing action [{action_id}]: {action_type.upper()} {service}"
        )

        # Final safety gate before any execution
        if self._is_protected(service):
            msg = f"SECURITY BLOCK: '{service}' is a protected service — execution refused"
            logger.error(msg)
            action_log.mark_executed(action_id, success=False, actual_output=msg)
            return {"action_id": action_id, "success": False, "reason": msg}

        try:
            if action_type == "stop":
                success, output = self._stop_service(service)
            elif action_type == "restart":
                success, output = self._restart_service(service)
            elif action_type == "throttle":
                success, output = self._throttle_service(service)
            else:
                success, output = False, f"Unknown action type: {action_type}"

            action_log.mark_executed(action_id, success=success, actual_output=output)

            return {
                "action_id": action_id,
                "service": service,
                "action_type": action_type,
                "success": success,
                "output": output,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            msg = f"Execution exception: {str(e)}"
            logger.error(msg)
            action_log.mark_executed(action_id, success=False, actual_output=msg)
            return {"action_id": action_id, "success": False, "reason": msg}

    def _stop_service(self, service: str) -> tuple:
        """
        Stop a non-critical service via systemctl.

        Attempts user-level stop first, then falls back to system-level.
        In dry_run or demo_mode, simulates the stop without real execution.
        """
        unit = SERVICE_UNIT_MAP.get(service, service)

        if self.dry_run or self.demo_mode:
            # Update demo collector state so metrics reflect the stop
            if self._demo_collector:
                self._demo_collector.stop_service(service)
            output = (
                f"[SIMULATED] Command: systemctl --user stop {unit}\n"
                f"Result: Service '{service}' stopped successfully (simulation)"
            )
            logger.info(f"[DRY-RUN] Stopped service: {service} ({unit})")
            return True, output

        # Real execution path
        try:
            # Try user-level systemctl first
            cmd = f"systemctl --user stop {shlex.quote(unit)}"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=15
            )

            if result.returncode == 0:
                output = f"Stopped (user-level): {unit}\n{result.stdout}"
                logger.info(f"Service stopped successfully: {service} ({unit})")
                return True, output
            else:
                # Fallback: system-level (requires passwordless sudo for this command)
                cmd_sys = f"sudo systemctl stop {shlex.quote(unit)}"
                result_sys = subprocess.run(
                    cmd_sys, shell=True, capture_output=True, text=True, timeout=15
                )
                if result_sys.returncode == 0:
                    output = f"Stopped (system-level): {unit}\n{result_sys.stdout}"
                    logger.info(f"System service stopped: {service}")
                    return True, output
                else:
                    output = (
                        f"User-level error: {result.stderr}\n"
                        f"System-level error: {result_sys.stderr}"
                    )
                    logger.warning(f"Could not stop {unit}: {result.stderr}")
                    return False, output

        except subprocess.TimeoutExpired:
            return False, f"Command timed out for service: {unit}"
        except Exception as e:
            return False, f"Execution error: {str(e)}"

    def _restart_service(self, service: str) -> tuple:
        """Restart a service (useful for memory leak recovery)."""
        unit = SERVICE_UNIT_MAP.get(service, service)

        if self.dry_run or self.demo_mode:
            output = f"[SIMULATED] Command: systemctl --user restart {unit}"
            return True, output

        try:
            cmd = f"systemctl --user restart {shlex.quote(unit)}"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=15
            )
            success = result.returncode == 0
            return success, result.stdout if success else result.stderr
        except Exception as e:
            return False, str(e)

    def _throttle_service(self, service: str) -> tuple:
        """
        Throttle a service CPU usage to 5% via systemctl CPUQuota.
        This limits CPU without fully stopping the service.
        """
        unit = SERVICE_UNIT_MAP.get(service, service)

        if self.dry_run or self.demo_mode:
            output = (
                f"[SIMULATED] Command: "
                f"systemctl --user set-property {unit} CPUQuota=5%"
            )
            return True, output

        try:
            cmd = (
                f"systemctl --user set-property "
                f"{shlex.quote(unit)} CPUQuota=5%"
            )
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=15
            )
            success = result.returncode == 0
            return success, f"CPUQuota set to 5% for {unit}"
        except Exception as e:
            return False, str(e)

    def _is_protected(self, service: str) -> bool:
        """
        Check if a service is in the protected list.
        Case-insensitive partial match to catch variants.
        """
        service_lower = service.lower()
        return any(
            protected.lower() in service_lower or service_lower in protected.lower()
            for protected in PROTECTED_SERVICES
        )

    def get_status(self) -> dict:
        """Return current executor configuration status."""
        return {
            "mode": "dry-run" if self.dry_run else "live",
            "demo": self.demo_mode,
            "protected_services_count": len(PROTECTED_SERVICES),
            "pending_actions": len(action_log.get_pending_actions()),
        }


# ─────────────────────────────────────────────
#  CLI test entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    import colorlog
    from collector import get_collector
    from brain import GeminiBrain

    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    print("\n" + "=" * 65)
    print("  Smart-Grid Agent — Day 3: Executor + Human-in-the-Loop")
    print("=" * 65)

    collector = get_collector("demo")
    brain = GeminiBrain()
    executor = ExecutorModule(dry_run=True, demo_mode=True)
    executor.set_demo_collector(collector)

    # Step 1: Collect metrics
    ctx = collector.collect()
    print(f"\n[Step 1] Metrics collected — CPU: {ctx.metrics['cpu']:.1f}%, "
          f"Status: {ctx.metrics['status']}")

    # Step 2: Brain decision
    decision = brain.analyze(ctx)
    print(f"[Step 2] Brain decision: {len(decision.get('actions', []))} actions proposed")
    print(f"         Analysis: {decision.get('analysis', '')[:80]}...")

    # Step 3: Queue for human approval
    queued_ids = executor.queue_actions_from_decision(decision)
    print(f"[Step 3] {len(queued_ids)} actions queued for human approval")

    # Step 4: Simulate human approval
    print("\n[Step 4] Simulating human operator approval...")
    pending = action_log.get_pending_actions()
    for pa in pending:
        print(f"  Approving: {pa['action_type'].upper()} '{pa['service']}'")
        action_log.approve_action(pa["id"], approved_by="human-operator-demo")

    # Step 5: Execute approved actions
    print("\n[Step 5] Executing approved actions...")
    results = executor.execute_approved_actions()
    for r in results:
        status = "SUCCESS" if r.get("success") else "FAILED"
        print(f"  [{status}] {r.get('action_type', '?').upper()} '{r.get('service', '?')}'")

    # Step 6: Savings report
    summary = action_log.get_savings_summary()
    print(f"\n[Savings Report]")
    print(f"  Total actions  : {summary['total_actions']}")
    print(f"  Approved       : {summary['total_approved']}")
    print(f"  Executed       : {summary['total_executed']}")
    print(f"  CPU freed      : {summary['cumulative_savings']['cpu_percent_hours']:.2f}%")
    print(f"  Memory freed   : {summary['cumulative_savings']['memory_mb_hours']:.0f} MB")
    print(f"  Cost saved     : ${summary['cumulative_savings']['cost_usd']:.6f}/hr")
    print("\n✅ Day 3 Complete: Executor + Human-in-the-Loop operational")
