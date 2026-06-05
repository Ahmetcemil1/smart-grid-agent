"""
╔══════════════════════════════════════════════════════════════╗
║  Smart-Grid Agent - Flask REST API Server                    ║
║  Bridges the backend agent with the Dashboard frontend       ║
║                                                              ║
║  Endpoints:                                                  ║
║    GET  /api/status            Agent status + runtime info   ║
║    GET  /api/metrics           Current system metrics        ║
║    GET  /api/metrics/live      Force fresh metric collection  ║
║    GET  /api/actions           All actions (filterable)      ║
║    GET  /api/actions/pending   Pending approval queue        ║
║    POST /api/actions/approve   Approve an action             ║
║    POST /api/actions/reject    Reject an action              ║
║    GET  /api/savings           Savings summary               ║
║    GET  /api/savings/history   Timeline for chart data       ║
║    POST /api/agent/cycle       Trigger one agent cycle       ║
║    POST /api/agent/start       Start background loop         ║
║    POST /api/agent/stop        Stop background loop          ║
║    GET  /api/log               Full audit log export         ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import logging
import threading
import time
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Make backend modules importable
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from collector import get_collector
from brain import GeminiBrain
from executor import ExecutorModule
import action_log

from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────────────
#  Flask App Setup
# ─────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder=str(Path(__file__).parent.parent / "frontend"),
)
CORS(app, origins="*")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartGrid.API")

# ─────────────────────────────────────────────
#  Component Initialization
# ─────────────────────────────────────────────
_mode = os.getenv("AGENT_MODE", "demo")
collector = get_collector(_mode)
brain = GeminiBrain()
executor = ExecutorModule(
    dry_run=(_mode == "demo"),
    demo_mode=(_mode == "demo"),
)
executor.set_demo_collector(collector if _mode == "demo" else None)

# Shared agent state (thread-safe via lock)
_agent_state = {
    "running": False,
    "tick": 0,
    "last_metrics": None,
    "last_decision": None,
    "last_cycle_time": None,
    "errors": [],
}
_agent_lock = threading.Lock()


# ─────────────────────────────────────────────
#  Background Agent Thread
# ─────────────────────────────────────────────
def _agent_loop():
    """
    Background thread: continuously runs agent cycles.
    Automatically queues actions when system is idle.
    """
    interval = int(os.getenv("CHECK_INTERVAL", "15"))
    logger.info(f"Background agent started (interval: {interval}s)")

    while _agent_state["running"]:
        try:
            mcp_context = collector.collect()
            decision = brain.analyze(mcp_context)

            with _agent_lock:
                _agent_state["tick"] += 1
                _agent_state["last_metrics"] = mcp_context.to_dict()
                _agent_state["last_decision"] = decision
                _agent_state["last_cycle_time"] = datetime.now(timezone.utc).isoformat()

            # Queue actions only when system is idle
            cpu = mcp_context.metrics.get("cpu", 100)
            if cpu < 15:
                executor.queue_actions_from_decision(decision)

            # Execute any previously approved actions
            executor.execute_approved_actions()

        except Exception as e:
            logger.error(f"Agent loop error: {e}")
            with _agent_lock:
                _agent_state["errors"].append({
                    "time": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                })
                _agent_state["errors"] = _agent_state["errors"][-10:]

        time.sleep(interval)


# ─────────────────────────────────────────────
#  API Routes
# ─────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    """Return agent runtime status and configuration."""
    with _agent_lock:
        return jsonify({
            "status": "running" if _agent_state["running"] else "stopped",
            "tick": _agent_state["tick"],
            "mode": _mode,
            "last_cycle": _agent_state["last_cycle_time"],
            "brain_available": brain._available,
            "brain_engine": "gemini-pro" if brain._available else "local-rule-engine",
            "version": "1.0.0",
            "uptime_seconds": _agent_state["tick"] * int(os.getenv("CHECK_INTERVAL", "15")),
        })


@app.route("/api/metrics")
def api_metrics():
    """Return most recent cached metrics, or collect fresh if none cached."""
    with _agent_lock:
        cached = _agent_state.get("last_metrics")

    if cached:
        return jsonify(cached)

    try:
        mcp_context = collector.collect()
        return jsonify(mcp_context.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/metrics/live")
def api_metrics_live():
    """Force a fresh metric collection (bypasses cache)."""
    try:
        mcp_context = collector.collect()
        with _agent_lock:
            _agent_state["last_metrics"] = mcp_context.to_dict()
        return jsonify(mcp_context.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/actions")
def api_actions():
    """Return all actions with optional status filter and limit."""
    status_filter = request.args.get("status")
    limit = int(request.args.get("limit", 50))
    actions = action_log.get_all_actions(limit=limit)

    if status_filter:
        actions = [a for a in actions if a["status"] == status_filter]

    return jsonify({"actions": actions, "count": len(actions)})


@app.route("/api/actions/pending")
def api_pending_actions():
    """Return all actions currently awaiting human approval."""
    pending = action_log.get_pending_actions()
    return jsonify({"pending": pending, "count": len(pending)})


@app.route("/api/actions/approve", methods=["POST"])
def api_approve_action():
    """
    Approve a pending action (Human-in-the-Loop gate).
    Immediately executes the action after approval.
    """
    data = request.get_json()
    if not data or "action_id" not in data:
        return jsonify({"error": "action_id is required"}), 400

    action_id = data["action_id"]
    approved_by = data.get("approved_by", "human-dashboard")

    success = action_log.approve_action(action_id, approved_by=approved_by)

    if success:
        results = executor.execute_approved_actions()
        return jsonify({
            "success": True,
            "action_id": action_id,
            "executed": results,
            "message": f"Action {action_id} approved and executed successfully",
        })
    else:
        return jsonify({
            "success": False,
            "error": f"Action {action_id} not found or already processed",
        }), 404


@app.route("/api/actions/reject", methods=["POST"])
def api_reject_action():
    """Reject a pending action (Human-in-the-Loop rejection)."""
    data = request.get_json()
    if not data or "action_id" not in data:
        return jsonify({"error": "action_id is required"}), 400

    action_id = data["action_id"]
    reason = data.get("reason", "Rejected by operator")

    success = action_log.reject_action(action_id, reason=reason)

    if success:
        return jsonify({
            "success": True,
            "action_id": action_id,
            "message": f"Action {action_id} rejected",
        })
    else:
        return jsonify({
            "success": False,
            "error": f"Action {action_id} not found or already processed",
        }), 404


@app.route("/api/savings")
def api_savings():
    """Return savings summary with hourly/daily/monthly projections."""
    summary = action_log.get_savings_summary()
    cumulative = summary["cumulative_savings"]

    runtime_seconds = _agent_state["tick"] * int(os.getenv("CHECK_INTERVAL", "15"))
    runtime_hours = runtime_seconds / 3600
    hourly_rate = cumulative["cost_usd"] / max(runtime_hours, 0.001)

    summary["projections"] = {
        "hourly_cost_save_usd": round(hourly_rate, 6),
        "daily_cost_save_usd": round(hourly_rate * 24, 4),
        "monthly_cost_save_usd": round(hourly_rate * 24 * 30, 2),
        "runtime_hours": round(runtime_hours, 3),
    }

    return jsonify(summary)


@app.route("/api/savings/history")
def api_savings_history():
    """Return executed action timeline for chart rendering."""
    log = action_log.get_full_log()
    executed = [a for a in log.get("actions", []) if a["status"] == "executed"]

    timeline = []
    cumulative_cpu = 0.0
    cumulative_cost = 0.0
    for a in executed:
        savings = a.get("actual_savings", {})
        cumulative_cpu += savings.get("cpu_percent", 0)
        cumulative_cost += savings.get("cost_per_hour_usd", 0)
        timeline.append({
            "timestamp": a.get("executed_at"),
            "service": a.get("service"),
            "cpu_saved": savings.get("cpu_percent", 0),
            "memory_saved_mb": savings.get("memory_mb", 0),
            "cumulative_cpu": round(cumulative_cpu, 2),
            "cumulative_cost": round(cumulative_cost, 6),
        })

    return jsonify({"timeline": timeline, "total_executed": len(executed)})


@app.route("/api/agent/cycle", methods=["POST"])
def api_trigger_cycle():
    """Manually trigger one complete agent cycle."""
    try:
        mcp_context = collector.collect()
        decision = brain.analyze(mcp_context)

        cpu = mcp_context.metrics.get("cpu", 100)
        new_ids = []
        if cpu < 15:
            new_ids = executor.queue_actions_from_decision(decision)

        executed = executor.execute_approved_actions()
        savings = action_log.get_savings_summary()

        with _agent_lock:
            _agent_state["tick"] += 1
            _agent_state["last_metrics"] = mcp_context.to_dict()
            _agent_state["last_decision"] = decision
            _agent_state["last_cycle_time"] = datetime.now(timezone.utc).isoformat()

        return jsonify({
            "success": True,
            "metrics": mcp_context.metrics,
            "decision_actions": len(decision.get("actions", [])),
            "new_actions_queued": len(new_ids),
            "executed": len(executed),
            "savings": savings,
            "decision": decision,
        })
    except Exception as e:
        logger.error(f"Manual cycle error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/agent/start", methods=["POST"])
def api_start_agent():
    """Start the background agent loop."""
    if not _agent_state["running"]:
        _agent_state["running"] = True
        thread = threading.Thread(target=_agent_loop, daemon=True)
        thread.start()
        return jsonify({"success": True, "message": "Background agent started"})
    return jsonify({"success": False, "message": "Agent is already running"})


@app.route("/api/agent/stop", methods=["POST"])
def api_stop_agent():
    """Stop the background agent loop."""
    _agent_state["running"] = False
    return jsonify({"success": True, "message": "Agent stopped"})


@app.route("/api/log")
def api_log():
    """Return the full action audit log."""
    return jsonify(action_log.get_full_log())


# ─────────────────────────────────────────────
#  Static Frontend Serving
# ─────────────────────────────────────────────
@app.route("/")
def serve_dashboard():
    """Serve the main dashboard HTML."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    """Serve static frontend assets (CSS, JS)."""
    return send_from_directory(app.static_folder, filename)


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "5000"))

    # Auto-start background agent loop
    _agent_state["running"] = True
    agent_thread = threading.Thread(target=_agent_loop, daemon=True)
    agent_thread.start()

    logger.info(f"Smart-Grid Agent API server running at http://{host}:{port}")
    logger.info(f"Dashboard:  http://localhost:{port}/")
    logger.info(f"API Status: http://localhost:{port}/api/status")

    app.run(host=host, port=port, debug=False, use_reloader=False)
