# Energy Aware Chat Session 17 backlog

Status: controlled intake list for class-inspired improvements before standalone extraction.

This backlog exists so Energy Aware Chat can keep learning from LIDR sessions without becoming chaotic.

## Intake rule

A new class-inspired idea may enter this backlog only if it improves at least one of these product goals:

1. Better evidence grounding.
2. Better evaluation rigor.
3. Better repair or rejection decisions.
4. Better observability.
5. Better demo clarity.
6. Better deployment readiness.
7. Better final-project grading alignment.

Do not add generic framework work unless it directly improves the product.

Reject as scope creep any idea that mixes Energy Aware Chat, Energy Aware Code, Session 08, Session 09, adapters, provider changes, and deployment work in one patch.

## Candidate post-checkpoint layers

| Priority | Layer | Why it matters | Acceptance proof |
| --- | --- | --- | --- |
| P0 | Project-source RAG | Grounds project claims in docs and repo files | retrieval tests plus Energy Card evidence refs |
| P0 | Fixed eval dataset | Enables honest quality comparison | versioned cases plus report artifact |
| P1 | Agent orchestration | Separates retriever, critic, decider, and repairer | deterministic trace plus tests |
| P1 | Live DeepSeek benchmark run | Converts fake-provider harness into measured evidence | saved report with claim boundary |
| P1 | Streamlit export report button | Makes demo reviewer-friendly | UI helper tests and manual smoke |
| P2 | Deployment proof | Satisfies public demo expectation | deployed URL or video proof |
| P2 | Cost and latency card | Makes model tradeoffs visible | metrics contract and tests |
| P2 | Final README polish | Makes the project portfolio-ready | documentation tests |

## Do not implement yet

Do not implement these until the core evidence and eval layers are stable:

1. Multi-agent debate.
2. Autonomous repository edits.
3. Automatic Git commits.
