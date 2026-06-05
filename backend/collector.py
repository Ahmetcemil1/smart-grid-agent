"""
╔══════════════════════════════════════════════════════════════╗
║  Smart-Grid Agent - Dynatrace Metrics Collector              ║
║  Day 1: Environment API Integration                          ║
║  Supports: Live Dynatrace API + Demo/Mock mode               ║
╚══════════════════════════════════════════════════════════════╝

Dynatrace Environment API v2 endpoints used:
  - /api/v2/metrics/query  → CPU, Memory, Disk I/O metrics
  - /api/v2/problems       → Active problems/alerts
  - /api/v2/entities       → Host entity discovery
"""

import os
import json
import time
import random
import logging
import math
import psutil
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("SmartGrid.Collector")


# ─────────────────────────────────────────────
#  Dynatrace MCP (Model Context Protocol) Layer
# ─────────────────────────────────────────────
class DynatraceMCPContext:
    """
    Implements the Dynatrace MCP (Model Context Protocol) interface.

    This class structures Dynatrace metrics as rich context objects
    for consumption by AI agents (Gemini Brain).

    MCP Format: Structured context with typed fields for AI reasoning.
    This is the primary interface between Dynatrace observability data
    and the Gemini AI decision engine.
    """

    def __init__(self, metrics: dict, host_info: dict, problems: list):
        self.metrics = metrics
        self.host_info = host_info
        self.problems = problems
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_context_string(self) -> str:
        """Convert metrics to MCP-formatted context string for AI agent."""
        lines = [
            f"[DYNATRACE_MCP_CONTEXT] timestamp={self.timestamp}",
            f"[HOST] id={self.host_info.get('entityId', 'LOCAL')} "
            f"name={self.host_info.get('displayName', 'localhost')}",
            "",
            "## SYSTEM METRICS",
            f"  cpu_usage_percent      : {self.metrics['cpu']:.2f}%",
            f"  memory_usage_percent   : {self.metrics['memory']:.2f}%",
            f"  disk_io_read_mbps      : {self.metrics['disk_io_read']:.2f} MB/s",
            f"  disk_io_write_mbps     : {self.metrics['disk_io_write']:.2f} MB/s",
            f"  network_in_mbps        : {self.metrics['network_in']:.2f} MB/s",
            f"  network_out_mbps       : {self.metrics['network_out']:.2f} MB/s",
            f"  system_status          : {self.metrics['status']}",
            "",
            "## ACTIVE PROBLEMS",
        ]
        if self.problems:
            for p in self.problems:
                lines.append(f"  - [{p['severity']}] {p['title']}")
        else:
            lines.append("  No active problems detected.")

        lines += [
            "",
            "## RUNNING SERVICES (Non-Critical)",
        ]
        for svc in self.metrics.get("services", []):
            lines.append(
                f"  - {svc['name']:30s} cpu={svc['cpu']:.1f}%  "
                f"mem={svc['memory_mb']:.0f}MB  status={svc['status']}"
            )

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "mcp_type": "dynatrace_metrics",
            "timestamp": self.timestamp,
            "host": self.host_info,
            "metrics": self.metrics,
            "problems": self.problems,
            "context_string": self.to_context_string(),
        }


# ─────────────────────────────────────────────
#  Live Dynatrace API Collector
# ─────────────────────────────────────────────
class DynatraceCollector:
    """
    Collects real metrics from Dynatrace Environment API v2.

    Uses API Token authentication with required scopes:
      - metrics.read
      - entities.read
      - problems.read

    Set environment variables:
      DYNATRACE_ENV_URL  = https://your-env.live.dynatrace.com
      DYNATRACE_API_TOKEN = dt0c01.XXXX...
    """

    def __init__(self, env_url: str = None, api_token: str = None):
        self.env_url = env_url or os.getenv("DYNATRACE_ENV_URL", "")
        self.api_token = api_token or os.getenv("DYNATRACE_API_TOKEN", "")
        self.headers = {
            "Authorization": f"Api-Token {self.api_token}",
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make authenticated GET request to Dynatrace API."""
        url = f"{self.env_url}{endpoint}"
        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Dynatrace API error [{endpoint}]: {e}")
            raise

    def get_host_metrics(self, host_entity_id: str = None) -> dict:
        """
        Fetch CPU, Memory, Disk I/O from Dynatrace Metrics API v2.
        Uses metric selectors for precise queries.
        """
        metrics_to_fetch = {
            "cpu": "builtin:host.cpu.usage:splitBy():avg:last",
            "memory": "builtin:host.mem.usage:splitBy():avg:last",
            "disk_io_read": "builtin:host.disk.readThroughput:splitBy():avg:last",
            "disk_io_write": "builtin:host.disk.writeThroughput:splitBy():avg:last",
            "network_in": "builtin:host.net.nic.trafficIn:splitBy():avg:last",
            "network_out": "builtin:host.net.nic.trafficOut:splitBy():avg:last",
        }

        result = {}
        for metric_key, selector in metrics_to_fetch.items():
            try:
                data = self._get(
                    "/api/v2/metrics/query",
                    params={
                        "metricSelector": selector,
                        "from": "now-5m",
                        "resolution": "1m",
                    },
                )
                if data.get("result") and data["result"][0].get("data"):
                    values = data["result"][0]["data"][0].get("values", [None])
                    result[metric_key] = values[-1] if values else 0.0
                else:
                    result[metric_key] = 0.0
            except Exception:
                result[metric_key] = 0.0

        return result

    def get_problems(self) -> list:
        """Fetch active problems from Dynatrace Problems API."""
        try:
            data = self._get(
                "/api/v2/problems",
                params={"status": "OPEN", "pageSize": 10},
            )
            problems = []
            for p in data.get("problems", []):
                problems.append(
                    {
                        "id": p.get("problemId"),
                        "title": p.get("title", "Unknown Problem"),
                        "severity": p.get("severityLevel", "INFO"),
                        "status": p.get("status"),
                    }
                )
            return problems
        except Exception:
            return []

    def get_host_info(self) -> dict:
        """Fetch host entity information."""
        try:
            data = self._get(
                "/api/v2/entities",
                params={"entitySelector": "type(HOST)", "pageSize": 1},
            )
            entities = data.get("entities", [])
            if entities:
                return {
                    "entityId": entities[0].get("entityId"),
                    "displayName": entities[0].get("displayName", "Unknown Host"),
                }
        except Exception:
            pass
        return {"entityId": "UNKNOWN", "displayName": "localhost"}

    def collect(self) -> DynatraceMCPContext:
        """Collect all metrics and return as MCP context."""
        logger.info("Collecting metrics from Dynatrace API...")
        host_info = self.get_host_info()
        metrics = self.get_host_metrics(host_info.get("entityId"))
        problems = self.get_problems()

        cpu = metrics.get("cpu", 0)
        if cpu < 10:
            status = "idle"
        elif cpu < 60:
            status = "normal"
        elif cpu < 85:
            status = "busy"
        else:
            status = "critical"

        metrics["status"] = status
        metrics["services"] = []

        # Convert bytes to MB/s where needed
        for key in ["disk_io_read", "disk_io_write", "network_in", "network_out"]:
            if metrics.get(key, 0) > 1000:
                metrics[key] = metrics[key] / (1024 * 1024)

        return DynatraceMCPContext(metrics, host_info, problems)


# ─────────────────────────────────────────────
#  Demo / Mock Collector (uses real psutil data)
# ─────────────────────────────────────────────
class DemoCollector:
    """
    Demo mode collector using real local system metrics via psutil
    AND simulating Dynatrace-style service monitoring.

    Produces realistic data for demonstration purposes without
    requiring a live Dynatrace environment.
    """

    def __init__(self):
        self._tick = 0
        self._simulated_services = [
            {
                "name": "baloo_file_indexer",
                "display": "Baloo File Indexer",
                "base_cpu": 4.2,
                "base_mem": 85,
                "criticality": "low",
            },
            {
                "name": "tracker-miner-fs",
                "display": "GNOME Tracker Miner",
                "base_cpu": 3.1,
                "base_mem": 62,
                "criticality": "low",
            },
            {
                "name": "packagekitd",
                "display": "PackageKit Daemon",
                "base_cpu": 1.8,
                "base_mem": 45,
                "criticality": "low",
            },
            {
                "name": "evolution-addressbook",
                "display": "GNOME Address Book",
                "base_cpu": 0.9,
                "base_mem": 38,
                "criticality": "low",
            },
        ]
        self._stopped_services = set()

    def stop_service(self, service_name: str):
        """Mark a service as stopped in the simulation."""
        self._stopped_services.add(service_name)
        logger.info(f"[Demo] Service marked as stopped: {service_name}")

    def collect(self) -> DynatraceMCPContext:
        """Collect real system metrics + simulated service data."""
        self._tick += 1

        # Real CPU/Memory from psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        # Add sinusoidal variation for realistic oscillation
        variation = math.sin(self._tick * 0.3) * 2.0

        metrics = {
            "cpu": max(0, cpu_percent + variation),
            "memory": mem.percent,
            "disk_io_read": (disk_io.read_bytes / (1024 * 1024)) if disk_io else 0.0,
            "disk_io_write": (disk_io.write_bytes / (1024 * 1024)) if disk_io else 0.0,
            "network_in": (net_io.bytes_recv / (1024 * 1024)) if net_io else 0.0,
            "network_out": (net_io.bytes_sent / (1024 * 1024)) if net_io else 0.0,
        }

        # Classify system status
        cpu = metrics["cpu"]
        if cpu < 10:
            status = "idle"
        elif cpu < 60:
            status = "normal"
        elif cpu < 85:
            status = "busy"
        else:
            status = "critical"

        metrics["status"] = status

        # Build simulated service list (excluding stopped ones)
        services = []
        for svc in self._simulated_services:
            if svc["name"] in self._stopped_services:
                continue
            svc_variation = random.uniform(-0.5, 0.5)
            services.append(
                {
                    "name": svc["name"],
                    "display": svc["display"],
                    "cpu": max(0, svc["base_cpu"] + svc_variation),
                    "memory_mb": svc["base_mem"] + random.uniform(-3, 3),
                    "status": "running",
                    "criticality": svc["criticality"],
                }
            )

        metrics["services"] = services

        # Simulate Dynatrace problems when system is idle but services are consuming
        problems = []
        if cpu < 10 and services:
            problems.append(
                {
                    "id": f"PROB_{self._tick:04d}",
                    "title": "High idle resource consumption detected on localhost",
                    "severity": "PERFORMANCE",
                    "status": "OPEN",
                }
            )

        host_info = {
            "entityId": "HOST-DEMO-001",
            "displayName": "localhost (demo)",
            "os": "Linux",
            "cpu_cores": psutil.cpu_count(),
            "total_memory_gb": round(mem.total / (1024 ** 3), 1),
        }

        return DynatraceMCPContext(metrics, host_info, problems)


# ─────────────────────────────────────────────
#  Factory function
# ─────────────────────────────────────────────
def get_collector(mode: str = None):
    """
    Factory: returns appropriate collector based on AGENT_MODE env var.

    Modes:
      'demo' → DemoCollector (uses real psutil + simulated services)
      'live' → DynatraceCollector (requires Dynatrace API credentials)
    """
    mode = mode or os.getenv("AGENT_MODE", "demo")
    if mode == "live":
        logger.info("Using LIVE Dynatrace API collector")
        return DynatraceCollector()
    else:
        logger.info("Using DEMO collector (psutil + simulated services)")
        return DemoCollector()


# ─────────────────────────────────────────────
#  CLI test entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import colorlog

    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    collector = get_collector("demo")

    print("\n" + "=" * 65)
    print("  Smart-Grid Agent — Day 1: Dynatrace Metrics Collector")
    print("=" * 65)

    for i in range(3):
        ctx = collector.collect()
        m = ctx.metrics
        output = {
            "cpu": round(m["cpu"], 2),
            "memory": round(m["memory"], 2),
            "disk_io_read_mbps": round(m["disk_io_read"], 3),
            "disk_io_write_mbps": round(m["disk_io_write"], 3),
            "status": m["status"],
            "services_monitored": len(m.get("services", [])),
        }
        print(f"\n[Tick {i+1}] JSON Output:")
        print(json.dumps(output, indent=2))
        print("\n[MCP Context Preview]:")
        print(ctx.to_context_string())
        print("-" * 65)
        if i < 2:
            time.sleep(2)

    print("\n✅ Day 1 Complete: Dynatrace collector operational")
