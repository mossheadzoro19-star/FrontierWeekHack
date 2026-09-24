# ClaimSight Demo Knowledge Base

This document is a **demo grounding source**, not a real insurance policy or legal/regulatory document.
It defines the decision-support rules used in the prototype and the boundaries a production implementation should preserve.

## Evidence hierarchy
1. Tool-returned claim metrics and thresholds are the primary evidence for risk classification.
2. Structured Triage Agent output is the only claim evidence passed to the Decision Agent in the Python workflow.
3. This guidance explains how to interpret evidence; it does not replace policy documents, contracts, regulatory requirements, or an authorized adjuster's judgment.
4. Missing or conflicting evidence must be surfaced rather than invented.

## Prototype decision guidance
- **REQUEST DOCUMENTS** when required evidence is missing or incomplete and a reliable recommendation cannot yet be made.
- **INVESTIGATE** when fraud risk is materially above its configured threshold, or when multiple significant risk indicators require investigation.
- **APPROVE** is a recommendation only when supplied evidence indicates metrics are within configured thresholds and required documentation is complete.
- **DENY** should not be inferred solely from a risk label. It requires explicit supporting evidence and human review under the prototype governance model.
- human_review_required=true always remains true regardless of the recommended action.

## Escalation guidance
Escalate to a human adjuster when:
- fraud risk exceeds the configured threshold;
- multiple significant metrics are out of range;
- evidence is incomplete or conflicting;
- the recommendation would have material financial or coverage consequences;
- the model cannot support its recommendation with the supplied evidence.

## Production grounding target
In a production ClaimSight deployment, this demo document should be replaced or supplemented by governed, versioned sources such as:
- the customer's applicable policy and endorsements;
- approved claims-handling procedures;
- authorized regulatory/compliance guidance;
- approved fraud-intelligence sources;
- document and claim-history systems.

Every source should have an owner, version/effective date, access control, and an audit trail.
