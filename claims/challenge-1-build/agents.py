"""
Challenge 1: Build Agents — Insurance Claims Processing
Claims Triage Agent and Claims Decision Agent for ClaimSight Insurance.

Usage:
    python agents.py

Builds both agents with system prompts, tools, and conversation handling.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from openai.types.responses.response_input_param import FunctionCallOutput


# Resolve repo root by finding .env in parent directories.
def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            return parent
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _find_repo_root()

# Load environment
env_path = REPO_ROOT / ".env"
load_dotenv(env_path)

PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.4")
CLAIMS_DATA_PATH = Path(__file__).resolve().parent / "claims_data.json"


def _load_claim_batch() -> list[dict]:
    """Load claim records to send as a batch payload in demo requests."""
    with open(CLAIMS_DATA_PATH, "r") as f:
        data = json.load(f)
    return data.get("claims", [])


# =============================================================================
# Tool Function: assess_claim
# This is already implemented — agents can call this to get claim risk analysis
# =============================================================================

def assess_claim(claim_id: str) -> str:
    """
    Reads claims_data.json and checks if a claim's metrics are within acceptable thresholds.
    Returns a JSON string with the analysis.
    """
    with open(CLAIMS_DATA_PATH, "r") as f:
        data = json.load(f)

    claim = None
    for c in data["claims"]:
        if c["claim_id"] == claim_id:
            claim = c
            break

    if not claim:
        return json.dumps({"error": f"Claim '{claim_id}' not found"})

    results = {
        "claim_id": claim["claim_id"],
        "type": claim["type"],
        "claimant": claim["claimant"],
        "date_filed": claim["date_filed"],
        "status": claim["status"],
        "documents_submitted": claim["documents_submitted"],
        "flags": [],
        "all_metrics": {},
    }

    for metric, reading in claim["metrics"].items():
        value = reading["value"]
        threshold = claim["thresholds"][metric]
        in_spec = threshold["min"] <= value <= threshold["max"]

        results["all_metrics"][metric] = {
            "value": value,
            "unit": reading["unit"],
            "min": threshold["min"],
            "max": threshold["max"],
            "in_spec": in_spec,
        }

        if not in_spec:
            deviation = ""
            if value > threshold["max"]:
                pct = ((value - threshold["max"]) / threshold["max"]) * 100
                deviation = f"{pct:.1f}% above max"
            elif value < threshold["min"]:
                pct = ((threshold["min"] - value) / threshold["min"]) * 100
                deviation = f"{pct:.1f}% below min"

            results["flags"].append({
                "metric": metric,
                "value": value,
                "unit": reading["unit"],
                "threshold_min": threshold["min"],
                "threshold_max": threshold["max"],
                "deviation": deviation,
            })

    return json.dumps(results, indent=2)


# Tool definition for the agent (Foundry FunctionTool format)
ASSESS_CLAIM_TOOL = FunctionTool(
    name="assess_claim",
    description="Assess an insurance claim's metrics against acceptable thresholds. Returns flags if any metrics are outside acceptable ranges (completeness too low, fraud risk too high, etc.).",
    parameters={
        "type": "object",
        "properties": {
            "claim_id": {
                "type": "string",
                "description": "The claim ID (e.g., 'CLM-001') to assess",
            }
        },
        "required": ["claim_id"],
        "additionalProperties": False,
    },
    strict=False,
)


# =============================================================================
# Claims Triage Agent
# =============================================================================

class ClaimsTriageAgent:
    def __init__(self):
        self.agent = None
        self.client = None
        self.openai = None

    def create(self):
        """Create the claims triage agent in Foundry."""
        self.client = AIProjectClient(
            endpoint=PROJECT_CONNECTION_STRING,
            credential=DefaultAzureCredential(),
        )
        self.openai = self.client.get_openai_client()

        system_prompt = """
        You are the Claims Triage Agent for ClaimSight Insurance.

        Your role is DECISION SUPPORT. You do not approve, deny, or make a final insurance determination.

        For every claim:
        1. Call assess_claim using the claim_id.
        2. Examine every returned metric against its threshold.
        3. Identify all out-of-range metrics.
        4. Classify risk:
           - NORMAL: no material threshold violations
           - WARNING: one or more issues requiring follow-up
           - CRITICAL: high fraud risk, multiple significant violations, or a combination indicating material claim risk
        5. Identify missing or potentially missing documentation.
        6. Explain the evidence supporting the risk classification.
        7. Assign a confidence value from 0.0 to 1.0 based only on available claim evidence.
        8. Decide whether human review is required.

        Human review is REQUIRED when:
        - fraud_risk_score is above its maximum threshold, OR
        - multiple significant metrics are outside thresholds, OR
        - available evidence is insufficient for a reliable recommendation.

        IMPORTANT:
        - Never invent claim facts.
        - Never change metric values returned by the tool.
        - Never treat the existing claim status as ground truth.
        - Base classification on actual metrics and thresholds returned by assess_claim.
        - Do not make a final approval or denial decision.

        Return ONLY one valid JSON array containing one object for EVERY claim assessed:
        [
          {
            "claim_id": "CLM-001",
            "risk_level": "NORMAL | WARNING | CRITICAL",
            "confidence": 0.0,
            "flagged_metrics": [
              {
                "metric": "fraud_risk_score",
                "value": 82,
                "threshold": 50,
                "direction": "above"
              }
            ],
            "missing_documents": [],
            "evidence_summary": "Short factual explanation.",
            "human_review_required": true
          }
        ]

        Output contract:
        - Exactly one JSON array; no markdown fences and no commentary.
        - Include every requested claim exactly once.
        - Preserve the metric names and values returned by the tool.
        - Confidence must reflect evidence completeness; do not use confidence to override a required human review.
        - A CRITICAL result must have a concrete evidence trail in flagged_metrics or missing_documents.
        - A NORMAL result must contain an empty flagged_metrics array and human_review_required=false unless evidence is insufficient.

        Be concise and evidence-based.
        """

        self.agent = self.client.agents.create_version(
            agent_name="claims-triage-agent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=system_prompt,
                tools=[ASSESS_CLAIM_TOOL],
            ),
        )

        return self.agent

    def run(self, input_text: str) -> str:
        """Run the claims triage agent with the given input."""
        conversation = self.openai.conversations.create()

        response = self.openai.responses.create(
            input=input_text,
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )

        # Handle function call loops
        while True:
            function_calls = [item for item in response.output if item.type == "function_call"]
            if not function_calls:
                break

            input_list = []
            for item in function_calls:
                if item.name == "assess_claim":
                    args = json.loads(item.arguments)
                    result = assess_claim(args["claim_id"])
                else:
                    result = json.dumps({"error": f"Unknown tool '{item.name}'"})

                input_list.append(
                    FunctionCallOutput(
                        type="function_call_output",
                        call_id=item.call_id,
                        output=result,
                    )
                )

            response = self.openai.responses.create(
                input=input_list,
                conversation=conversation.id,
                extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
            )

        self.openai.conversations.delete(conversation_id=conversation.id)
        return response.output_text

    def cleanup(self):
        """Delete the agent version and close connections."""
        if self.agent:
            self.client.agents.delete_version(
                agent_name=self.agent.name,
                agent_version=self.agent.version,
            )
        if self.client:
            self.client.close()


# =============================================================================
# Claims Decision Agent
# =============================================================================

class ClaimsDecisionAgent:
    def __init__(self):
        self.agent = None
        self.client = None
        self.openai = None

    def create(self):
        """Create the claims decision agent in Foundry."""
        self.client = AIProjectClient(
            endpoint=PROJECT_CONNECTION_STRING,
            credential=DefaultAzureCredential(),
        )
        self.openai = self.client.get_openai_client()

        system_prompt = """
        You are the Claims Decision Agent for ClaimSight Insurance.

        You provide DECISION SUPPORT to a human claims adjuster.
        You must NOT present your recommendation as a final insurance determination.

        You receive structured triage results containing:
        - claim ID
        - risk level
        - confidence
        - flagged metrics
        - missing documents
        - evidence summary
        - human review requirement

        Recommend ONE action:
        - APPROVE
        - REQUEST DOCUMENTS
        - INVESTIGATE
        - DENY

        Decision guidance:
        1. If required documentation is missing: REQUEST DOCUMENTS.
        2. If fraud risk is materially above threshold: INVESTIGATE.
        3. If fraud risk is high and damage-vs-estimate is below threshold: INVESTIGATE.
        4. If policy coverage is below threshold: recommend further coverage review; use DENY only when the supplied evidence supports it, and clearly preserve human review.
        5. If all important metrics are in range and documentation is complete: APPROVE.
        6. If multiple significant indicators are present: INVESTIGATE.
        7. If human_review_required is true: preserve it regardless of recommendation.

        Never invent policy terms, claim facts, or missing evidence.

        Return ONLY valid JSON:
        {
          "claim_id": "CLM-001",
          "recommended_action": "APPROVE | REQUEST DOCUMENTS | INVESTIGATE | DENY",
          "confidence": 0.0,
          "reasoning": "Evidence-based explanation.",
          "next_steps": ["Specific action for the claims adjuster"],
          "urgency": "IMMEDIATE | WITHIN_48H | STANDARD",
          "human_review_required": true
        }

        This is a recommendation for a human claims adjuster, not an autonomous final decision.
        """

        self.agent = self.client.agents.create_version(
            agent_name="claims-decision-agent",
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT_NAME,
                instructions=system_prompt,
            ),
        )

        return self.agent

    def run(self, input_text: str) -> str:
        """Run the claims decision agent with the given input."""
        conversation = self.openai.conversations.create()

        response = self.openai.responses.create(
            input=input_text,
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )

        self.openai.conversations.delete(conversation_id=conversation.id)
        return response.output_text

    def cleanup(self):
        """Delete the agent version and close connections."""
        if self.agent:
            self.client.agents.delete_version(
                agent_name=self.agent.name,
                agent_version=self.agent.version,
            )
        if self.client:
            self.client.close()


# =============================================================================
# Main — Test both agents
# =============================================================================

def main():
    if not PROJECT_CONNECTION_STRING:
        print("❌ PROJECT_CONNECTION_STRING not set. Run challenge 0 first!")
        sys.exit(1)

    print("=== Claims Triage Agent ===")
    print("Creating agent...")

    triage_agent = ClaimsTriageAgent()
    triage_agent.create()
    print(f"✅ Created: {triage_agent.agent.name} (version {triage_agent.agent.version})")

    print("\nAssessing all claims...")
    claim_batch = _load_claim_batch()
    claim_ids = [claim["claim_id"] for claim in claim_batch]
    triage_result = triage_agent.run(
        "You are receiving a batch payload of claims that must be assessed in one run. "
        "Use assess_claim for each claim_id in the payload and summarize all flags.\n\n"
        f"BATCH_CLAIM_IDS: {json.dumps(claim_ids)}\n"
        "BATCH_CLAIM_DATA:\n"
        f"{json.dumps(claim_batch, indent=2)}"
    )
    print(triage_result)

    print("\n=== Claims Decision Agent ===")
    print("Creating agent...")

    decision_agent = ClaimsDecisionAgent()
    decision_agent.create()
    print(f"✅ Created: {decision_agent.agent.name} (version {decision_agent.agent.version})")

    print("\nPassing triage results to Decision Agent...")
    decision_result = decision_agent.run(
        """You are receiving the structured output from the Claims Triage Agent.

Use ONLY the triage results below to provide decision-support recommendations.

Do not independently invent claim facts.
Do not ignore the human-review requirement.

For each claim, provide:
- recommended action
- confidence
- reasoning
- next steps
- urgency
- human review requirement

TRIAGE RESULTS:
"""
        + triage_result
    )
    print(decision_result)

    # Cleanup — comment out to keep agents visible in the Foundry portal
    # print("\nCleaning up agents...")
    # triage_agent.cleanup()
    # decision_agent.cleanup()
    # print("✅ Done!")


if __name__ == "__main__":
    main()
