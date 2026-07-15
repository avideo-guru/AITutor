---
tags: [type/architecture, domain/startup, startup/architecture, decision/anchor]
updated: 2026-07-15
status: PROPOSAL — brainstorm output (2026-07-15 session), ready for lane assignment
---
# 🔁 Adaptive Loop — research, architecture, roadmap

> **One-line:** fuse the JEPA pattern (cheap latent student-state, expensive
> decoder invoked selectively) with our existing RAG + verifier pipeline and a
> Squirrel-AI-style closed learning loop — so the LLM becomes a *selectively
> invoked decoder* inside a loop we own, instead of the brain of every request.

> **How this relates to existing docs:** extends [[Student-Model]] (and
> resolves its open `BKT vs IRT vs Elo` decision: **Elo first**), plugs into
> the seams built in [[Opus-Execution-Plan]] P1, and shares its item bank with
> the P3 golden set. It does **not** replace any phase of the Opus plan — it is
> a parallel lane (Phases A–D below) that consumes P0's flywheel and P5's
> verifier.

## 0. Thesis — own the loop; the model falls out of it

Cursor (Composer), Squirrel AI (LAM), and DeepSeek (R1) are the same story:
whoever owns the environment where actions get *verified* ends up owning the
model, almost for free. The sequence is always **loop → data → model**, never
the reverse. Ranked by defensibility, what we hold:

1. **The event log + knowledge base** — data assets; compound daily; cannot be
   copied backwards in time. Squirrel AI's real moat was ~10 years of logged
   learning behavior, not their algorithm.
2. **The mechanical verifier** ([[Verification-Engine]]) — hard engineering;
   the correctness guarantee nobody else offers; later doubles as an RLVR
   reward function (the R1 recipe).
3. **The orchestration/harness** — valuable, but re-buildable by a competitor
   in months. Table stakes, not moat.
4. **Models** — commodity today (DeepSeek/Gemini), ours later (distilled,
   Phase D). Never the moat (the Harvey lesson in [[Opus-Execution-Plan]] §1).

Everything below is arranged so the cheap-to-build parts (schema, Elo, one
endpoint) feed the impossible-to-copy parts (the log, the verifier corpus).

**Why this is economically decisive for the ₹0 phase:** an adaptive decision
(serve next item, mark mastery, schedule review) is one SQL query ≈ ₹0;
verification is CPU-side SymPy ≈ ₹0; only an *explanation* costs an LLM call.
Marginal cost scales with explanations requested, not with learning activity —
every GPT-wrapper competitor pays a frontier-LLM call on *every* interaction.
The gap widens as students practice more (cheap) relative to asking (expensive).

## 1. Research foundations (annotated reading list)

Grouped by what we take from each. Items marked 📥 are candidates for
`docs/Research/Papers/` + [[Papers-Index]].

### 1.1 JEPA family — the architecture pattern
- 📥 **I-JEPA** — Assran et al. 2023, <https://arxiv.org/abs/2301.08243>.
  *Take:* predict in **representation space**, not output space. Applied to
  learners instead of images = predict the student's future knowledge-state
  embedding, not their next answer token.
- 📥 **VL-JEPA** — Chen et al. 2025, <https://arxiv.org/abs/2512.10942>.
  *Take:* **selective decoding** — a cheap latent predictor handles
  classification/retrieval/routing; the text decoder is invoked only when text
  must actually be produced (they report 2.85× fewer decode ops, ~50% fewer
  trainable params). This is our cost architecture in one sentence.
- **LeCun, "A Path Towards Autonomous Machine Intelligence"** (position paper,
  2022) — <https://openreview.net/forum?id=BZ5a1r-kVsf>. *Take:* the framing —
  a world model (student model) + a cheap policy (orchestrator) + an actuator
  (LLM decoder). Background reading, not implementation.

### 1.2 Knowledge tracing — the state estimator
- **BKT** — Corbett & Anderson 1995, <https://doi.org/10.1007/BF01099821>.
  The original mastery model (4-parameter HMM per skill). *Take:* the concept;
  we start simpler (Elo) and skip to attention models later.
- **Elo for adaptive practice** — Pelánek 2016,
  <https://doi.org/10.1016/j.compedu.2016.03.017>. *Take:* **our v1
  estimator.** Student rating + item rating per knowledge component; one
  UPDATE per attempt; no training, no cold-start model, well-studied in
  production (used by e.g. Duolingo-class systems).
- 📥 **DKT** — Piech et al. 2015, <https://arxiv.org/abs/1506.05908>. First
  neural KT (LSTM). Historical anchor for Phase C.
- 📥 **SAKT** — Pandey & Karypis 2019, <https://arxiv.org/abs/1907.06837>.
  Self-attention KT — small, simple, strong baseline; ~1M params trains on a
  free Colab GPU.
- 📥 **AKT** — Ghosh et al. 2020, <https://arxiv.org/abs/2007.12324>.
  Context-aware attentive KT, monotonic attention + IRT-style difficulty; the
  strongest published baseline to beat in Phase C.
- 📥 **Knowledge Tracing: A Survey** — Abdelrahman et al. 2022,
  <https://arxiv.org/abs/2201.06953>. The field map; read before Phase C.
- **pyKT** — <https://pykt.org> (github `pykt-team/pykt-toolkit`).
  Standardized KT benchmarks/implementations — Phase C starts here, not from
  scratch.
- **Duolingo half-life regression** — Settles & Meeder 2016,
  <https://aclanthology.org/P16-1174/>. *Take:* review scheduling as decay
  estimation, feature-based, cheap.
- **FSRS** — <https://github.com/open-spaced-repetition> . *Take:* the
  `due_at` scheduler for `student_kc_state` (already flagged in
  [[Opus-Execution-Plan]] §Resources for the Student-Model phase).

### 1.3 Adaptive systems — the loop design (what we borrow from whom)
- **Knowledge Space Theory (ALEKS)** — Doignon & Falmagne;
  practitioner overview: <https://www.aleks.com/about_aleks/knowledge_space_theory>.
  *Take:* mastery as a **prerequisite partial order**; adaptivity = probing
  the outer fringe of what the student can do. 1980s academic theory, free to
  use.
- **Squirrel AI (IALS / LAM)** — <https://squirrelai.com>; LAM announcement:
  [PR Newswire 2024-07-01](https://www.prnewswire.com/news-releases/squirrel-ai-debuts-enhanced-large-multimodal-adaptive-model-revolutionizing-its-educational-software-and-hardware-systems-302186596.html).
  *Take:* the **closed loop** (assess → practice → learn → test → teach on one
  surface) and **super-fine knowledge points** (they claim ~30k+ KCs; we start
  at ~50/chapter, depth 3). *Do not take:* their scale claims at face value —
  the transferable asset is the loop discipline, and their real moat was the
  log, which we must grow ourselves. Their China-lock means no channel
  conflict in India, but it buys us time, not the finish line.
- **Cognitive Tutors (Carnegie Learning)** — Anderson et al. 1995,
  <https://doi.org/10.1207/s15327809jls0402_2>. *Take:* **misconception
  tagging** — log *why* an answer was wrong (conceptual / computational /
  careless), not just that it was. Our verifier localizes the first wrong step
  (P5), which is exactly the input this needs.
- **Caution (only IP note):** BKT/DKT/Elo/KST are open literature, but avoid
  verbatim reimplementation of ALEKS's or Squirrel's *patented item-selection
  procedures* if we ever enter the US. Concept-level borrowing is standard.

### 1.4 Verified reasoning as reward — the Phase D bridge
- 📥 **DeepSeek-R1** — <https://arxiv.org/abs/2501.12948>. RL on verifiable
  rewards produces reasoning without human labels. *Take:* our verifier verdict
  IS this reward function, for our domain, already planned as P5.
- 📥 **Tülu 3 (RLVR)** — Lambert et al. 2024, <https://arxiv.org/abs/2411.15124>.
  Named and systematized RLVR. *Take:* the recipe details when Phase D arrives.
- **Cursor Composer** — <https://cursor.com/blog/composer>. *Take:* the
  pattern — specialize a small model by doing RL **inside your own harness**;
  kernel-level work (custom MXFP8 MoE kernels, quantization, GEMM-level
  optimization) pays off **only at self-hosted serving scale**. For us that is
  Phase D, explicitly not before.

### 1.5 Public datasets — cold-start for Phase C (pretrain before we have logs)
- 📥 **EdNet** — Choi et al. 2019, <https://arxiv.org/abs/1912.03072>. 131M
  interactions, Korean TOEIC platform (Santa/Riiid). Largest public KT corpus.
- **Eedi / NeurIPS 2020 Education Challenge** —
  <https://arxiv.org/abs/2007.12061>. Diagnostic questions with misconception
  labels — closest public analog to our misconception tagging.
- **ASSISTments** — <https://sites.google.com/site/assistmentsdata/>. The
  classic KT benchmark family (math, US middle school).
- *Use:* pretrain the Phase C model on these, fine-tune on our log — the
  standard KT transfer setup in pyKT. None are JEE-specific; they de-risk the
  architecture, not the final weights.

## 2. What exists today (the substrate we plug into)

From `backend/schema.sql` + `backend/app/` after P0+P1 (merged to `main`,
PR #5):

- **Pipeline** (`orchestrator/pipeline.py`): `Retrieve → build prompt →
  Reason(stream) → [Verify: P5] → Teach(SSE) → Log` — the *decoder path* in
  this design. Stays untouched.
- **`traces` table (P0.2)** — the per-*ask* flywheel already spinning
  (`classification, chunks, gate_outcome, verify, stage_latency_ms`).
- **`sessions.feedback_*` + `thread_id` (P0.3)** — feedback + history wiring.
- **Seams (P1)** — `Retriever` Protocol, model Router, thin routes. The new
  `StateEstimator` Protocol below copies this exact pattern.
- **`verify/` stub** — P5 lands the verifier; its verdicts become both attempt
  labels (this doc) and, eventually, RLVR rewards (Phase D).

What's *missing* for a closed loop: the system only reacts to questions asked
(`/v1/ask`). It has no notion of items, knowledge components, mastery, or
"what should this student do next." That is the entire gap this design closes.

## 3. Architecture design

### 3.1 The loop

```
            ┌──────────────────────────────────────────────────┐
            │                 student session                  │
            └───────┬──────────────────────────────▲───────────┘
                    │ attempts, hints, time        │ next item / explanation
                    ▼                              │
        ┌───────────────────┐            ┌─────────┴──────────┐
        │ event log         │            │ mechanical verifier │  ← P5
        │ (attempts,traces) │            │ "math disposes"     │
        └───────┬───────────┘            └─────────▲──────────┘
                ▼                                  │ (only when LLM ran)
        ┌───────────────────┐            ┌─────────┴──────────┐
        │ state estimator   │            │ LLM decoder         │  ← existing
        │ Elo now,JEPA later│            │ pipeline.run()      │    pipeline
        └───────┬───────────┘            └─────────▲──────────┘
                ▼                                  │ selective: explain/hint only
        ┌───────────────────┐   cheap path         │
        │ orchestrator      ├──────────────────────┤
        │ policy: /v1/next  │   serve item (SQL, no LLM)
        └───────┬───────────┘
                ▲ reads
        ┌───────┴───────────────────────────────────┐
        │ knowledge base: KC graph + items + chunks │
        └────────────────────────────────────────────┘
```

**Selective-decoding rule (the VL-JEPA transplant):** the LLM is invoked only
when (a) the student explicitly asks (`/v1/ask`, unchanged), (b) a wrong
attempt + "explain" tap — RAG pre-filtered to the item's chapter, or (c) a
hint request that pre-authored hints can't cover. Everything else — item
selection, mastery updates, review scheduling — is SQL.

### 3.2 Data model (additive migrations, same style as P0)

```sql
-- Migration (A.1): knowledge graph. IDs are human-readable paths so content
-- tagging is reviewable in a diff ('phy.mech.kinematics.projectile').
create table if not exists knowledge_components (
  id text primary key,
  subject text not null, chapter text not null,
  name text not null,
  depth int not null default 3          -- 1=subject 2=chapter 3=microconcept
);
create table if not exists kc_edges (        -- prerequisite DAG (ALEKS/KST)
  prereq text not null references knowledge_components on delete cascade,
  postreq text not null references knowledge_components on delete cascade,
  primary key (prereq, postreq)
);

-- Migration (A.2): item bank. The P3 golden set (gold answer as sympy expr +
-- value + unit) uses the SAME answer_gold shape — golden problems are items
-- with an eval tag; curate once, use twice.
create table if not exists items (
  id uuid primary key default gen_random_uuid(),
  kc_id text not null references knowledge_components,
  stem text not null,                    -- LaTeX, $...$ convention as today
  answer_gold jsonb not null,            -- {expr, value, unit, choices?}
  hints jsonb,                           -- pre-authored ladder, cheap path
  difficulty real not null default 0,    -- Elo item rating, updated online
  source_ref text, content_hash text unique,
  created_at timestamptz default now()
);

-- Migration (A.3): the practice event log. Append-only; same retention rules
-- as traces (raw 18mo / aggregates forever, DPDP: no PII beyond user_id FK).
create table if not exists attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles on delete cascade,
  item_id uuid not null references items,
  correct boolean,
  response jsonb,                        -- raw answer as given
  time_ms int, hints_used int not null default 0,
  verify jsonb,                          -- P5 verdict when the LLM explained
  error_class text,                      -- conceptual|computational|careless (P5+)
  created_at timestamptz default now()
);
create index if not exists attempts_user_idx on attempts (user_id, created_at desc);

-- Migration (A.4): mastery state — ONE ROW per (student, KC); the "latent".
create table if not exists student_kc_state (
  user_id uuid not null references profiles on delete cascade,
  kc_id text not null references knowledge_components,
  rating real not null default 0,        -- Elo; later: JEPA-derived mastery
  attempts int not null default 0, correct int not null default 0,
  last_attempt_at timestamptz, due_at timestamptz,   -- FSRS review scheduling
  updated_at timestamptz default now(),
  primary key (user_id, kc_id)
);
```

RLS: same posture as `sessions` (enable + own-rows select policy; backend uses
service role).

### 3.3 Backend modules (mirrors the P1 seam style)

```
backend/app/adaptive/
  __init__.py
  state.py      # StateEstimator Protocol + EloEstimator (v1)
  policy.py     # next-item selection (frontier + due reviews + target p≈0.7)
backend/app/routes/
  practice.py   # POST /v1/attempts · GET /v1/next
```

- **`StateEstimator` Protocol** — `update(user, item, outcome) -> None` and
  `mastery(user, kc) -> float`. `EloEstimator` v1: expected
  `p = 1/(1+10^((R_item−R_student)/400))`; `R_student += K·(outcome−p)`;
  item rating updated inversely with a decaying K (Pelánek 2016). Uncertainty
  proxied by attempt count. Swapping in the Phase C model is a new
  implementation of the same Protocol — the Retriever-Protocol trick again.
- **Policy v1 (pure SQL + ~100 lines):** candidates = *frontier* KCs (all
  prereqs ≥ mastery threshold, self < threshold) ∪ *due reviews*
  (`due_at <= now()`); pick the item whose rating gives target success
  probability ≈ 0.7 (desirable difficulty); exclude recently seen items.
- **API contracts:**
  - `GET /v1/next?subject=physics` → `{item: {id, stem, kc_id, choices?},
    reason: "frontier|review", mastery_snapshot: {...}}`
  - `POST /v1/attempts` `{item_id, response, time_ms, hints_used}` →
    `{correct, rating_delta, next_hint?}` — grades against `answer_gold`
    (numeric/choice compare v1; sympy equivalence when P5 utilities exist),
    updates Elo + FSRS `due_at` in one transaction.
- **Not touched:** `/v1/ask`, SSE protocol, quota, router, verifier placement.
  Practice attempts don't consume the LLM question quota (they cost ~₹0).

### 3.4 Student-JEPA (Phase C spec, kept honest)

- **Input:** per-student event sequence `(kc embedding, correct, time bucket,
  hints)`; **context encoder:** 2–4 layer transformer (~1–10M params);
  **objective:** I-JEPA-style — predict the *embedding* of a masked/future
  window of events produced by an EMA target encoder; loss in latent space.
- **Probe/eval:** linear head → next-attempt correctness AUC + calibration,
  benchmarked against `EloEstimator` and AKT (via pyKT) on the same split.
  Ship only if it beats Elo out-of-sample — pre-registered, P3-style rule.
- **Serving:** nightly batch job writes per-KC mastery into
  `student_kc_state.rating` — the online system never changes shape.
- **Pretraining:** EdNet/Eedi/ASSISTments, fine-tune on our log (§1.5).
- **Research upside:** JEPA-style KT is essentially unexplored — publishable
  by a math-first team; fits the research → build loop in [[Startup-MOC]].

### 3.5 Phase D — the fusion becomes our LAM (gated, not scheduled)

Student-JEPA world model decides → LLM decoder speaks → verifier disposes →
RLVR (verifier verdict + gold answers as reward) distills into a small
self-hosted tutor model (R1/Tülu-3 recipe). **Only here** do quantization,
serving, and kernel/GEMM-level optimization enter (the Composer lesson).
Gates: funding + paid tier + P5 false-verified <1% + eval harness mature.

## 4. Roadmap (Phases A–D) and how it meshes with the Opus plan

| Phase | What ships | Cost | Effort | Gate to enter | Meshes with |
|---|---|---|---|---|---|
| **A — log + graph** | Migrations A.1–A.4; KC graph for ONE chapter (~50 KCs, Physics–Optics or Mechanics); attempts logged | ₹0 | 3–5 days | none — start anytime | parallel to P2/P3; golden-set problems get `kc_id` tags (curate once, use twice) |
| **B — closed loop** | `EloEstimator` + policy + `/v1/next` + `/v1/attempts`; minimal practice screen (UI lane); FSRS `due_at` | ₹0 | 1–2 weeks | item bank ≥ ~150 items for the chapter (NCERT exemplar + past papers, same sourcing as P3) | resolves [[Student-Model]] open decision; D7 retention KPI now measurable on *practice*, not just asks |
| **C — learned estimator** | SAKT/AKT baseline then Student-JEPA (§3.4); nightly batch; A/B vs Elo | ₹0 (Colab/Kaggle GPU) | 2–4 weeks research-lane | ≥100k logged attempts OR public-data pretrain; P3 eval discipline applies | uses pyKT; paper opportunity |
| **D — own model (LAM)** | RLVR distillation, self-hosted small model, kernel/quant work | funded | quarters | funding + paid tier + P5 shipped with false-verified <1% | consumes P5 verdicts as rewards; Cursor sequence completes |

**Sequencing note:** A and B are deliberately boring and SQL-shaped — they are
to the adaptive lane what P0 was to the ask lane: the flywheel. C and D are
gated bets that cost nothing until their gates open. **Do not block the
product on JEPA** — the loop must work (and retain students) on Elo alone; if
it doesn't, no model fixes it (the Khanmigo lesson: engagement > cleverness).

**Suggested lane split:** backend account — migrations + `adaptive/` +
`practice.py` (Phase A–B server side); UI account — practice screen + the
still-missing feedback UI (same screen, two birds). Phase C is a research
lane either account can own.

## 5. Competitive positioning (why this square is open)

| Player | Has | Lacks |
|---|---|---|
| Coursera / Pearson | content breadth, distribution | exam-depth adaptivity; verified reasoning |
| ALEKS / Carnegie | 20+ yrs knowledge tracing | LLM-era explanation; India/JEE presence |
| Squirrel AI | the closed loop + the log | India access (China-locked); verification |
| Chegg | brand (fading) | lost to raw ChatGPT; no correctness guarantee |
| GPT-wrapper tutors | frontier LLM answers | per-interaction economics; adaptivity; verification |
| **Us** | loop + verifier + JEE depth at Indian price | the log (starts at zero — which is why Phase A ships first) |

The open square: **exam-specific depth × verified correctness × adaptive loop
× Indian price point.** Every attempt logged widens the gap; nobody can buy
our log.

## 6. Risks & open questions

- **Item-bank curation is the real cost** — pure human hours, not code
  (Squirrel spent years here). Mitigation: reuse P3 golden problems; NCERT
  exemplar; start with ONE chapter and prove retention before scaling content.
- **Engagement risk:** a practice loop students don't return to is a dead
  loop. D7 on practice is the Phase B KPI, pre-registered like the
  [[Viability-Brutal-Honesty]] kill criteria.
- **DPDP:** attempts are behavioral data of likely-minors — same rules as
  traces (no PII, 18mo raw retention, aggregates forever, India region).
- **KC granularity creep:** resist 30k-KC fantasies; depth-3, ~50/chapter,
  split only when the data shows a KC hides two skills.
- `#decision/open` grading engine for `POST /v1/attempts` v1: numeric/MCQ only
  (ships in Phase B) vs waiting for P5's sympy utilities (richer, later)?
  Recommendation: numeric/MCQ v1, upgrade in place.
- `#decision/open` does the practice loop live inside the existing thread UI
  or a separate tab? (UI lane call.)

## Connections
- Extends → [[Student-Model]] (resolves its v1-mastery decision: Elo) ·
  Plugs into → [[Opus-Execution-Plan]] (P1 seams, P3 golden set, P5 verifier)
- Economics guard → [[Viability-Brutal-Honesty]] §3.1 · Moat logic →
  [[Durable-Moat]] · Verifier spec → [[Verification-Engine]]
- Status board → [[Status]] · Hub → [[Startup-MOC]]
