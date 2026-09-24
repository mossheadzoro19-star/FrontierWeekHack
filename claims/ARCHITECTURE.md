# ClaimSight — Architecture & Engineering Notes

## Purpose
ClaimSight is a Microsoft Foundry multi-agent **decision-support** system for insurance claim triage. It is intentionally not an autonomous claim approval/denial system. The final decision remains with an authorized human adjuster.

## End-to-end architecture
```text
Incoming claim batch
        |
        v
+---------------------+
| Claims Triage Agent |
| - assess_claim tool |
| - threshold checks  |
| - evidence summary  |
| - risk + confidence |
+----------+----------+
           |
           v
+---------------------------+
| Risk / Human Review Gate  |
| Route WARNING/CRITICAL    |
| or insufficient evidence  |
+-------------+-------------+
              |
              v
+---------------------------+
| Claims Decision Agent     |
| - consumes triage JSON    |
| - recommends an action    |
| - preserves escalation   |
+-------------+-------------+
              |
              v
   Human claims adjuster
```

## Why two agents?
The agents have separate responsibilities:
- **Triage** gathers evidence and classifies risk.
- **Decision** converts the structured triage evidence into an operational recommendation.
This separation makes prompts, traces, evaluation results, and failure analysis easier to reason about than a single monolithic agent.

## Grounding and evidence
The Triage Agent must call `assess_claim` for requested claim IDs. The tool calculates threshold compliance from the claim record instead of allowing the model to invent or reinterpret raw values.
The agent must not use the source `status` field as ground truth. Risk is derived from evidence rather than simply echoing an existing label.

## Structured handoff
Triage returns exactly one JSON array containing one record per claim:
- `claim_id`
- `risk_level`
- `confidence`
- `flagged_metrics`
- `missing_documents`
- `evidence_summary`
- `human_review_required`
The workflow validates this contract before routing claims to the Decision Agent.
The Decision Agent receives the actual Triage Agent result. The production workflow therefore does not recompute flags independently after triage.

## Safety and governance controls
- Decision support rather than autonomous final adjudication.
- Human review is preserved when evidence is insufficient or risk indicators are material.
- No invented policy terms or claim facts.
- Recommendations must be evidence-based.
- Confidence does not override a required human review.
- Tool-derived metric values are preserved.
- The workflow separates evidence collection from recommendation generation.

## Observability
Challenge 2 instruments the real Triage -> Decision execution path with GenAI tracing and Azure Monitor/Application Insights.
This allows investigation of agent inputs/outputs, tool calls, latency, failures, and behavior across workflow stages.

## Evaluation
Challenge 3 uses the Microsoft-provided evaluation dataset and Foundry evaluators for systematic quality measurement. Evaluation is treated as a release-quality signal rather than a one-time demo step.

## Orchestration
Challenge 4 provides two implementations:
1. Python SDK orchestration for explicit control and testability.
2. A Foundry Workflow Agent for portal-visible multi-agent orchestration.
The intended workflow is: `Triage -> route based on structured risk -> Decision -> consolidated report`.

## Production evolution
The local `assess_claim` function is a lab tool boundary. A production implementation can replace it with authenticated tools such as policy lookup, fraud intelligence lookup, document retrieval/request, claim history, and payment/coverage verification.
The same structured contracts and human-review gate can remain in place while the underlying systems change.

## Interview-ready engineering story
The important engineering decisions are not the UI. They are:
1. Tool-grounded evidence instead of free-form model judgment.
2. Specialized agents instead of one oversized prompt.
3. Explicit structured contracts between agents.
4. Human-in-the-loop escalation.
5. OpenTelemetry/Foundry tracing.
6. Dataset-based evaluation.
7. Workflow orchestration.
8. A clear boundary between recommendation and final business authority.

This maps directly to the Level 3 Architect lifecycle: **Build -> Monitor -> Evaluate -> Orchestrate/Deploy**.