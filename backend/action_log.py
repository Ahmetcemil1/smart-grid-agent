"""
╔══════════════════════════════════════════════════════════════╗
║  Smart-Grid Agent - Action Logger & Savings Tracker          ║
║  Persistent JSON log with cumulative savings calculation     ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("SmartGrid.ActionLog")

LOG_FILE = Path(__file__).parent.parent / "data" / "action_log.json"


def _load_log() -> dict:
    """Load the action log from disk, creating it if it doesn't exist."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Corrupted action log detected, resetting...")
    return {
        "session_start": datetime.now(timezone.utc).isoformat(),
        "total_actions": 0,
        "total_approved": 0,
        "total_rejected": 0,
        "cumulative_savings": {
            "cpu_percent_hours": 0.0,
            "memory_mb_hours": 0.0,
            "cost_usd": 0.0,
        },
        "actions": [],
    }


def _save_log(log: dict):
    """Persist the action log to disk as JSON."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2, default=str)


def create_action(
    service: str,
    action_type: str,
    reason: str,
    estimated_cpu_save: float,
    estimated_memory_save_mb: float,
    priority: str = "medium",
    brain_decision: dict = None,
) -> str:
    """
    Create a new pending action and add it to the log.

    Args:
        service: Name of the target service
        action_type: stop | restart | throttle | monitor
        reason: Human-readable explanation from AI brain
        estimated_cpu_save: Estimated CPU % to be freed
        estimated_memory_save_mb: Estimated MB RAM to be freed
        priority: high | medium | low
        brain_decision: Full decision dict from brain (for audit trail)

    Returns:
        action_id: Short UUID string identifier
    """
    log = _load_log()
    action_id = str(uuid.uuid4())[:8]

    action = {
        "id": action_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": service,
        "action_type": action_type,
        "reason": reason,
        "priority": priority,
        "status": "pending",
        "estimated_cpu_save": estimated_cpu_save,
        "estimated_memory_save_mb": estimated_memory_save_mb,
        "approved_at": None,
        "approved_by": None,
        "executed_at": None,
        "execution_result": None,
        "actual_savings": None,
    }

    log["actions"].append(action)
    log["total_actions"] += 1
    _save_log(log)

    logger.info(
        f"Action created [{action_id}]: {action_type.upper()} {service} "
        f"(priority: {priority})"
    )
    return action_id


def approve_action(action_id: str, approved_by: str = "human") -> bool:
    """
    Mark an action as approved by a human operator.

    This implements the Human-in-the-Loop gate — no action executes
    until this function is called with explicit human confirmation.

    Returns:
        True if the action was found and approved, False otherwise
    """
    log = _load_log()
    for action in log["actions"]:
        if action["id"] == action_id and action["status"] == "pending":
            action["status"] = "approved"
            action["approved_at"] = datetime.now(timezone.utc).isoformat()
            action["approved_by"] = approved_by
            log["total_approved"] += 1
            _save_log(log)
            logger.info(f"Action approved [{action_id}] by '{approved_by}'")
            return True
    logger.warning(f"Action not found or not pending: [{action_id}]")
    return False


def reject_action(action_id: str, reason: str = "") -> bool:
    """
    Mark an action as rejected by a human operator.

    Returns:
        True if the action was found and rejected, False otherwise
    """
    log = _load_log()
    for action in log["actions"]:
        if action["id"] == action_id and action["status"] == "pending":
            action["status"] = "rejected"
            action["rejected_at"] = datetime.now(timezone.utc).isoformat()
            action["rejection_reason"] = reason
            log["total_rejected"] += 1
            _save_log(log)
            logger.info(f"Action rejected [{action_id}]: {reason}")
            return True
    return False


def mark_executed(action_id: str, success: bool, actual_output: str = "") -> bool:
    """
    Mark an approved action as executed and record actual savings.

    Updates cumulative savings if execution was successful.

    Returns:
        True if the action was found and updated, False otherwise
    """
    log = _load_log()
    for action in log["actions"]:
        if action["id"] == action_id and action["status"] == "approved":
            action["status"] = "executed" if success else "failed"
            action["executed_at"] = datetime.now(timezone.utc).isoformat()
            action["execution_result"] = actual_output

            if success:
                cpu_save = action["estimated_cpu_save"]
                mem_save = action["estimated_memory_save_mb"]
                cost_save = (cpu_save * 0.0018 + mem_save * 0.000025)
                action["actual_savings"] = {
                    "cpu_percent": cpu_save,
                    "memory_mb": mem_save,
                    "cost_per_hour_usd": cost_save,
                }
                # Accumulate global savings totals
                log["cumulative_savings"]["cpu_percent_hours"] += cpu_save
                log["cumulative_savings"]["memory_mb_hours"] += mem_save
                log["cumulative_savings"]["cost_usd"] += cost_save

            _save_log(log)
            status_str = "SUCCESS" if success else "FAILED"
            logger.info(f"Action executed [{action_id}]: {status_str}")
            return True
    return False


def get_pending_actions() -> list:
    """Return all actions currently awaiting human approval."""
    log = _load_log()
    return [a for a in log["actions"] if a["status"] == "pending"]


def get_all_actions(limit: int = 50) -> list:
    """Return the most recent actions (all statuses)."""
    log = _load_log()
    return log["actions"][-limit:]


def get_savings_summary() -> dict:
    """Return cumulative savings statistics and action status distribution."""
    log = _load_log()
    executed = [a for a in log["actions"] if a["status"] == "executed"]

    return {
        "total_actions": log["total_actions"],
        "total_approved": log["total_approved"],
        "total_rejected": log["total_rejected"],
        "total_executed": len(executed),
        "cumulative_savings": log["cumulative_savings"],
        "session_start": log["session_start"],
        "actions_by_status": {
            "pending": len([a for a in log["actions"] if a["status"] == "pending"]),
            "approved": len([a for a in log["actions"] if a["status"] == "approved"]),
            "executed": len(executed),
            "rejected": log["total_rejected"],
            "failed": len([a for a in log["actions"] if a["status"] == "failed"]),
        },
    }


def get_full_log() -> dict:
    """Return the complete action log (for audit trail export)."""
    return _load_log()
