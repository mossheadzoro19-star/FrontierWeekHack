# ClaimSight Production Evaluation Plan

## Goal
Evaluate whether the multi-agent system produces useful, grounded, safe, and contract-compliant decision support before a version is promoted.

## Evaluation layers

### 1. Triage contract tests
For every test claim:
- exactly one JSON record is returned;
- every requested claim appears exactly once;
- required fields are present;
- risk is supported by flagged metrics or missing evidence;
- source status is not treated as ground truth;
- human-review requirements are preserved.

### 2. Agent quality evaluation
Use the Microsoft Foundry evaluation flow from Challenge 3 with the provided dataset. The current lab submission uses Coherence and Fluency because the portal dataset evaluation cannot execute the local assess_claim function.

For a production evaluation suite, add:
- **Groundedness** — recommendation is supported by supplied evidence/approved knowledge;
- **Task adherence** — follows the triage/decision contract;
- **Relevance** — response addresses the claim and requested task;
- **Safety / governance** — does not turn decision support into an autonomous final determination;
- **Tool-call correctness** — calls the right tool with the right claim identifier when tools are enabled.

### 3. Workflow tests
Test the complete path:
claim input -> triage -> validation -> routing -> decision -> human-review flag -> report

Include normal, warning, critical, missing-document, conflicting-evidence, malformed-output, and tool-error cases.

## Release gates
A candidate version should be promoted only when:
- structured-output validation passes;
- no critical safety/governance regression is detected;
- evaluation results meet the team's agreed thresholds;
- important failure cases have an owner and remediation;
- traces show expected tool usage and workflow routing.

## Observability feedback loop
Use Foundry/OpenTelemetry traces and Application Insights to inspect latency, failures, tool calls, inputs/outputs, and workflow stages. Sample failed or low-quality traces into the regression dataset so evaluation improves with real failure modes.

## Human review
Evaluation must not optimize only for automated scores. Human adjuster review remains the authority for consequential recommendations, especially high-risk or ambiguous claims.
