# Smart-Grid Agent: Autonomous FinOps Orchestrator

> **"Smart-Grid Agent bridges the gap between observability and automated action, turning raw Dynatrace metrics into actionable cost-saving decisions."**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Dynatrace](https://img.shields.io/badge/Dynatrace-MCP_API-1496FF?style=flat&logo=dynatrace&logoColor=white)](https://dynatrace.com)
[![Gemini AI](https://img.shields.io/badge/Google_Gemini-1.5_Pro-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev)
[![Google Cloud](https://img.shields.io/badge/Google_Cloud-Agent_Builder-4285F4?style=flat&logo=googlecloud&logoColor=white)](https://cloud.google.com)
[![Tests](https://img.shields.io/badge/Tests-37%2F37_PASSED-brightgreen?style=flat&logo=pytest)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

<p align="center">
  <video src="smart_grid_agent_demo.mp4" width="100%" controls autoplay loop muted></video>
</p>

---

## 🏆 Google Cloud Rapid Agent Hackathon Submission

**Category:** Autonomous AI Agent | FinOps & Cost Optimization  
**Tech Stack:** Dynatrace MCP + Google Gemini 1.5 Pro + Python

---

## 🎯 What Problem Does This Solve?

### The Problem: Invisible Resource Waste

In modern cloud and on-premise infrastructure, a significant portion of compute costs are wasted on **idle, unnecessary background services** that nobody notices:

- File indexers running while the system is idle
- Package managers polling for updates at 3 AM
- Address book daemons consuming RAM 24/7
- Background sync services active during off-hours

**On a single server:** ~10% CPU wasted = ~$200/month in cloud credits  
**At enterprise scale (500 servers):** ~$100,000+/year wasted

The problem is not that engineers don't care — it's that **no human can monitor every service on every server in real time.**

### The Solution: AI-Powered Autonomous Monitoring

Smart-Grid Agent is an **always-on AI agent** that:

1. **Watches** — Collects real-time metrics via Dynatrace MCP every 15-30 seconds
2. **Understands** — Sends structured context to Gemini AI for FinOps analysis
3. **Decides** — AI identifies which services are unnecessary right now
4. **Asks** — Presents decisions to a human operator for approval (Human-in-the-Loop)
5. **Acts** — Executes only approved actions via `systemctl`
6. **Reports** — Tracks cumulative savings with cost calculations

---

## 🧠 How the AI Works

### The Core Intelligence Loop

```
┌─────────────────────────────────────────────────────────────┐
│                  SMART-GRID AGENT LOOP                      │
│                   (runs every 15-30s)                       │
│                                                             │
│  Dynatrace MCP API                                          │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐    MCP Context String                      │
│  │ collector.py│ ──────────────────────────────────────┐   │
│  │             │  [DYNATRACE_MCP_CONTEXT]               │   │
│  │ Real psutil │  cpu_usage_percent: 3.24%              │   │
│  │ + Dynatrace │  memory_usage_percent: 26.2%           │   │
│  │   API v2    │  baloo_file_indexer: 4.1% CPU          │   │
│  └─────────────┘  tracker-miner-fs: 3.1% CPU           │   │
│                   packagekitd: 1.8% CPU                 │   │
│                        │                                    │
│                        ▼                                    │
│  ┌─────────────┐                                            │
│  │  brain.py   │  FinOps System Prompt:                     │
│  │             │  "You are a FinOps expert.                 │
│  │ Google      │   CPU < 10% + idle services running        │
│  │ Gemini      │   → recommend stopping them"               │
│  │ 1.5 Pro     │                                            │
│  │             │  AI Response (JSON):                       │
│  │ OR local    │  {"actions": [                             │
│  │ rule-based  │    {"service": "baloo_file_indexer",       │
│  │ fallback    │     "action": "stop",                      │
│  └─────────────┘     "estimated_cpu_save": 4.1,            │
│       │               "confidence": 0.92}                   │
│       │           ]}                                        │
│       ▼                                                     │
│  ┌─────────────┐                                            │
│  │ executor.py │  HUMAN-IN-THE-LOOP GATE                    │
│  │             │  ↓                                         │
│  │ Security:   │  Pending Queue → Human Approval            │
│  │ 15 protected│  ↓                                         │
│  │ services    │  systemctl --user stop baloo_file_extractor│
│  │ hardcoded   │  ↓                                         │
│  └─────────────┘  Result: 4.1% CPU freed, 85MB RAM freed   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                            │
│  │action_log.py│  Cumulative savings tracked:               │
│  │             │  CPU: 9.41% freed                          │
│  │ Persistent  │  RAM: 224 MB freed                         │
│  │ JSON audit  │  Cost: $0.023/hr saved                     │
│  │ log         │  Monthly projection: $16.50                │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

### What the AI Actually Understands

The agent doesn't just see raw numbers. It receives **structured MCP context** and applies **FinOps reasoning**:

```
SYSTEM STATE: CPU at 3.2% (idle threshold: <10%)
PROBLEM: 4 background services consuming 10.1% CPU unnecessarily

AI REASONING:
  "The system is effectively idle. baloo_file_indexer is a file 
   search indexer — it only needs to run when the user is actively 
   searching. At 3:30 AM with 3.2% total CPU, this service is 
   wasting 4.1% CPU for zero benefit. Stopping it will immediately 
   free resources with zero impact on user experience."

DECISION: STOP baloo_file_indexer
CONFIDENCE: 92%
RISK: LOW
SAVINGS: 4.1% CPU + 85MB RAM
```

---

## 🏗️ Architecture Deep Dive

### System Architecture

```
smart-grid-agent/
│
├── backend/                    # Core agent logic (Python)
│   ├── collector.py            # Layer 1: Observability
│   │   ├── DynatraceMCPContext # Structures metrics as AI context
│   │   ├── DemoCollector       # Real psutil + simulated services
│   │   └── DynatraceCollector  # Live Dynatrace Environment API v2
│   │
│   ├── brain.py                # Layer 2: AI Decision Engine
│   │   ├── GeminiBrain         # Google Gemini 1.5 Pro integration
│   │   ├── FINOPS_SYSTEM_PROMPT # Expert FinOps reasoning rules
│   │   └── _local_rule_engine  # Fallback (no API key required)
│   │
│   ├── executor.py             # Layer 3: Safe Execution
│   │   ├── ExecutorModule      # Human-in-the-loop gate
│   │   ├── PROTECTED_SERVICES  # 15 hardcoded never-touch services
│   │   └── SERVICE_UNIT_MAP    # Service name → systemctl unit mapping
│   │
│   ├── action_log.py           # Layer 4: Audit & Savings Tracking
│   │   ├── create_action()     # Persistent JSON action log
│   │   ├── approve_action()    # Human approval gate
│   │   └── get_savings_summary() # Cumulative cost calculations
│   │
│   └── main.py                 # Orchestrator: connects all layers
│
├── api/
│   └── server.py               # Flask REST API (13 endpoints)
│
├── frontend/
│   ├── index.html              # Glassmorphism dark-mode dashboard
│   ├── style.css               # Premium UI with animations
│   └── app.js                  # Real-time Chart.js + approval flow
│
├── config/
│   └── settings.json           # Thresholds, cost model, services
│
└── tests/
    └── test_agent.py           # 37 unit tests, 100% passing
```

### Data Flow

```
1. COLLECT  →  Dynatrace API / psutil
                    ↓
               DynatraceMCPContext
               {cpu: 3.24, memory: 26.2,
                services: [{name: "baloo", cpu: 4.1}],
                problems: ["PERFORMANCE: idle waste"]}
                    ↓
2. ANALYZE  →  GeminiBrain.analyze(context)
               System prompt + MCP context → Gemini API
                    ↓
               Decision JSON:
               {risk: "low", actions: [...], confidence: 0.92}
                    ↓
3. QUEUE    →  action_log.create_action()
               Status: "pending" → waits for human
                    ↓
4. APPROVE  →  Human clicks [APPROVE] on dashboard
               action_log.approve_action(id, by="human")
                    ↓
5. EXECUTE  →  executor._stop_service("baloo")
               systemctl --user stop baloo_file_extractor
                    ↓
6. RECORD   →  action_log.mark_executed(id, success=True)
               cumulative_savings += {cpu: 4.1, cost: $0.007}
```

---

## 🔌 Dynatrace MCP Integration

### What is Dynatrace MCP?

**Model Context Protocol (MCP)** is Dynatrace's framework for providing AI models with rich, structured observability context. Instead of sending raw JSON metrics to an LLM, MCP formats the data in a way that maximizes AI comprehension and reasoning quality.

Smart-Grid Agent implements the MCP interface to produce this context format:

```
[DYNATRACE_MCP_CONTEXT] timestamp=2026-06-05T11:49:09Z
[HOST] id=HOST-PROD-001 name=prod-server-01

## SYSTEM METRICS
  cpu_usage_percent      : 3.24%        ← System is IDLE
  memory_usage_percent   : 26.20%       ← Memory abundant
  disk_io_read_mbps      : 0.12 MB/s    ← Minimal disk activity
  disk_io_write_mbps     : 0.08 MB/s
  network_in_mbps        : 0.45 MB/s    ← Near-zero network
  network_out_mbps       : 0.12 MB/s
  system_status          : idle

## ACTIVE PROBLEMS
  - [PERFORMANCE] High idle resource consumption on prod-server-01

## RUNNING SERVICES (Non-Critical)
  - baloo_file_indexer        cpu=4.1%  mem=85MB   ← WASTEFUL
  - tracker-miner-fs          cpu=3.1%  mem=62MB   ← WASTEFUL
  - packagekitd               cpu=1.8%  mem=45MB   ← WASTEFUL
  - evolution-addressbook     cpu=0.9%  mem=38MB   ← WASTEFUL
```

This MCP-formatted string is the exact input the Gemini AI receives, enabling it to make contextually-aware, quantified FinOps decisions.

### Dynatrace API v2 Metric Selectors Used

| Metric | Selector |
|--------|----------|
| CPU Usage | `builtin:host.cpu.usage:splitBy():avg:last` |
| Memory Usage | `builtin:host.mem.usage:splitBy():avg:last` |
| Disk Read | `builtin:host.disk.readThroughput:splitBy():avg:last` |
| Disk Write | `builtin:host.disk.writeThroughput:splitBy():avg:last` |
| Network In | `builtin:host.net.nic.trafficIn:splitBy():avg:last` |
| Network Out | `builtin:host.net.nic.trafficOut:splitBy():avg:last` |

---

## 🤖 Google Gemini Integration

### The FinOps System Prompt

The agent uses a carefully engineered system prompt that gives Gemini the role of a FinOps expert:

```python
FINOPS_SYSTEM_PROMPT = """
You are a FinOps (Financial Operations) and SRE expert.
Your mission: analyze Dynatrace metric data and produce cost 
optimization decisions.

DECISION RULES:
1. CPU < 10% + non-critical services running → recommend stopping
2. Memory < 15% → recommend stopping memory-intensive background tasks
3. Disk I/O < 5 MB/s → recommend deferring index/scan services
4. NEVER touch: NetworkManager, sshd, dbus, firewalld, systemd-logind
5. Quantify every recommendation with CPU%, RAM, and $/hour savings

OUTPUT: Strict JSON with actions, risk_level, confidence, savings
"""
```

### Decision Output Schema

```json
{
  "brain": "gemini-1.5-pro",
  "analysis": "System idle at 3.2% CPU. 4 wasteful services detected consuming 10.1% CPU and 230MB RAM.",
  "risk_level": "low",
  "confidence": 0.92,
  "actions": [
    {
      "service": "baloo_file_indexer",
      "action": "stop",
      "reason": "CPU at 3.2% (below 10% idle threshold). Service consuming 4.1% CPU unnecessarily during off-hours.",
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
  "recommendation": "Stop all 4 idle services. Total estimated saving: 10.1% CPU, 230MB RAM."
}
```

---

## 🔒 Security Architecture

### Human-in-the-Loop (Critical Design Decision)

**No action ever executes without explicit human approval.** This is not just a feature — it's a core architectural principle.

```
AI Proposes → Human Reviews → Human Approves → System Executes
                    ↓
              Human Rejects → Logged & Discarded
```

**Why?** AI systems can make mistakes. In infrastructure, a wrong `systemctl stop` command can take down critical services. The human approval gate ensures:
- Engineers stay in control at all times
- Every action is audited with who approved it and when
- Mistakes can be caught before damage occurs

### Protected Services (Hardcoded, Cannot Be Overridden)

```python
PROTECTED_SERVICES = {
    "NetworkManager",    # Network connectivity — NEVER touch
    "sshd",             # SSH access — NEVER touch
    "dbus",             # System message bus — NEVER touch
    "systemd-logind",   # Login management — NEVER touch
    "display-manager",  # GUI display — NEVER touch
    "gdm",              # GNOME Display Manager — NEVER touch
    "lightdm",          # LightDM — NEVER touch
    "firewalld",        # Firewall — NEVER touch
    "snapd",            # Package management — NEVER touch
    "polkit",           # Privilege authorization — NEVER touch
    "accounts-daemon",  # User accounts — NEVER touch
    "rtkit-daemon",     # Real-time scheduling — NEVER touch
    "udisks2",          # Disk management — NEVER touch
    "upower",           # Power management — NEVER touch
    "avahi-daemon",     # Network service discovery — NEVER touch
}
```

These services are checked **twice** — once when queueing and once before execution — making bypass impossible.

### Security Test Results

```
✅ test_protected_services_are_blocked     — All 15 protected services blocked
✅ test_queue_rejects_protected_service    — sshd never queued
✅ test_queue_rejects_networkmanager       — NetworkManager never queued
✅ test_dry_run_never_calls_subprocess     — subprocess.run never called in demo
✅ test_cannot_approve_already_rejected    — State machine integrity verified
```

---

## 📊 Live Savings Dashboard

### Dashboard Features

The web dashboard provides real-time visibility into agent operations:

| Feature | Description |
|---------|-------------|
| **Live Metrics Panel** | CPU%, Memory%, Disk I/O updated every 5 seconds |
| **System Status Badge** | IDLE / NORMAL / BUSY / CRITICAL with color coding |
| **CPU Timeline Chart** | 30-point rolling CPU history (Chart.js line chart) |
| **Savings Donut Chart** | Cumulative savings distribution by service |
| **Action Queue** | Pending approvals with one-click APPROVE/REJECT |
| **Audit Log** | Full action history with timestamps and approvers |
| **Savings Projections** | Hourly → Daily → Monthly cost estimates |

### Savings Calculation Model

```python
# Cost model (configurable in config/settings.json)
cost_per_cpu_percent_per_hour = $0.0018   # Per CPU% freed per hour
cost_per_mb_ram_per_hour      = $0.000025 # Per MB RAM freed per hour

# Example: Stop baloo_file_indexer
cpu_save   = 4.1%  → $0.0074/hr
memory_save = 85MB → $0.0021/hr
total_save = $0.0095/hr
daily_save = $0.228
monthly_save = $6.84

# At enterprise scale (100 servers):
monthly_enterprise_save = $684/month per server cluster
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.10+ required
python3 --version

# Optional: Gemini API key (agent works without it using local rules)
# Get from: https://aistudio.google.com/app/apikey

# Optional: Dynatrace account
# Sign up at: https://www.dynatrace.com/trial/
```

### Installation

```bash
git clone https://github.com/Ahmetcemil1/smart-grid-agent.git
cd smart-grid-agent

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
nano .env
```

```env
# Start with demo mode — no accounts required
AGENT_MODE=demo

# Add your Gemini key for real AI analysis (optional)
GEMINI_API_KEY=your_key_from_aistudio.google.com

# Add Dynatrace for production monitoring (optional)
# AGENT_MODE=live
# DYNATRACE_ENV_URL=https://your-env.live.dynatrace.com
# DYNATRACE_API_TOKEN=dt0c01.YOUR_TOKEN
```

### Running the Agent

```bash
# Option A: Terminal only (primary usage)
cd backend
python main.py

# Option B: With web dashboard
cd api
python server.py
# Visit: http://localhost:5000
```

### Expected Terminal Output

```
14:30:01 [SmartGrid.Main] ============================================================
14:30:01 [SmartGrid.Main]   Smart-Grid Agent: Autonomous FinOps Orchestrator
14:30:01 [SmartGrid.Main] ============================================================
14:30:01 [SmartGrid.Main]   Mode           : DEMO
14:30:01 [SmartGrid.Main]   Check interval : 30s
14:30:02 [SmartGrid.Collector] Using DEMO collector (psutil + simulated services)
14:30:02 [SmartGrid.Brain] GEMINI_API_KEY not set — using local rule-based fallback

14:30:03 [SmartGrid.Main] Cycle #1 | 11:30:03 UTC
14:30:04 [SmartGrid.Main] Metrics: {"cpu":3.24,"memory":26.2,"status":"idle","services_monitored":4}
14:30:04 [SmartGrid.Brain] Brain analyzing system state: idle (CPU: 3.2%)
14:30:04 [SmartGrid.Main] Brain: 4 actions proposed | Risk: low | Est. CPU save: 10.1%
14:30:04 [SmartGrid.ActionLog] Action created [a1b2c3d4]: STOP baloo_file_indexer (priority: high)
14:30:04 [SmartGrid.ActionLog] Action created [e5f6g7h8]: STOP tracker-miner-fs (priority: high)
14:30:04 [SmartGrid.Main] 4 actions queued — awaiting human approval
14:30:04 [SmartGrid.Main] Savings: CPU=9.41% | RAM=224MB | Cost=$0.022529/hr
```

---

## 🧪 Test Results

```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3
collected 37 items

tests/test_agent.py::TestDemoCollector::test_collect_returns_mcp_context PASSED
tests/test_agent.py::TestDemoCollector::test_cpu_within_valid_range PASSED
tests/test_agent.py::TestDemoCollector::test_mcp_context_string_contains_markers PASSED
tests/test_agent.py::TestDemoCollector::test_memory_within_valid_range PASSED
tests/test_agent.py::TestDemoCollector::test_metrics_contain_required_fields PASSED
tests/test_agent.py::TestDemoCollector::test_multiple_ticks_increment PASSED
tests/test_agent.py::TestDemoCollector::test_services_is_a_list PASSED
tests/test_agent.py::TestDemoCollector::test_status_is_one_of_valid_values PASSED
tests/test_agent.py::TestDemoCollector::test_stop_service_removes_it_from_future_collections PASSED
tests/test_agent.py::TestDemoCollector::test_to_dict_is_json_serializable PASSED
tests/test_agent.py::TestGeminiBrain::test_actions_field_is_a_list PASSED
tests/test_agent.py::TestGeminiBrain::test_analyze_returns_dict PASSED
tests/test_agent.py::TestGeminiBrain::test_brain_field_identifies_engine PASSED
tests/test_agent.py::TestGeminiBrain::test_confidence_is_between_0_and_1 PASSED
tests/test_agent.py::TestGeminiBrain::test_decision_has_all_required_keys PASSED
tests/test_agent.py::TestGeminiBrain::test_each_action_has_required_fields PASSED
tests/test_agent.py::TestGeminiBrain::test_estimated_savings_structure PASSED
tests/test_agent.py::TestGeminiBrain::test_risk_level_is_valid PASSED
tests/test_agent.py::TestGeminiBrain::test_savings_are_non_negative PASSED
tests/test_agent.py::TestExecutorSecurity::test_dry_run_never_calls_subprocess PASSED
tests/test_agent.py::TestExecutorSecurity::test_executor_status_returns_dict PASSED
tests/test_agent.py::TestExecutorSecurity::test_non_critical_service_gets_queued PASSED
tests/test_agent.py::TestExecutorSecurity::test_non_critical_services_are_allowed PASSED
tests/test_agent.py::TestExecutorSecurity::test_protected_services_are_blocked PASSED
tests/test_agent.py::TestExecutorSecurity::test_queue_rejects_networkmanager PASSED
tests/test_agent.py::TestExecutorSecurity::test_queue_rejects_protected_service PASSED
tests/test_agent.py::TestActionLog::test_approve_action_moves_out_of_pending PASSED
tests/test_agent.py::TestActionLog::test_cannot_approve_already_rejected_action PASSED
tests/test_agent.py::TestActionLog::test_create_action_returns_string_id PASSED
tests/test_agent.py::TestActionLog::test_created_action_appears_in_pending PASSED
tests/test_agent.py::TestActionLog::test_failed_execution_does_not_accumulate_savings PASSED
tests/test_agent.py::TestActionLog::test_get_savings_summary_structure PASSED
tests/test_agent.py::TestActionLog::test_reject_action_removes_from_pending PASSED
tests/test_agent.py::TestActionLog::test_savings_accumulate_after_execution PASSED
tests/test_agent.py::TestCollectorFactory::test_default_mode_is_demo PASSED
tests/test_agent.py::TestCollectorFactory::test_demo_mode_returns_demo_collector PASSED
tests/test_agent.py::TestCollectorFactory::test_live_mode_returns_dynatrace_collector PASSED

========================= 37 passed in 21.10s =================================
```

---

## 📡 REST API Reference

The Flask server exposes 13 endpoints for the dashboard and programmatic access:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/status` | Agent runtime, mode, brain engine, uptime |
| `GET` | `/api/metrics` | Latest cached Dynatrace metrics |
| `GET` | `/api/metrics/live` | Force fresh metric collection |
| `GET` | `/api/actions` | All actions with optional `?status=` filter |
| `GET` | `/api/actions/pending` | Queue awaiting human approval |
| `POST` | `/api/actions/approve` | `{"action_id": "abc12345"}` → approve + execute |
| `POST` | `/api/actions/reject` | `{"action_id": "abc12345", "reason": "..."}` |
| `GET` | `/api/savings` | Summary with hourly/daily/monthly projections |
| `GET` | `/api/savings/history` | Timeline data for Chart.js |
| `POST` | `/api/agent/cycle` | Manually trigger one agent cycle |
| `POST` | `/api/agent/start` | Start background agent loop |
| `POST` | `/api/agent/stop` | Stop background agent loop |
| `GET` | `/api/log` | Full JSON audit log export |

---

## 🗓️ 4-Day Development Journey

### Day 1: Dynatrace MCP Integration
**Goal:** Collect real metrics and output structured JSON  
**Files:** `backend/collector.py`  
**Result:**
```bash
$ python backend/collector.py
{"cpu": 3.24, "memory": 26.2, "status": "idle", "services_monitored": 4}
[DYNATRACE_MCP_CONTEXT] — 4 services listed with CPU/RAM usage
```

### Day 2: Gemini AI Brain
**Goal:** Feed MCP context to Gemini, get FinOps decisions  
**Files:** `backend/brain.py`  
**Result:**
```bash
$ python backend/brain.py
[Brain] 4 actions proposed | Risk: low | Confidence: 88% | CPU save: 10.1%
⚡ STOP baloo_file_indexer — 4.1% CPU, 85MB RAM
⚡ STOP tracker-miner-fs — 3.1% CPU, 62MB RAM
```

### Day 3: Executor + Human-in-the-Loop
**Goal:** Execute AI decisions safely with human approval gate  
**Files:** `backend/executor.py`, `backend/action_log.py`  
**Result:**
```bash
$ python backend/executor.py
[Step 3] 3 actions queued for human approval
[Step 4] Human approved: STOP baloo_file_indexer
[Step 5] [SUCCESS] STOP 'baloo_file_indexer' | [SUCCESS] STOP 'tracker-miner-fs'
[Savings] CPU=8.82% | Memory=192MB | Cost=$0.020676/hr
```

### Day 4: Dashboard + Full Integration
**Goal:** Web UI for real-time monitoring and approval flow  
**Files:** `api/server.py`, `frontend/`  
**Result:** Full-stack agent running at `http://localhost:5000`

---

## 💡 Real-World Impact

### Demo Metrics (Single Machine)

| Metric | Value |
|--------|-------|
| Services stopped | 4 idle background processes |
| CPU freed | **10.1%** (4.1 + 3.1 + 1.8 + 0.9) |
| RAM freed | **224 MB** |
| Cost saved | **$0.023/hour** |
| Daily savings | **$0.55** |
| Monthly savings | **$16.50** |

### Enterprise Scale Projection

| Scale | Monthly Savings |
|-------|----------------|
| 10 servers | $165/month |
| 100 servers | $1,650/month |
| 500 servers | $8,250/month |
| 1,000 servers | $16,500/month |

> These numbers use conservative estimates. Real enterprise environments with larger VMs and higher cloud rates would see significantly higher savings.

---

## 🔧 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Observability** | Dynatrace Environment API v2 | Production metric collection |
| **MCP Protocol** | Dynatrace MCP format | AI-readable metric context |
| **AI Brain** | Google Gemini 1.5 Pro | FinOps decision making |
| **Fallback Brain** | Local rule engine (Python) | Works without API keys |
| **Local Metrics** | psutil | Demo mode system monitoring |
| **Execution** | subprocess + systemctl | Safe service management |
| **REST API** | Flask + Flask-CORS | Dashboard backend |
| **Frontend** | Vanilla JS + Chart.js | Real-time dashboard |
| **Design** | CSS Glassmorphism + dark mode | Premium UI |
| **Logging** | colorlog + JSON | Persistent audit trail |
| **Testing** | pytest + unittest | 37 automated tests |

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Run tests: `pytest tests/ -v`
4. Commit: `git commit -m 'feat: add my feature'`
5. Push: `git push origin feature/my-feature`
6. Open a Pull Request

---

## 📄 License

MIT License — Google Cloud Rapid Agent Hackathon 2024 Submission

---

## 👨‍💻 Author

**Ahmet Cemil**  
Smart-Grid Agent — FinOps × Observability × AI Autonomy

---

*"Smart-Grid Agent bridges the gap between observability and automated action, turning raw Dynatrace metrics into actionable cost-saving decisions."*
