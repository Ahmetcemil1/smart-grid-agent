# Smart-Grid Agent: Autonomous FinOps Orchestrator

> **"Smart-Grid Agent bridges the gap between observability and automated action, turning raw Dynatrace metrics into actionable cost-saving decisions."**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Dynatrace](https://img.shields.io/badge/Dynatrace-MCP-1496FF?style=flat&logo=dynatrace&logoColor=white)](https://dynatrace.com)
[![Gemini AI](https://img.shields.io/badge/Gemini-1.5_Pro-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

---

## Overview

Smart-Grid Agent is an autonomous **FinOps Orchestrator** that:

1. **Collects** real-time system metrics via **Dynatrace MCP (Model Context Protocol)**
2. **Analyzes** them using **Google Gemini AI** as a FinOps expert brain
3. **Recommends** cost-saving actions with quantified resource savings
4. **Executes** approved actions via `systemctl` — only after **human confirmation**
5. **Tracks** all savings cumulatively in a live dashboard

### Core Pipeline (Terminal-Based)

```
Dynatrace MCP API
       │
       ▼
  collector.py  ──→  {"cpu": 3.2, "memory": 12.1, "status": "idle"}
       │
       ▼
   brain.py     ──→  "Stop baloo_file_indexer — consuming 4.2% CPU while idle"
       │
       ▼  [Human-in-the-Loop Approval Gate]
       │
  executor.py   ──→  systemctl --user stop baloo_file_extractor
       │
       ▼
  action_log.py ──→  Savings: 4.2% CPU, 85MB RAM freed per hour
```

---

## Project Structure

```
smart-grid-agent/
├── backend/
│   ├── collector.py      # Dynatrace MCP metrics collector (real psutil + API)
│   ├── brain.py          # Gemini AI FinOps decision engine
│   ├── executor.py       # Service manager with human-in-the-loop gate
│   ├── action_log.py     # Persistent audit log + savings tracker
│   └── main.py           # Main orchestrator (terminal entry point)
├── api/
│   └── server.py         # Flask REST API (serves the dashboard)
├── frontend/
│   ├── index.html        # Savings Dashboard UI
│   ├── style.css         # Dark mode glassmorphism design
│   └── app.js            # Real-time chart & approval interface
├── config/
│   └── settings.json     # Thresholds, service definitions, cost model
├── tests/
│   └── test_agent.py     # Unit & security tests
├── data/                 # Auto-created: action_log.json, agent.log
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Ahmetcemil1/smart-grid-agent.git
cd smart-grid-agent

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
nano .env
```

```env
# Demo mode — no Dynatrace account required
AGENT_MODE=demo

# Optional: enable real Gemini AI analysis
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: connect to a live Dynatrace environment
# AGENT_MODE=live
# DYNATRACE_ENV_URL=https://your-env.live.dynatrace.com
# DYNATRACE_API_TOKEN=dt0c01.XXXXXXXXXX...
```

### 3. Run in Terminal (Primary Usage)

```bash
# ── Day 1: Test metrics collection ──────────────────────────
cd backend
python collector.py
# Output: {"cpu": 3.24, "memory": 45.1, "status": "idle", ...}

# ── Day 2: Test AI brain decision ───────────────────────────
python brain.py
# Output: [Brain] 4 actions proposed | CPU save: 10.1%

# ── Day 3: Test executor + approval flow ────────────────────
python executor.py
# Output: Queued → Approved → Executed → Savings logged

# ── Full agent: continuous loop ─────────────────────────────
python main.py
# Press Ctrl+C to stop
```

**Expected terminal output:**

```
14:30:01 [SmartGrid.Main        ] INFO ============================================================
14:30:01 [SmartGrid.Main        ] INFO   Smart-Grid Agent: Autonomous FinOps Orchestrator
14:30:01 [SmartGrid.Main        ] INFO ============================================================
14:30:01 [SmartGrid.Collector   ] INFO Using DEMO collector (psutil + simulated services)
14:30:01 [SmartGrid.Brain       ] WARNING GEMINI_API_KEY not set — using local rule-based fallback
14:30:02 [SmartGrid.Main        ] INFO Cycle #1 | 14:30:02 UTC
14:30:03 [SmartGrid.Main        ] INFO Metrics: {"cpu":3.24,"memory":45.1,"status":"idle","services_monitored":4}
14:30:03 [SmartGrid.Brain       ] INFO Brain analyzing system state: idle (CPU: 3.2%)
14:30:03 [SmartGrid.Main        ] INFO Brain: 4 actions proposed | Risk: low | Est. CPU save: 10.1%
14:30:03 [SmartGrid.Main        ] INFO 4 actions queued — awaiting human approval
14:30:03 [SmartGrid.Main        ] INFO Savings: CPU=0.00% | RAM=0MB | Cost=$0.000000/hr
```

### 4. Dashboard (Optional — Approval UI)

```bash
cd api
python server.py
# Open: http://localhost:5000
```

---

## Dynatrace MCP Integration

This project uses the **Dynatrace Model Context Protocol (MCP)** to structure observability data as rich AI-readable context.

### API Token Setup

1. Go to Dynatrace console → **Settings → Access Tokens**
2. Create a token with these scopes:
   - `metrics.read`
   - `entities.read`
   - `problems.read`
3. Add to `.env`:

```env
AGENT_MODE=live
DYNATRACE_ENV_URL=https://abc12345.live.dynatrace.com
DYNATRACE_API_TOKEN=dt0c01.XXXXXXXXXX...
```

### MCP Context Format

The collector produces structured context that the AI brain consumes:

```
[DYNATRACE_MCP_CONTEXT] timestamp=2024-06-05T11:30:00+00:00
[HOST] id=HOST-DEMO-001 name=localhost (demo)

## SYSTEM METRICS
  cpu_usage_percent      : 3.24%
  memory_usage_percent   : 45.10%
  disk_io_read_mbps      : 12.345 MB/s
  disk_io_write_mbps     : 4.123 MB/s
  system_status          : idle

## ACTIVE PROBLEMS
  - [PERFORMANCE] High idle resource consumption detected

## RUNNING SERVICES (Non-Critical)
  - baloo_file_indexer           cpu=4.1%  mem=85MB  status=running
  - tracker-miner-fs             cpu=3.1%  mem=62MB  status=running
  - packagekitd                  cpu=1.8%  mem=45MB  status=running
  - evolution-addressbook        cpu=0.9%  mem=38MB  status=running
```

---

## Gemini AI FinOps Brain

### System Prompt

```
You are a FinOps (Financial Operations) and SRE expert.
If CPU usage is below 10% and non-critical services are running,
recommend stopping them and provide quantified savings estimates.
```

### Decision Output Example

```json
{
  "analysis": "System is idle (CPU: 3.2%). 4 unnecessary services detected consuming 10.1% CPU.",
  "risk_level": "low",
  "actions": [
    {
      "service": "baloo_file_indexer",
      "action": "stop",
      "reason": "CPU at 3.2% (below 10% idle threshold). Service consuming 4.1% CPU unnecessarily.",
      "estimated_cpu_save": 4.1,
      "estimated_memory_save_mb": 85,
      "priority": "high"
    }
  ],
  "estimated_total_savings": {
    "cpu_percent": 10.1,
    "memory_mb": 230,
    "cost_per_hour_usd": 0.0238
  },
  "confidence": 0.92
}
```

---

## Security: Human-in-the-Loop

**No action ever executes automatically.** Every AI recommendation goes through a human approval gate:

```
Brain Decision
      │
      ▼
  Pending Queue ──→ Human Reviews
      │                   │
      │          ┌────────┴────────┐
      │          ▼                 ▼
      │       APPROVE           REJECT
      │          │                 │
      │          ▼                 ▼
      │       Execute           Logged only
      │          │
      ▼          ▼
   Audit Log ← Savings Recorded
```

### Protected Services (Never Touched)

```python
PROTECTED_SERVICES = {
    "NetworkManager", "sshd", "dbus",
    "systemd-logind", "display-manager",
    "gdm", "firewalld", "snapd", "polkit"
}
```

Any action targeting a protected service is **silently blocked** before reaching the queue.

---

## Executor: Real System Commands

When running in **live mode**, the executor issues real systemctl commands:

```bash
# Stop an idle service
systemctl --user stop baloo_file_extractor

# Throttle CPU to 5% quota without stopping
systemctl --user set-property tracker-miner-fs-3 CPUQuota=5%

# Restart a memory-leaking service
systemctl --user restart packagekit
```

| Mode | Behavior |
|------|----------|
| `AGENT_MODE=demo` | Simulates commands — safe, no real side effects |
| `AGENT_MODE=live` | Issues real `systemctl` commands after human approval |

---

## Savings Dashboard

Measured outcomes after agent runs in demo mode:

| Metric | Value |
|--------|-------|
| CPU Freed | ~10.1% (4 services stopped) |
| Memory Freed | ~230 MB |
| Hourly Cost Saving | ~$0.023 |
| Daily Projection | ~$0.55 |
| Monthly Projection | ~$16.50 |

> In a real Dynatrace environment at enterprise scale, savings multiply significantly across hundreds of monitored hosts.

---

## Running Tests

```bash
cd tests
python -m pytest test_agent.py -v
```

**Test coverage:**

| Test Class | What it validates |
|------------|-------------------|
| `TestDemoCollector` | MCP context format, metric ranges, service simulation |
| `TestGeminiBrain` | Decision schema, confidence range, action structure |
| `TestExecutorSecurity` | Protected service blocking, dry-run behavior |
| `TestActionLog` | CRUD operations, approval flow, savings accumulation |
| `TestGetCollectorFactory` | Factory mode selection |

---

## 4-Day Development Timeline

| Day | Task | Deliverable |
|-----|------|-------------|
| **Day 1** | Dynatrace MCP integration | `collector.py` → JSON metrics in terminal |
| **Day 2** | Gemini FinOps Brain | `brain.py` → "Stop service X" decisions |
| **Day 3** | Executor + Human-in-the-Loop | `executor.py` → real `systemctl stop` |
| **Day 4** | Dashboard + Documentation | `server.py` → Savings Dashboard |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Observability | Dynatrace Environment API v2 + MCP Protocol |
| AI Brain | Google Gemini 1.5 Pro |
| Local Metrics | psutil |
| Action Execution | Python subprocess + systemctl |
| REST API | Flask + Flask-CORS |
| Dashboard | Vanilla JS + Chart.js |
| Logging | colorlog + JSON persistent audit log |
| Testing | unittest + pytest |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/status` | Agent runtime status |
| `GET` | `/api/metrics` | Latest cached metrics |
| `GET` | `/api/metrics/live` | Force fresh collection |
| `GET` | `/api/actions` | All actions (filterable) |
| `GET` | `/api/actions/pending` | Pending approval queue |
| `POST` | `/api/actions/approve` | Approve an action |
| `POST` | `/api/actions/reject` | Reject an action |
| `GET` | `/api/savings` | Savings summary + projections |
| `GET` | `/api/savings/history` | Timeline for chart data |
| `POST` | `/api/agent/cycle` | Trigger one agent cycle |
| `GET` | `/api/log` | Full audit log export |

---

## License

MIT License — Competition demo project.

---

*Smart-Grid Agent — FinOps × AI × Observability*
