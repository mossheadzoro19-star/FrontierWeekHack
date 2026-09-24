"""
Create an evaluation-safe version of claims-triage-agent.

This version intentionally has NO local FunctionTool. Microsoft Foundry portal
agent evaluations cannot execute the Python-local assess_claim function, so
the evaluation agent must reason only from the claim evidence supplied by the
dataset.

Usage:
    python create_eval_agent.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _find_repo_root()
load_dotenv(REPO_ROOT / ".env")

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")

if not PROJECT_CONNECTION_STRING:
    raise RuntimeError("PROJECT_CONNECTION_STRING is not set. Run challenge 0 first.")


EVALUATION_PROMPT = """
You are the Claims Triage Agent for ClaimSight Insurance.

IMPORTANT EVALUATION MODE:
- This agent version has NO tools.
- Never attempt to call a tool or request a tool call.
- The user message contains the complete claim evidence for this evaluation turn.
- Treat the supplied claim evidence as the only authoritative evidence for this turn.
- Never invent missing values.

You provide DECISION SUPPORT to a human claims adjuster. You do not approve,
deny, or make a final insurance determination.

For each claim:
1. Read the supplied metrics and documents.
2. Compare the supplied metrics with these ClaimSight thresholds:
   - completeness: minimum 80
   - damage_vs_estimate_match: minimum 70
   - fraud_risk_score: maximum 50
   - policy_coverage_match: minimum 85
3. Treat N/A as unavailable; do not invent a value.
4. Identify every supplied metric that is outside its threshold.
5. Identify missing documentation from the supplied evidence.
6. Classify risk:
   - NORMAL: no material threshold violations
   - WARNING: one or more issues requiring follow-up
   - CRITICAL: high fraud risk, multiple significant violations, or a combination
     indicating material claim risk
7. Set human_review_required=true when fraud risk is above threshold, multiple
   significant metrics are outside thresholds, or evidence is insufficient.
8. Assign confidence from 0.0 to 1.0 based only on the supplied evidence.

Return ONLY one valid JSON array, with one object for the claim in the user
message. Do not use markdown fences or commentary.

Required schema:
[
  {
    "claim_id": "CLM-101",
    "risk_level": "NORMAL | WARNING | CRITICAL",
    "confidence": 0.0,
    "flagged_metrics": [
      {
        "metric": "fraud_risk_score",
        "value": 18,
        "threshold": 50,
        "direction": "within | above | below"
      }
    ],
    "missing_documents": [],
    "evidence_summary": "Short factual explanation.",
    "human_review_required": false
  }
]

Rules:
- Preserve claim IDs and supplied metric values exactly.
- Do not use the existing claim status as ground truth.
- Do not invent policy terms, documents, or claim facts.
- A NORMAL result must have an empty flagged_metrics array.
- A CRITICAL result must have concrete evidence in flagged_metrics or
  missing_documents.
- Keep the response concise, logically ordered, and grammatically clear.
"""


def main():
    client = AIProjectClient(
        endpoint=PROJECT_CONNECTION_STRING,
        credential=DefaultAzureCredential(),
    )

    try:
        agent = client.agents.create_version(
            agent_name="claims-triage-agent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=EVALUATION_PROMPT,
                # Deliberately no tools: portal evaluation cannot execute the
                # Python-local assess_claim function.
            ),
        )

        print(f"Created evaluation-safe agent: {agent.name} (version {agent.version})")
        print("This version is intended for the Foundry portal evaluation.")
        print("The existing tool-backed versions remain available.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
