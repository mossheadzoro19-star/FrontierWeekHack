<div align="center">

<img src="https://img.shields.io/badge/Microsoft-Azure-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white" alt="Microsoft Azure">
<img src="https://img.shields.io/badge/Microsoft-Foundry-5B5FC7?style=for-the-badge&logo=microsoft&logoColor=white" alt="Microsoft Foundry">

# ClaimSight

### Multi-Agent Insurance Claims Decision Support

**Built with Microsoft Azure + Microsoft Foundry**  
*From evidence to decision support, with human oversight*

</div>

---

ClaimSight triages property and auto claims, identifies risk indicators, routes flagged cases, and generates evidence-based recommendations for human claims adjusters.

> **Decision support only:** final claim decisions remain with an authorized human.

## Architecture

<div align="center">
<img src="./claims/images/architecture.png" alt="ClaimSight Architecture" width="100%">
</div>

### Flow

```text
Claim Batch
    ↓
Claims Triage Agent
    ├── assess_claim
    ├── threshold analysis
    └── evidence + risk
    ↓
Structured Triage JSON
    ↓
Claims Decision Agent
    ↓
Recommendation
    ↓
Human Claims Adjuster
```

## Tech Stack

| Layer | Stack |
|---|---|
| AI platform | Microsoft Foundry / Foundry Agent Service |
| Model | GPT-4.1-mini |
| Language | Python 3.10+ |
| SDK | Azure AI Projects SDK, Azure Identity |
| Agent tools | Foundry FunctionTool / `assess_claim` |
| API | OpenAI Responses API / Conversations API |
| Observability | OpenTelemetry, Azure Monitor, Application Insights |
| Evaluation | Microsoft Foundry Evaluations — Coherence + Fluency |
| Orchestration | Foundry Workflow Agent + Python SDK |
| Data | JSON / JSONL |
| Development | GitHub Codespaces |

## Agents

| Agent | Responsibility |
|---|---|
| **Claims Triage Agent** | Evidence extraction, threshold checks, missing-document detection, risk classification |
| **Claims Decision Agent** | Consumes structured triage evidence and produces an evidence-based recommendation |

## Key Engineering Controls

- Tool-grounded claim metrics and explicit thresholds
- Structured JSON contract between agents
- Human-in-the-loop escalation
- Evidence-based recommendations
- Foundry tracing + Application Insights
- Dataset-based evaluation
- Separate tool-free evaluation agent for portal evaluation

## Project Structure

```text
claims/
├── challenge-0-setup/       # Azure + Foundry setup
├── challenge-1-build/       # Triage + Decision agents
├── challenge-2-monitor/     # Tracing / Application Insights
├── challenge-3-evaluate/    # Evaluation dataset + evaluation agent
├── challenge-4-deploy/      # Python + Foundry workflow
├── knowledge/               # Demo grounding guidance
├── ARCHITECTURE.md
└── EVALUATION_PLAN.md
```

## Run

### Build agents

```bash
cd claims/challenge-1-build
python agents.py
```

### Enable monitoring

```bash
cd claims/challenge-2-monitor
python monitor.py
```

### Run production workflow

```bash
cd claims/challenge-4-deploy
python deploy.py
```

## Evaluation

Use **Microsoft Foundry → Build → Evaluations** with:

- Target: `claims-triage-agent`
- Scope: Individual turns
- Dataset: `claims/challenge-3-evaluate/eval_portal.jsonl`
- Evaluators: Coherence, Fluency

The latest successful evaluation run recorded **100% overall**, with **10/10 Coherence** and **10/10 Fluency** across 10 test cases.

## Validation

- ✅ Two persistent Foundry agents
- ✅ GenAI tracing + Application Insights instrumentation
- ✅ 10-case Foundry evaluation
- ✅ `claims-processing-workflow` deployed
- ✅ End-to-end Python orchestration
- ✅ Human-review controls and structured agent handoff

## Documentation

- [Claims scenario](./claims/README.md)
- [Architecture & engineering notes](./claims/ARCHITECTURE.md)
- [Evaluation plan](./claims/EVALUATION_PLAN.md)
- [Demo grounding guidance](./claims/knowledge/CLAIMSIGHT_DEMO_GUIDANCE.md)
- [Microsoft Foundry](https://learn.microsoft.com/azure/foundry/)
- [Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/overview)
- [Foundry evaluation](https://learn.microsoft.com/azure/foundry/how-to/evaluate-generative-ai-app)

---

<div align="center">

**Build → Monitor → Evaluate → Orchestrate/Deploy**

</div>
