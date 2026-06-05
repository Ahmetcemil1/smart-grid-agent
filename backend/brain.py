"""
╔══════════════════════════════════════════════════════════════╗
║  Smart-Grid Agent - Gemini AI Brain (Decision Engine)        ║
║  Day 2: FinOps Decision Making via Google Gemini Pro         ║
║  Pipeline: Dynatrace MCP context → AI reasoning → Actions   ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import logging
import re
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("SmartGrid.Brain")

# ─────────────────────────────────────────────
#  FinOps System Prompt (English)
# ─────────────────────────────────────────────
FINOPS_SYSTEM_PROMPT = """
You are a FinOps (Financial Operations) and Site Reliability Engineering expert.
Your mission: analyze Dynatrace metric data and produce cost optimization decisions.

DECISION RULES:
1. If CPU usage is below 10% AND non-critical services are running → recommend stopping them
2. If Memory usage is below 15% → recommend stopping memory-intensive background processes
3. If Disk I/O < 5 MB/s → recommend deferring index/scan services
4. NEVER touch critical services (NetworkManager, sshd, dbus, firewalld, systemd-logind)
5. Explain every action with a clear reason and quantified savings estimate

MANDATORY OUTPUT FORMAT (strict JSON, no markdown):
{
  "analysis": "Brief summary of the current system state",
  "risk_level": "low|medium|high",
  "actions": [
    {
      "service": "service_name",
      "action": "stop|restart|throttle|monitor",
      "reason": "Why this action is recommended",
      "estimated_cpu_save": 4.2,
      "estimated_memory_save_mb": 85,
      "priority": "high|medium|low"
    }
  ],
  "estimated_total_savings": {
    "cpu_percent": 9.2,
    "memory_mb": 230,
    "cost_per_hour_usd": 0.0085
  },
  "recommendation": "Overall optimization strategy",
  "confidence": 0.92
}

IMPORTANT: Return only valid JSON. Do NOT use markdown code blocks.
"""


# ─────────────────────────────────────────────
#  Gemini Brain
# ─────────────────────────────────────────────
class GeminiBrain:
    """
    Google Gemini Pro based FinOps decision engine.

    Receives Dynatrace MCP context and returns structured action plans.
    Falls back to a local rule-based engine if Gemini API is unavailable.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = "gemini-1.5-pro"
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        """Initialize Gemini client with error handling."""
        if not self.api_key or self.api_key in ("your_gemini_api_key_here", "placeholder-no-real-key", "test-key-placeholder"):
            logger.warning(
                "GEMINI_API_KEY not set — using local rule-based fallback engine"
            )
            self._available = False
            return

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=FINOPS_SYSTEM_PROMPT,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                ),
            )
            self._available = True
            logger.info(f"Gemini Brain initialized ({self.model_name})")
        except ImportError:
            logger.error("google-generativeai package not installed. Run: pip install google-generativeai")
            self._available = False
        except Exception as e:
            logger.error(f"Gemini initialization failed: {e}")
            self._available = False

    def analyze(self, mcp_context) -> dict:
        """
        Send MCP context to Gemini and receive action recommendations.
        Falls back to local rule-based engine if Gemini is unavailable.

        Args:
            mcp_context: DynatraceMCPContext object from collector

        Returns:
            dict with analysis, risk_level, actions, savings estimates
        """
        context_str = mcp_context.to_context_string()
        metrics = mcp_context.metrics
        services = metrics.get("services", [])

        logger.info(f"Brain analyzing system state: {metrics.get('status', '?')} "
                    f"(CPU: {metrics.get('cpu', 0):.1f}%)")

        if self._available:
            return self._gemini_analyze(context_str, metrics)
        else:
            return self._local_rule_engine(metrics, services)

    def _gemini_analyze(self, context_str: str, metrics: dict) -> dict:
        """Send context to Gemini Pro API and parse the JSON response."""
        prompt = f"""
Analyze the following Dynatrace system metric data and provide FinOps optimization decisions:

{context_str}

Current CPU Usage: {metrics.get('cpu', 0):.2f}%
System Status: {metrics.get('status', 'unknown')}

Respond with your decisions in JSON format:
"""
        try:
            response = self._client.generate_content(prompt)
            text = response.text.strip()

            # Strip markdown code blocks if present
            if text.startswith("```"):
                text = re.sub(r"^```json?\n?", "", text)
                text = re.sub(r"\n?```$", "", text)

            result = json.loads(text)
            result["brain"] = "gemini-pro"
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            logger.info(
                f"Gemini decision: {len(result.get('actions', []))} actions "
                f"(confidence: {result.get('confidence', '?')})"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Gemini returned invalid JSON: {e}")
            return self._local_rule_engine(metrics, metrics.get("services", []))
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._local_rule_engine(metrics, metrics.get("services", []))

    def _local_rule_engine(self, metrics: dict, services: list) -> dict:
        """
        Local rule-based fallback engine.

        Implements FinOps decision rules without requiring Gemini API.
        Produces identical output format to the Gemini response.

        Rules:
          - CPU < 10%: Stop idle non-critical services
          - Memory < 15% + CPU > 10%: Throttle background processes
          - System busy: Monitor only, no intervention
        """
        cpu = metrics.get("cpu", 0)
        memory = metrics.get("memory", 0)
        status = metrics.get("status", "unknown")

        actions = []
        total_cpu_save = 0.0
        total_mem_save = 0.0

        # Rule 1: System idle + non-critical services running
        if cpu < 10 and services:
            for svc in services:
                if svc.get("criticality") == "low" and svc.get("cpu", 0) > 0.5:
                    action = {
                        "service": svc["name"],
                        "action": "stop",
                        "reason": (
                            f"System CPU at {cpu:.1f}% (below 10% idle threshold). "
                            f"Service '{svc['name']}' is consuming {svc['cpu']:.1f}% CPU "
                            f"and {svc.get('memory_mb', 0):.0f}MB RAM unnecessarily. "
                            f"Stopping will immediately free these resources."
                        ),
                        "estimated_cpu_save": round(svc["cpu"], 2),
                        "estimated_memory_save_mb": round(svc.get("memory_mb", 40), 0),
                        "priority": "high" if svc["cpu"] > 3 else "medium",
                    }
                    actions.append(action)
                    total_cpu_save += svc["cpu"]
                    total_mem_save += svc.get("memory_mb", 40)

        # Rule 2: Low memory + moderate CPU → throttle background services
        elif memory < 15 and cpu > 10:
            for svc in services[:2]:
                if svc.get("criticality") == "low":
                    action = {
                        "service": svc["name"],
                        "action": "throttle",
                        "reason": (
                            f"Memory usage is low ({memory:.1f}%). "
                            f"Service '{svc['name']}' can be CPU-throttled to 5% quota."
                        ),
                        "estimated_cpu_save": round(svc["cpu"] * 0.5, 2),
                        "estimated_memory_save_mb": round(svc.get("memory_mb", 40) * 0.3, 0),
                        "priority": "low",
                    }
                    actions.append(action)
                    total_cpu_save += svc["cpu"] * 0.5
                    total_mem_save += svc.get("memory_mb", 40) * 0.3

        # Classify risk
        if cpu > 80 or memory > 90:
            risk_level = "high"
            analysis = (
                f"System under high resource pressure. "
                f"CPU: {cpu:.1f}%, Memory: {memory:.1f}%. "
                f"Emergency intervention may be required."
            )
        elif cpu < 10 and actions:
            risk_level = "low"
            analysis = (
                f"System is idle (CPU: {cpu:.1f}%). "
                f"{len(actions)} unnecessary services detected consuming "
                f"{total_cpu_save:.1f}% CPU and {total_mem_save:.0f}MB RAM. "
                f"Stopping them will immediately reduce resource waste."
            )
        else:
            risk_level = "medium"
            analysis = (
                f"System operating within normal range. "
                f"CPU: {cpu:.1f}%, Memory: {memory:.1f}%. "
                f"{len(actions)} optimization opportunities identified."
            )

        # Calculate cost savings
        cost_per_cpu_per_hour = 0.0018  # USD per CPU% per hour
        cost_per_mb_per_hour = 0.000025  # USD per MB per hour
        cost_save = (
            total_cpu_save * cost_per_cpu_per_hour
            + total_mem_save * cost_per_mb_per_hour
        )

        return {
            "brain": "local-rule-engine",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis,
            "risk_level": risk_level,
            "actions": actions,
            "estimated_total_savings": {
                "cpu_percent": round(total_cpu_save, 2),
                "memory_mb": round(total_mem_save, 0),
                "cost_per_hour_usd": round(cost_save, 6),
            },
            "recommendation": (
                "Stop idle background services to immediately free CPU and memory resources. "
                "All actions require human approval before execution."
                if actions
                else "System is operating optimally. Continue periodic monitoring."
            ),
            "confidence": 0.88 if actions else 0.95,
        }


# ─────────────────────────────────────────────
#  CLI test entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import colorlog
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from collector import get_collector

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
    print("  Smart-Grid Agent — Day 2: Gemini FinOps Brain")
    print("=" * 65)

    collector = get_collector("demo")
    brain = GeminiBrain()

    ctx = collector.collect()
    decision = brain.analyze(ctx)

    print(f"\n[Brain Mode]  : {decision.get('brain', 'unknown')}")
    print(f"[Analysis]    : {decision.get('analysis', '')}")
    print(f"[Risk Level]  : {decision.get('risk_level', '?')}")
    print(f"[Confidence]  : {decision.get('confidence', 0) * 100:.0f}%")
    print(f"\n[Recommended Actions ({len(decision.get('actions', []))})]:")
    for a in decision.get("actions", []):
        print(f"  ⚡ {a['action'].upper():10s} {a['service']}")
        print(f"     Reason: {a['reason'][:80]}...")
        print(
            f"     Savings: {a['estimated_cpu_save']:.1f}% CPU, "
            f"{a['estimated_memory_save_mb']:.0f}MB RAM"
        )

    savings = decision.get("estimated_total_savings", {})
    print(f"\n[Total Estimated Savings]:")
    print(f"  CPU Freed  : {savings.get('cpu_percent', 0):.2f}%")
    print(f"  RAM Freed  : {savings.get('memory_mb', 0):.0f} MB")
    print(f"  Cost/Hour  : ${savings.get('cost_per_hour_usd', 0):.6f}")
    print(f"\n✅ Day 2 Complete: Gemini Brain operational")
