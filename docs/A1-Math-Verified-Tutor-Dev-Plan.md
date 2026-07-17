---
tags: [type/note, domain/ai, domain/startup, status/active]
updated: 2026-07-03
---
> 🧠 Part of the [[Startup-MOC|Startup brain]] · synthesized into → [[Verification-Engine]] · [[Roadmap]] · [[Student-Model]] · [[Market-and-GTM]]

# A-1: Math-Verified AI Tutor for Competitive Exams — Development Plan

**Team:** 4 (Math + CS) · **Funding:** low/moderate · **Date:** June 2026
**One-line:** An AI tutor for JEE/NEET that **mathematically verifies every step it shows**, so it is *never confidently wrong* — and diagnoses the exact step where a student goes wrong.

---

## 0. The Product Thesis (don't skip)

Every "doubt-solving" app (Doubtnut, Photomath, Khanmigo, PW's AI, generic GPT) shares one fatal flaw for exam prep: **it can be confidently wrong.** A wrong intermediate step taught to a student is worse than no answer. 

Your wedge is a single, hard-to-copy promise:

> **"Every step we show you is checked by a math engine, not just an AI's guess. If we're not sure, we say so."**

This is defensible because:
1. **The verifier is real engineering** (CAS + numeric testing + domain solvers), not a prompt — most ed-tech teams *can't build it*. Your math is the moat.
2. **Honest abstention** ("I'm not fully certain — here's what I can verify") builds the trust that wins parents/teachers. Nobody else does this.
3. **The diagnostic flywheel**: pinpointing *which step* a student got wrong generates a proprietary dataset of Indian-exam step-errors that no competitor has → personalization + a fine-tuned model later.

**Scope decision:** Start with **JEE (Physics + Math)** — the verifier's sweet spot (symbolic/numeric). Expand to **NEET Physics + Physical Chemistry** (also numerical). **De-prioritize UPSC and Biology for now** — they're memorization/essay, not math-verifiable, so they don't use your moat. Lead with quantitative subjects; treat factual subjects as a later RAG-based product line.

---

## 1. The Core Moat — The Verifier (Deep Dive)

The architecture principle is **"LLM proposes, math disposes."** The LLM generates candidate reasoning; a deterministic layer verifies it; failures are repaired or abstained on.

### 1.1 Solution representation
Force the model to emit a **structured** solution, not prose. Each step carries both a human explanation *and* a machine-checkable object:

```json
{
  "given":   {"u": "20 m/s", "theta": "30 deg", "g": "9.8 m/s^2"},
  "find":    "range R",
  "steps": [
    {"id": 1, "nl": "Horizontal velocity component",
     "expr": "ux = u*cos(theta)", "op": "definition"},
    {"id": 2, "nl": "Time of flight",
     "expr": "T = 2*u*sin(theta)/g", "op": "kinematics"},
    {"id": 3, "nl": "Range = ux * T",
     "expr": "R = u**2 * sin(2*theta)/g", "op": "substitute+simplify",
     "depends_on": [1,2]}
  ],
  "final": {"symbol": "R", "value": "35.35 m"}
}
```

### 1.2 The verification layers (each is a real, winnable math problem)

| Layer                              | What it checks                          | Technique                                                                                                                                                                                                                                                                                                          | Why your team wins                                                                     |                             |                  |
| ---------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- | --------------------------- | ---------------- |
| **Final-answer equivalence**       | Is the final answer right?              | Symbolic `simplify(ans - gold)==0`; numeric within tolerance + correct units/sig-figs; normalize equivalent forms (√2/2 ≡ 1/√2)                                                                                                                                                                                    | Ground truth from your curated bank                                                    |                             |                  |
| **Step-transition check**          | Does step *i* validly imply step *i+1*? | **Random numeric equivalence testing** — substitute random values for free vars; if `expr_i` and `expr_{i+1}` disagree at random points, the step is wrong. Justified by the **Schwartz–Zippel lemma** (a non-zero polynomial is non-zero almost everywhere) → near-zero false-pass probability with a few samples | Cheap, robust, catches the algebra slips LLMs make even when the final answer is right |                             |                  |
| **Dimensional analysis** (Physics) | Are equations unit-consistent?          | `pint`: every equation must be dimensionally homogeneous                                                                                                                                                                                                                                                           | Catches a huge class of physics errors deterministically                               |                             |                  |
| **Conservation / balance** (Chem)  | Is the reaction/charge/mass balanced?   | Stoichiometry = null space of the atom-count matrix `A x = 0` over rationals → exact coefficients; charge/mass conservation                                                                                                                                                                                        | Pure linear algebra → *provably* correct, never hallucinated                           |                             |                  |
| **Self-consistency**               | Do independent solves agree?            | Sample *k* LLM solutions + an independent symbolic solve; confidence from agreement; abstain on dispersion                                                                                                                                                                                                         | Principled ensemble/confidence — statistics is your home turf                          |                             |                  |
| **Sanity constraints**             | Physically/mathematically possible?     | Domain bounds (prob ∈ [0,1], mass > 0,                                                                                                                                                                                                                                                                             | sin                                                                                    | ≤ 1), limit/boundary checks | Cheap guardrails |

### 1.3 The repair loop & the gate
```
generate (k samples) → verify each layer → 
  if all pass & confidence ≥ τ:  SHOW (verified)
  elif a step fails:             REPAIR (re-prompt with the verifier's specific failure) → re-verify (≤N retries)
  else:                          ABSTAIN ("here's the part I can verify; this part I'm unsure of")
```
**Design principle: precision over recall.** A false "verified" (wrong step shown as correct) is catastrophic for trust; abstaining is fine. Target **step-precision ≥ 99%**, even if coverage starts at ~70–80%.

### 1.4 Honest staging (the realistic risk)
Fully verifying *arbitrary* free-form reasoning is hard — translating natural-language steps into checkable form ("autoformalization") is itself error-prone. So **stage it**:
- **v1 — curated bank:** only serve problems from a bank where you already hold the **ground-truth answer** (past papers, NCERT, partner content). Gate on final-answer match + computational-step checks. Tractable, high-precision, and it's exactly what students study.
- **v2 — open problems:** extend to user-submitted/photographed problems via the full solver-verifier loop with confidence + abstention.
- **v3 — formal (optional):** Lean/Isabelle for select proof-type problems. Research flex, not a v1 dependency.

### 1.5 The long-term crown jewel — RLVR
Your verifier is a **verifiable reward function**. That's exactly what frontier math-reasoning models train on (Reinforcement Learning with Verifiable Rewards). Once you have volume, fine-tune/GRPO a small open model (e.g. a Qwen-Math-class 7B) on Indian-exam problems using your verifier as the reward signal → a **specialized model that's cheaper and better than GPT for this niche**. This folds the B-2 (cheap-model) moat *into* A-1 and crushes your inference cost at scale. This is your 12-month technical north star.

---

## 2. System Architecture

```
┌─────────────┐   ┌──────────────────┐   ┌─────────────────────────────┐
│   INTAKE    │   │  UNDERSTANDING   │   │           SOLVER            │
│ photo (OCR) │──▶│ classify subj/   │──▶│ ① retrieve (bank match)     │
│ text/LaTeX  │   │ topic/type;      │   │ ② LLM solve ×k (self-consist)│
│ voice (ASR) │   │ extract given/   │   │ ③ symbolic solve (SymPy)    │
└─────────────┘   │ find/units       │   └──────────────┬──────────────┘
                  └──────────────────┘                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         VERIFIER  (the moat)                           │
│  answer-equiv · step-transition (Schwartz–Zippel) · dimensional ·      │
│  conservation/balance · self-consistency · sanity   →  confidence/gate │
└───────────────┬───────────────────────────────────┬───────────────────┘
        fail → REPAIR loop (≤N)              pass/abstain
                                                     ▼
┌──────────────────┐   ┌───────────────────┐   ┌─────────────────────────┐
│  DIAGNOSTIC      │   │   PEDAGOGY        │   │      DELIVERY           │
│  localize wrong  │◀──│ Socratic hints,   │──▶│ WhatsApp bot + PWA;     │
│  step in student │   │ concept notes,    │   │ Hinglish + regional;    │
│  attempt; error  │   │ common-mistakes;  │   │ voice (TTS); LaTeX/img  │
│  type            │   │ vernacular gen    │   └─────────────────────────┘
└────────┬─────────┘   └───────────────────┘
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  DATA FLYWHEEL: every attempt/error/correction → labeled dataset →     │
│  mastery model (BKT/IRT) · spaced repetition · fine-tune small model   │
└──────────────────────────────────────────────────────────────────────┘
```

### Components & where math is the edge
- **Verifier** (P1): §1 — the differentiator.
- **Mastery model** (P2): **Bayesian Knowledge Tracing / Item Response Theory** for real per-skill mastery estimation (not heuristics) + a **spaced-repetition scheduler** (FSRS/half-life regression). Proper psychometrics = genuinely adaptive practice.
- **Orchestration/data/infra** (P3): LLM routing, OCR, WhatsApp, caching, data platform.
- **Product/pedagogy/partners** (P4): Socratic hint design, vernacular+voice, design-partner pilots, content pipeline.

---

## 3. Tech Stack (cheap, Python-first)

| Layer | Choice | Note / cost |
|---|---|---|
| Verifier | **SymPy**, **pint** (units), **RDKit** (chem), NumPy | Free |
| LLM (reasoning) | API: Gemini Flash / GPT-4o-mini / Claude Haiku for the 80%; escalate hard ones to a frontier model. **Route by difficulty.** | Pennies/solve; **cache** standard problems → near-zero repeat cost |
| LLM (volume / future fine-tune) | Open **Qwen-Math / DeepSeek-math-class** on **Modal/RunPod** serverless | Pay-per-use GPU; chase credits |
| Math OCR | Vision LLM first; **Mathpix** if quality demands | Start free-ish |
| Indic voice | **AI4Bharat / Sarvam** ASR+TTS; Deepgram/ElevenLabs fallback | Vernacular moat |
| Backend | **FastAPI** + Postgres + Redis | Math team lives in Python |
| Retrieval | pgvector / Qdrant over problem+concept bank | Free/cheap |
| Frontend | **WhatsApp Business API** (Gupshup/AiSensy) + **Next.js PWA** | WhatsApp = India reach, no install |
| Payments | **Razorpay** (UPI, subscriptions) | — |
| Infra | Google Cloud Run → Modal for GPU bursts | No fixed GPU cost |
| Credits | AWS Activate, Google/OpenAI/Anthropic for Startups, Modal | Funds 6–12 months of compute |

**Cost intuition:** because standard exam problems repeat, a **solution cache** gives huge hit-rates → marginal cost approaches zero on repeats. Realistic MVP burn with credits: a few hundred $/month, mostly absorbed by credits. This is genuinely buildable on low/moderate funding.

---

## 4. Phased Roadmap

### Phase 0 — De-risk the core (Weeks 0–2)  ← *do this first*
Prove the one thing that can kill the company: **does verification actually lift correctness enough to matter?**
- Dataset: **100 JEE Main Physics problems** (mechanics + electricity) with known answers.
- Build (throwaway): typed/LaTeX intake → LLM structured solution → verifier (numeric step-check + dimensional + final-answer vs ground truth) → 1 repair retry → confidence/abstain.
- **Measure:** raw-LLM final-answer accuracy **vs** verified-pipeline accuracy; and step-precision.
- **Success gate:** pipeline lifts final-answer accuracy to **≥95%** and step-precision to **≥99%** (by abstaining when unsure). If yes → build. If verification proves intractable in your timeline → reconsider scope.
- In parallel (P4): 3 coaching-institute conversations; collect 50 of their problems + 5 student testers; apply for credits.

### Phase 1 — Verified-solutions MVP on a curated bank (Weeks 3–8)
- Ingest a **problem bank** (past papers + NCERT + partner content) with ground-truth answers; tag subject/topic/type.
- Pipeline: intake (typed + **photo OCR**) → solve → verify → render **step-by-step** with Socratic hint mode (reveal one step at a time) → **Hinglish + voice**.
- Ship via **WhatsApp + PWA** to design-partner students.
- **KPIs:** % verified (coverage), step-precision, student-rated helpfulness, p50 latency.

### Phase 2 — Practice + diagnostic engine (the flywheel) (Weeks 9–16)
- Student solves; system **localizes the first wrong step** and classifies error (conceptual / computational / careless) → targeted remediation.
- Begin capturing **step-error data**. Add **mastery model (BKT/IRT)** + **spaced repetition** + weak-area dashboard.
- **KPIs:** diagnosis-accuracy (does the student agree the flagged step is where they erred?), problems/student/week, D7/D30 retention.

### Phase 3 — Personalize, monetize, fine-tune (Months 5–8)
- Adaptive problem selection from mastery model; mock tests + analytics.
- **B2B institute dashboard** (cohort weak-areas, usage, outcomes) → the paying product.
- Start the **RLVR fine-tune** of a small model on captured verified data → cut inference cost.
- **KPIs:** paid conversion, ₹ MRR, institutes live, cost/solve trend.

---

## 5. Content, Distribution & Data — solved by ONE move

The hardest non-tech problems (content rights, distribution/CAC, and labeled data) are **all solved by the B2B2C coaching-institute partnership**:
- **Content:** institutes have huge vetted problem banks → they give you content.
- **Distribution:** they have students → near-zero CAC; you co-brand/white-label.
- **Data:** their students generate your step-error flywheel.
- **Revenue:** per-seat licensing (real money) vs thin B2C subscriptions.

Target the **thousands of small/mid coaching centers** who can't build AI and need to compete with Physics Wallah/Allen/Unacademy. That's your beachhead; direct-to-student B2C app is the long-tail second.

**Pricing:** B2C ₹199–499/mo; B2B ₹X/seat/month to institutes (the core of revenue).

---

## 6. Evaluation — your proof *and* your moat

Build a **gold benchmark** early: N problems with known answers + expert step annotations. Track relentlessly:

| Metric | Target | Why it matters |
|---|---|---|
| **Step-precision** (when we say "correct," it is) | **≥ 99%** | A false "verified" destroys trust — the #1 metric |
| Final-answer accuracy | ≥ 95% | Core correctness |
| Coverage (% confidently answered) | ≥ 80% (grow over time) | Abstention is OK early |
| Diagnosis accuracy | ≥ 90% | Powers the flywheel |
| p50 latency | < 8s typed / < 20s photo | UX |
| Cost / solve | < ₹1 (→ <₹0.2 with cache) | Unit economics |

**Principle: honest uncertainty beats confident hallucination.** Optimize precision; grow coverage as the verifier matures.

---

## 7. Team Roles (4 people)

| Person | Owns | Skills |
|---|---|---|
| **P1** | **Verifier + solver core** (the moat) | Strongest math + CAS/SymPy; symbolic + numeric methods |
| **P2** | **ML/personalization**: BKT/IRT, spaced repetition, evals, later RLVR fine-tune | Stats/ML, optimization |
| **P3** | **Backend + data platform + integrations**: LLM orchestration, OCR, WhatsApp, caching, infra | Systems/CS |
| **P4** | **Product + pedagogy + GTM**: Socratic UX, vernacular/voice, design partners, content pipeline | Product sense, communication, owns users |

Everyone codes; ownership is for accountability. **P4 (users/partners) is as critical as P1 (tech)** — a perfect verifier with no students is a dead project.

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **Autoformalization gap** (NL→checkable is itself error-prone) | Stage: curated bank + computational-step checks first; abstain when unsure; expand to open problems carefully |
| **Verifier false positives** | Conservative thresholds, abstention, human-in-loop spot-checks early; obsess over step-precision |
| **Content/copyright** of past papers | Lean on NCERT (govt) + partner-supplied + own-authored content; legal care with copyrighted papers |
| **Distribution/CAC** | B2B2C via institutes; don't depend on B2C ads early |
| **Big incumbents add AI** (PW "Sahi", Unacademy) | Compete on *verified correctness + diagnosis* (their AI isn't verified) and sell to the long tail of institutes they don't serve; be a partner/acquisition target, not a head-on rival |
| **Low B2C ARPU** | Revenue from institute licensing, not consumer subs |
| **LLM cost at scale** | Aggressive caching (problems repeat!), cheap-model routing, RLVR small-model later |
| **Biology/UPSC pull** | Resist until quantitative core is strong; those need a different (RAG) build |

---

## 9. The 2-Week Kickoff (concrete, start Monday)

**Goal:** prove the verifier lifts correctness on 100 JEE Physics problems, and line up 3 design partners.

- **Day 1–2:** Curate 100 JEE Main Physics problems (mechanics + electricity) with ground-truth answers in a spreadsheet (problem LaTeX, answer, units, topic).
- **Day 3–6 (P1+P3):** Build the structured-solution prompt (JSON steps) + SymPy **numeric step-checker** (Schwartz–Zippel sampling) + **dimensional check** (pint) + final-answer comparator. Wire a 1-retry repair loop.
- **Day 7–9 (P2):** Build the eval harness: run raw-LLM vs verified-pipeline over the 100; compute final-answer accuracy, step-precision, coverage, latency, cost.
- **Day 4–10 (P4, parallel):** Contact 10 coaching institutes; aim for **3 pilots**; collect 50 of their problems + 5 student testers. Apply for AWS Activate + Google/OpenAI/Anthropic startup credits.
- **Day 10–12:** Add a minimal **WhatsApp** front-end: send a problem (text), get a verified step-by-step reply.
- **Day 13–14:** Decision review against the gate (≥95% final accuracy, ≥99% step-precision, partner interest). **Go / iterate / reconsider.**

**Definition of done for the kickoff:** a chart showing the verified pipeline beating raw LLM on accuracy, a working WhatsApp demo on 5 real student problems, and ≥1 institute that wants the pilot.

---

## 10. KPIs to watch (first 6 months)
- **Tech:** step-precision, final-answer accuracy, coverage, cost/solve, latency.
- **Engagement:** problems/student/week, hint-completion, D7/D30 retention, % "this helped."
- **Flywheel:** labeled step-errors collected, diagnosis-accuracy.
- **Business:** institutes piloting → paying, seats live, ₹ MRR, CAC (institute vs direct).

---

### Appendix A — Why this is genuinely a *math team's* company
The verifier (symbolic + Schwartz–Zippel numeric testing + linear-algebra stoichiometry + dimensional analysis), the mastery model (BKT/IRT psychometrics), the spaced-repetition optimization, and the eventual RLVR small-model are all real math/CS. The wrapper crowd cannot follow you here. That asymmetry *is* the business.
