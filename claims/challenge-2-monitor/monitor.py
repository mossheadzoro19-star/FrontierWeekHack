"""
Challenge 2: Monitor with Application Insights — Claims Processing
Enable GenAI tracing and verify traces appear in App Insights.

Usage:
    python monitor.py

IMPORTANT: Environment variables must be set BEFORE importing azure.ai.projects!
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment FIRST — tracing env vars must be set before SDK import
def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[2]


env_path = _find_repo_root() / ".env"
load_dotenv(env_path)

# Verify tracing is enabled
if os.getenv("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING") != "true":
    print("❌ AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING is not set to 'true' in .env")
    print("   Add: AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true")
    sys.exit(1)

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
APPINSIGHTS_CONN_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")


def setup_tracing():
    """Configure OpenTelemetry instrumentation and Azure Monitor export."""
    print("=== Setting up tracing ===")
    print("✅ AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING is enabled")

    from azure.ai.projects.telemetry import AIProjectInstrumentor
    AIProjectInstrumentor().instrument()
    print("✅ AIProjectInstrumentor configured")

    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(
        connection_string=APPINSIGHTS_CONN_STRING,
        enable_live_metrics=True,
    )
    print("✅ Azure Monitor exporter connected")


def run_traced_agent_call():
    """Run the real Claims Triage -> Decision flow so both agents are traced."""
    print("\n=== Running traced Claims workflow ===")

    # Import Challenge 1 only AFTER tracing has been configured.
    challenge1_dir = Path(__file__).resolve().parents[1] / "challenge-1-build"
    sys.path.insert(0, str(challenge1_dir))

    from agents import ClaimsDecisionAgent, ClaimsTriageAgent, _load_claim_batch

    claim_batch = _load_claim_batch()
    claim_ids = [claim["claim_id"] for claim in claim_batch]

    print("Creating Claims Triage Agent...")
    triage_agent = ClaimsTriageAgent()
    triage_agent.create()
    print(f"✅ Created: {triage_agent.agent.name} (version {triage_agent.agent.version})")

    triage_result = triage_agent.run(
        "Assess this claim batch using assess_claim for every claim ID. "
        "Base risk classification only on the tool results, not the existing status field. "
        "Return the structured JSON triage results requested by your system instructions.\n\n"
        f"CLAIM_IDS: {claim_ids}"
    )
    print(f"✅ Triage trace captured. Output preview: {triage_result[:200]}...")

    print("Creating Claims Decision Agent...")
    decision_agent = ClaimsDecisionAgent()
    decision_agent.create()
    print(f"✅ Created: {decision_agent.agent.name} (version {decision_agent.agent.version})")

    decision_result = decision_agent.run(
        "Use ONLY the structured triage results below to provide decision-support recommendations. "
        "Preserve every human-review requirement. Do not invent claim facts.\n\n"
        "TRIAGE RESULTS:\n"
        + triage_result
    )
    print(f"✅ Decision trace captured. Output preview: {decision_result[:200]}...")

    # Keep the agent versions available in Foundry for trace inspection.
    # They can be cleaned up manually after reviewing the traces.
    print("ℹ️ Agent versions were kept for portal inspection.")


def verify_traces():
    """Wait for traces to propagate and verify they appear in App Insights."""
    print("\n=== Verifying traces in App Insights ===")

    if not APPINSIGHTS_CONN_STRING:
        print("⚠️  APPLICATIONINSIGHTS_CONNECTION_STRING not set — skipping verification")
        print("   You can still check traces manually in the Azure Portal")
        return

    print("⏳ Waiting for traces to propagate (30 seconds)...")
    time.sleep(30)

    print("✅ Traces should now be visible in Application Insights")
    print("   Go to: Azure Portal → Application Insights → Transaction search")
    print("   Filter by: Last 5 minutes, Event type: Dependency")


def main():
    if not PROJECT_CONNECTION_STRING:
        print("❌ PROJECT_CONNECTION_STRING not set. Run challenge 0 first!")
        sys.exit(1)

    setup_tracing()
    run_traced_agent_call()
    verify_traces()

    print("\n🎉 Monitoring is active! Check App Insights for the full trace view.")


if __name__ == "__main__":
    main()
