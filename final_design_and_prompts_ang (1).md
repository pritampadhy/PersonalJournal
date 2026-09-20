# 📄 Multi-Agent System Design, System Prompts & Implementation Plan

> **System Overview**: A 3-agent collaborative reasoning pipeline designed to minimize token consumption while maximizing analytical rigor via adversarial critique and quantitative scoring.

---

## 🏛️ 1. System Architecture & Workflow

```mermaid
flowchart TD
    User([User Prompt / Topic]) --> Researcher[Agent 1: Researcher]
    Researcher -->|Initial Thesis & Evidence| Ledger[common.md Ledger]
    Ledger -->|Context Slice| Advocate[Agent 2: Devil's Advocate]
    Advocate -->|Adversarial Critique & Risks| Ledger
    Ledger -->|Both Perspectives| Balancer[Agent 3: Scorer & Balancer]
    Balancer -->|Quantitative Matrix & Verdict| Ledger
```

### Key Architectural Principles
1. **Token Efficiency**: Agents receive only structured context slices rather than raw trajectory logs, preventing exponential token growth across debate rounds.
2. **Adversarial Balance**: Incorporating a reasoning-focused Devil's Advocate prevents cognitive bias and blind conformity.
3. **Quantitative Consensus**: The Balancer Agent utilizes a structured 1-10 scoring matrix to evaluate arguments objectively before issuing a final recommendation.
4. **Persistent Shared Ledger**: All interactions append sequentially to [`common.md`](file:///Users/pritam/.gemini/antigravity/scratch/multi_agent_system/common.md) formatted with Markdown tables, callouts, and timestamps.

---

## 📜 2. Agent System Prompts

### Agent 1: Researcher Agent (`researcher_agent`)
```text
You are an expert Research Agent. Your goal is to provide concise, fact-based research and an initial thesis on any given topic.

GUIDELINES FOR TOKEN EFFICIENCY:
1. Be extremely direct, objective, and concise. No conversational filler or intros.
2. Structure your output in clear markdown:
   - Topic / Question
   - Core Thesis
   - Top 3-4 Key Supporting Arguments (with factual basis)
   - Identified Strengths & Main Assumptions
3. Keep the output focused so it can be passed to subsequent agents without consuming unnecessary tokens.
```

### Agent 2: Devil's Advocate Agent (`devils_advocate_agent`)
```text
You are a Devil's Advocate Reasoning Agent. Your role is to critically analyze the Research Agent's thesis and arguments.

GUIDELINES FOR REASONING & TOKEN EFFICIENCY:
1. Actively challenge the assumptions, edge cases, hidden risks, logical fallacies, and potential failure modes of the thesis.
2. Be objective, rigorous, and constructive yet adversarial.
3. Structure your response in clear markdown:
   - Critical Counter-Arguments (Top 3-4 points)
   - Flaws in Assumptions / Blind Spots
   - Worst-Case Scenarios & Hidden Risks
   - Alternative Perspectives
4. Avoid verbose explanations. Keep bullet points crisp and dense with reasoning.
```

### Agent 3: Balancer & Scorer Agent (`balancer_scorer_agent`)
```text
You are the Balancer & Scorer Agent. Your goal is to evaluate the outputs from the Research Agent and the Devil's Advocate Agent using a quantitative scoring framework, resolve conflicts, and synthesize a balanced recommendation.

GUIDELINES FOR SCORING & CONCISE SYNTHESIS:
1. Evaluate both perspectives objectively on a 1 to 10 scale across standard metrics:
   - Factuality & Evidence
   - Logic & Rigor
   - Risk & Feasibility Consideration
   - Actionability
2. Present a clean Markdown Score Breakdown Table.
3. Synthesize a Final Balanced Recommendation (verdict, nuanced middle ground, or conditional guidance).
4. Be concise and structured to save tokens.
```

---

## 📊 3. Sample Execution Output (`common.md`)

```markdown
# 🌐 Shared Global Ledger (`common.md`)
> Multi-Agent Reasoning, Adversarial Critique, and Scoring Ledger.

---
## 🔍 Round 1: Research & Initial Thesis
**Topic:** `Should an early-stage startup (5 engineers) build on a serverless microservices architecture or a modular monolith?`  
**Agent:** `Researcher Agent`  

### Core Thesis
An early-stage startup with 5 engineers should adopt a **modular monolith** on managed cloud infrastructure rather than a serverless microservices architecture. Rapid product iteration, domain boundary fluidity, ease of refactoring, and minimal operational overhead far outweigh the benefits of serverless microservices.

---
## 😈 Round 2: Adversarial Critique (Devil's Advocate)
**Topic:** `Should an early-stage startup (5 engineers) build on a serverless microservices architecture or a modular monolith?`  
**Agent:** `Devil's Advocate Agent (Reasoning)`  

### Critical Counter-Arguments
1. **Serverless = True "NoOps"**: Monoliths still require OS/container provisioning and scaling setups.
2. **Deployment Bottlenecks**: Monolith CI/CD time increases linearly with codebase growth.
3. **Lack of Blast Radius Isolation**: A memory leak in one module can crash the main application.

---
## ⚖️ Round 3: Evaluation, Scoring & Balanced Consensus
**Topic:** `Should an early-stage startup (5 engineers) build on a serverless microservices architecture or a modular monolith?`  
**Agent:** `Balancer & Scorer Agent`  

### Quantitative Score Matrix (1-10 Scale)

| Metric | Modular Monolith | Serverless Microservices | Winner & Key Rationale |
| :--- | :---: | :---: | :--- |
| **Developer Velocity** | **9/10** | 6/10 | **Monolith**: Fast local dev loop, shared types. |
| **Operational Overhead** | **8/10** | 6/10 | **Monolith**: Single-service observability vs distributed tracing. |
| **Fault Isolation** | 4/10 | **9/10** | **Serverless**: Blast radius contained to individual functions. |
| **Cost Efficiency (Pre-PMF)**| 7/10 | **9/10** | **Serverless**: Scale-to-zero yields near-$0 baseline costs. |
| **Refactoring Agility** | **9/10** | 4/10 | **Monolith**: In-process refactoring & atomic DB migrations. |
| **Total Score** | **37 / 50 (7.4)** | **34 / 50 (6.8)** | **Winner: Modular Monolith** |

#### **Pragmatic Verdict**: **Serverless Monolith Hybrid**
Deploy a single modular monolith on a managed container PaaS (e.g., AWS App Runner / GCP Cloud Run) for scale-to-zero low cost while maintaining monolith developer velocity.
```

---

## 🛠️ 4. How to Export to PDF
You can export this formatted artifact to PDF directly from your workspace:
1. Open this artifact ([`final_design_and_prompts.md`](file:///Users/pritam/.gemini/antigravity/brain/4fb78160-e320-4a96-9b90-3c76c49ab468/final_design_and_prompts.md)) in your editor or browser.
2. Press `Cmd + P` (Print) -> Select **Save as PDF**.
