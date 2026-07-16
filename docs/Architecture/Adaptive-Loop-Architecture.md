---
tags: [type/architecture, domain/startup, startup/architecture, decision/anchor]
updated: 2026-07-16
status: ACTIVE — A.0 shipped 2026-07-16 (PR #8); next step is A.1 (migrations)
---
# 🔁 Adaptive Loop — research, architecture, roadmap

> **One-line:** a **JEPA-inspired** loop (cheap student state, expensive decoder
> invoked selectively) fused with our existing RAG + verification pipeline and a
> Squirrel-AI-style closed learning loop — so the LLM becomes a *selectively
> invoked decoder* inside a loop we own, instead of the brain of every request.

> **Naming discipline (review 2026-07-16):** Phases A/B are **JEPA-inspired**,
> not JEPA. An Elo estimator + a policy + a decoder is exactly that and nothing
> more. JEPA means *learned predictive latent representations*; we only earn the
> name in Phase C, when an encoder is actually trained to predict future latent
> states. Say "JEPA-inspired architecture" for A/B and "Student-JEPA" only for
> §3.4. This distinction matters academically and in any investor conversation.

> **👉 Starting implementation? Skip to [§7](#7-start-here--phase-a0-the-first-pr).**

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
2. **The verification engine** ([[Verification-Engine]], §3.3b) — hard engineering;
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
  at ~50/chapter, depth 3).
  *Precise read of their advantage (review 2026-07-16), because expectations
  should stay realistic:* it is almost certainly **not the adaptive loop
  itself* — mastery tracking, fine-grained KCs, and adaptive sequencing are all
  well-published. Their durable advantage is the **combination** of (1) years
  of interaction logs, (2) extensive content aligned to their knowledge graph,
  (3) accumulated engineering refinements, and (4) deployment at scale.
  **Reproducing the architecture is feasible; reproducing the behavior
  requires data accumulated over a long period.** So: borrowing the design puts
  us at their *2014 starting line*, not their 2026 position — the clock on our
  data asset starts the day Phase A ships, which is the whole argument for §7.
  Their China-lock buys time, not a finish line. Note also that (2) — content
  aligned to the graph — is the line item we most underestimate; see §6 risks.
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

Two structural corrections from the 2026-07-16 review are now explicit:
the **verifier writes back to the event log** (that edge *is* the flywheel —
it was implied before, which is how load-bearing edges get lost), and the
**knowledge base is shared infrastructure**, not a leaf under the
orchestrator — nearly every component reads it.

```
                    ┌─────────────────────────┐
                    │     student session     │
                    └──┬───────────────────▲──┘
      attempts, hints, │                   │ next item / explanation
             time      ▼                   │
   ┌───────────────────────────┐   ┌───────┴──────────────┐
   │ EVENT LOG (event-sourced) │◄──┤ VERIFICATION ENGINE  │  ← P5, §3.6
   │ attempts · traces         │   │ sympy·units·sandbox… │
   │ verdicts · error classes  │   └───────▲──────────────┘
   └───────────┬───────────────┘           │ (only when the LLM ran)
               ▼ features                  │
   ┌───────────────────────────┐   ┌───────┴──────────────┐
   │ STATE ESTIMATOR           │   │ LLM DECODER          │  ← existing
   │ Elo now → Student-JEPA    │   │ pipeline.run()       │    pipeline
   └───────────┬───────────────┘   └───────▲──────────────┘
               ▼ mastery                   │ selective: explain / hint only
   ┌───────────────────────────┐  cheap    │
   │ POLICY / ORCHESTRATOR     ├───────────┘
   │ /v1/next · /v1/attempts   │  path: serve item (SQL, no LLM)
   └───────────────────────────┘

   ┌────────────────────────────────────────────────────────┐
   │ KNOWLEDGE BASE (shared infrastructure)                 │
   │ KC graph · items+gold · chunks/pgvector · misconceptions│
   └────────────────────────────────────────────────────────┘
        ▲ read by: policy (frontier/prereqs) · verification engine (gold
          answers) · decoder (RAG chunks, KC-filtered) · state estimator
          (KC identity/embeddings) · evals (P3 golden set)
```

**The flywheel cycle, stated once:** student → LLM → verification engine →
event log → state estimator → policy → student. Every turn of it appends
labeled data nobody else has. This is the loop that compounds over years;
everything else in this doc is scaffolding for it.

**Event sourcing is the discipline** (review, and correct): the event log is
not "training data we might use later" — it is the canonical history from
which mastery, misconceptions, hint usage, latency, forgetting curves,
engagement, and curriculum traversal are all *derived*. Raw events → features
→ state → policy → evals → training, and nothing upstream is ever mutated.
Practical rules: `attempts` and `traces` are append-only (no UPDATE, no
DELETE outside the 18-month retention job); `student_kc_state` is a
**derived cache**, never a source of truth — it must be reconstructible by
replaying the log. If we ever can't rebuild state from events, the estimator
swap in Phase C becomes a migration instead of a re-run.

**Selective-decoding rule (the VL-JEPA transplant):** the LLM is invoked only
when (a) the student explicitly asks (`/v1/ask`, unchanged), (b) a wrong
attempt + "explain" tap — RAG pre-filtered to the item's chapter, or (c) a
hint request that pre-authored hints can't cover. Everything else — item
selection, mastery updates, review scheduling — is SQL. Concretely: *solved
correctly → update mastery → choose next item → done*, with no LLM call; and
*concept forgotten → decay mastery → schedule review → done*, likewise.

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

-- Migration (A.4): mastery state — ONE ROW per (student, KC). DERIVED CACHE,
-- not a source of truth: every column here must be reconstructible by replaying
-- `attempts` (see §3.1 event sourcing). Safe to TRUNCATE and rebuild — that
-- property is what makes the Phase C estimator swap a re-run, not a migration.
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

### 3.3a Module contracts (freeze these first — they outlast the code)

Review point, adopted: implementations churn (Elo → SAKT → Student-JEPA;
one verifier → five), contracts don't. These land in **Phase A.0**, before any
estimator exists, as typing-only Protocols + Pydantic models. Everything
downstream codes against these, never against `EloEstimator` or `sympy`.

```python
# app/adaptive/contracts.py — no implementations, no DB, no I/O.

class KnowledgeState(BaseModel):          # the state representation
    user_id: UUID
    kc: dict[str, KCMastery]              # kc_id -> mastery
    computed_at: datetime
    estimator: str                        # "elo@v1" | "sjepa@v3" — provenance

class KCMastery(BaseModel):
    rating: float                         # estimator-native scale
    p_correct: float                      # 0..1 CALIBRATED — the portable unit
    confidence: float                     # 0..1; Elo: f(attempts). JEPA: variance
    attempts: int
    due_at: datetime | None

class StateEstimator(Protocol):           # Elo v1, Student-JEPA later
    name: str
    # `prior` is passed IN, not looked up: Elo needs the current rating and a
    # pure function can't fetch it. None = cold start. (A.0 correction 2, §7.)
    def observe(self, ev: AttemptEvent,
                prior: KCMastery | None) -> StateDelta: ...   # pure; caller persists
    async def state(self, pool, user_id: UUID, kcs: list[str]) -> KnowledgeState: ...
    async def rebuild(self, pool, user_id: UUID) -> None: ...  # replay log → cache

class Policy(Protocol):                   # next-item selection
    async def next(self, req: NextRequest) -> NextDecision: ...
    # NextDecision: {item_id, reason: frontier|review|probe|remediate,
    #                p_correct_expected: float, alternatives: [item_id],
    #                policy: "greedy@v1"}   ← reason+policy go in the log, always

class Verifier(Protocol):                 # ONE checker, not the whole engine
    name: str; domain: str                # "math.symbolic" | "physics.units" | …
    def applies_to(self, claim: Claim) -> bool: ...
    def check(self, claim: Claim) -> Verdict: ...   # pure, timeout-bounded
    # Verdict as SHIPPED in verify/base.py (P1 field names kept — A.0
    # correction 1, §7): {outcome: PASS|FAIL|INAPPLICABLE|TIMEOUT,
    #                     reason, confidence, checker: "sympy@1.13"}
```

Four rules that make these contracts load-bearing rather than decorative:

1. **`p_correct` is the portable unit.** Elo ratings, JEPA latents, and IRT
   thetas are not comparable across estimators; a calibrated probability is.
   Policy consumes `p_correct` only — so swapping the estimator can't silently
   change item selection semantics.
2. **`observe()` is pure**; the route persists. Keeps the estimator testable
   and lets the same function run online *and* in the Phase C replay/backfill.
3. **Decisions are logged with their reason and policy version.** Without
   `reason` + `policy` in the log, no future off-policy evaluation is possible
   — you can't A/B a policy against history that doesn't say why it acted.
4. **`INAPPLICABLE` ≠ `FAIL`** everywhere (already the P5 rule, edge #4 of
   [[Opus-Execution-Plan]] §2) — a Verdict enum, never a bool.

### 3.3b Verification: an engine of many verifiers, not one checker

Review point, adopted. "Mechanical verifier" (singular) is the wrong mental
model — the backend diversifies by domain, and the shipping name is already
[[Verification-Engine]]. The `Verifier` Protocol above is one *checker*; the
engine dispatches over a registry:

| Domain | Checker | Phase |
|---|---|---|
| Math (symbolic) | SymPy equivalence, step-transition via random numeric eval | P5.3 (planned) |
| Physics | `pint` dimensional homogeneity + unit-normalized final answer | P5.3 (planned) |
| Curated bank | gold-answer compare against `items.answer_gold` | **A.0 — ships first** |
| Chemistry | equation balancing, stoichiometry conservation | later |
| Programming | sandboxed execution + unit tests | later (if we add CS) |
| Logic / proofs | SAT/SMT (Z3) | research |

Engine contract: run all `applies_to` checkers, each timeout-bounded in a
process pool (SymPy can hang — P5.0), aggregate to a single gate outcome by this
precedence (**shipped in A.0**, `verify/registry.py`, pinned by a truth-table
test):

> **FAIL > TIMEOUT > PASS > INAPPLICABLE**
>
> - any **FAIL** ⇒ FAIL — one proof of wrongness outranks any number of passes.
> - else any **TIMEOUT** ⇒ TIMEOUT — something checkable went unchecked, so we
>   do not know. Ranking TIMEOUT *above* PASS is what stops "3 passed, 1 timed
>   out" from badging as verified. Abstain, don't badge.
> - else any **PASS** ⇒ PASS.
> - else **INAPPLICABLE** — including the no-checker-applied case. Never a PASS
>   (edge #4): an unchecked claim and a verified claim must never be
>   indistinguishable downstream.
>
> A checker that *raises* degrades to INAPPLICABLE and is logged loudly — never
> to FAIL. A bug in our code must not surface to a student as "you are wrong".

Verdicts fan out to three places: the SSE `verify` event, `traces.verify`
(ask path), and `attempts.verify` + `error_class` (practice path — the edge
§3.1 now draws). Keep `verify/` import-clean of tutor code so the
verifier-API pivot ([[Opus-Execution-Plan]] §Parallel track) stays available.

### 3.4 Student-JEPA (Phase C spec, kept honest)

**This is the only place the JEPA name is earned** — an encoder trained to
predict future latent states, not an Elo number with a fashionable label.

- **Input:** per-student event sequence `(kc embedding, correct, time bucket,
  hints)`; **context encoder:** 2–4 layer transformer (~1–10M params);
  **objective:** I-JEPA-style — predict the *embedding* of a masked/future
  window of events produced by an EMA target encoder; loss in latent space.
- **🔴 The actual research problem is the latent target, not the architecture**
  (review, and correct). "Predict the future knowledge embedding" is only
  meaningful if the target encoder's embedding space is itself meaningful —
  otherwise the loss is minimized by representation collapse and we've learned
  a constant. The transformer is a weekend; this is the paper. Concretely:
  - **Collapse is the default failure**, not an edge case. I-JEPA avoids it
    with asymmetric context/target + EMA target encoder + masking; we must
    replicate all three and *measure* it (embedding variance / rank per batch,
    not just loss going down — a collapsed model has a beautiful loss curve).
  - **Grounding candidates for the target space** (pick and test, don't assume):
    (a) target encoder over the *outcome window* (next-k attempt outcomes),
    which grounds the latent in observable behavior; (b) KC-graph structure —
    embeddings of co-required KCs should be near; (c) verifier-derived error
    classes as auxiliary heads (a JEE-only signal — nobody else's KT data has
    step-level verdicts, so this is the differentiating axis).
  - **Falsifiable stop rule:** if a linear probe on the latents doesn't beat
    `EloEstimator` AUC out-of-sample, the representation isn't real — ship Elo,
    publish the negative result, don't ship the model.
- **Probe/eval:** linear head → next-attempt correctness AUC + calibration
  (ECE, not just AUC — the policy consumes `p_correct`), benchmarked against
  `EloEstimator` and AKT (via pyKT) on the same time-split. Ship only if it
  beats Elo out-of-sample — pre-registered, P3-style rule.
- **Serving:** nightly batch job writes per-KC mastery into
  `student_kc_state` via `rebuild()` — the online system never changes shape.
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
| **A.0 — contracts** | `adaptive/contracts.py` (§3.3a) + `verify/registry.py` + gold-answer checker; typing/tests only, no DB, no routes | ₹0 | ~1 day | **none — start now (§7)** | freezes the seams P5/Phase C plug into |
| **A — log + graph** | Migrations A.1–A.4; KC graph for ONE chapter (~50 KCs, Physics–Optics or Mechanics); attempts logged | ₹0 | 3–5 days | A.0 merged | parallel to P2/P3; golden-set problems get `kc_id` tags (curate once, use twice) |
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
| Squirrel AI | the log + graph-aligned content + scale refinements (the loop itself is public knowledge) | India access (China-locked); verification |
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

---

## 7. Start here — Phase A.0, the first PR

> **Status: this is the next physical step.** Everything above is settled
> enough to build against. A.0 is deliberately the smallest merge that creates
> the seams the whole lane plugs into: **contracts + one real verifier, no DB,
> no routes, no behavior change.** It cannot break `/v1/ask` because it does
> not touch it — same discipline as P1's "zero behavior change" refactor.

### A.0 scope (~1 day, ₹0, one PR) — ✅ **SHIPPED** (2026-07-16, PR #8)

**Shipped** (as built; two corrections to the original spec are marked 🔧 and
explained below):
```
backend/app/adaptive/__init__.py
backend/app/adaptive/contracts.py      # §3.3a: KnowledgeState, KCMastery,
                                       # AttemptEvent, StateDelta, NextRequest,
                                       # NextDecision + StateEstimator/Policy
backend/app/verify/base.py             # 🔧 WIDENED IN PLACE (not a new
                                       # contracts.py): +Outcome.TIMEOUT,
                                       # +Verdict.checker, +Claim, and
                                       # name/domain/applies_to on Verifier
backend/app/verify/registry.py         # dispatch: applies_to → check →
                                       # aggregate (FAIL > TIMEOUT > PASS >
                                       # INAPPLICABLE)
backend/app/verify/checkers/__init__.py
backend/app/verify/checkers/gold.py    # GoldAnswerChecker — the first real
                                       # verifier: compare a response to
                                       # answer_gold {value, unit, choices}
backend/tests/test_adaptive_contracts.py   # 38 tests
backend/tests/test_verify_registry.py      # 39 tests
```

> **Both corrections below, and the other load-bearing "why is this weird?"
> calls from A.0, are recorded as one-screen ADRs in
> [`docs/Decisions/`](../Decisions/README.md) — read those before changing any
> of it. Correction 1 = [[ADR-001]], correction 2 = [[ADR-002]], the unit
> limitation = [[ADR-009]].**

**🔧 Correction 1 — `verify/base.py`, not `verify/contracts.py`.** This spec was
written without noticing that **P1 already shipped `verify/base.py`** carrying
`Outcome`/`Verdict`/`Verifier` (its docstring calls the `confidence` decision
"locked here", and `test_model_plane.py` asserts on it). Creating a second
`Verdict` would have put two competing contract types in one package — the exact
failure §3.3a exists to prevent. Resolution (user call, 2026-07-16): **widen
`base.py` in place, additively**, keeping P1's field names (`outcome`/`reason`,
*not* the `status`/`detail` this doc originally sketched). The P1 test passes
untouched. Anywhere this doc says `verify/contracts.py`, read `verify/base.py`.

**🔧 Correction 2 — `observe(ev, prior)`, not `observe(ev)`.** §3.3a's sketch
had `observe(self, ev: AttemptEvent) -> StateDelta` *and* required the method be
pure. Those are contradictory: an Elo update needs the current rating, and a
pure function cannot fetch it. Resolution: the caller — which already holds the
row it is about to update — passes `prior: KCMastery | None` in (`None` = cold
start). Purity rule preserved, which is what B.1's replay and Phase C's backfill
depend on. §3.3a above reflects the corrected signature.

**Also settled in A.0:** units in the gold checker are a **normalized string
compare**, not dimensional analysis, because A.0 adds no dependencies. `m/s^2`
== `M/S^2 `, but `N/kg` != `m/s^2` — a known false negative, pinned by a test
that is *meant* to fail (and be deleted) when `pint` lands at P5.0.

**Explicitly NOT in A.0** (each is its own PR): migrations, `EloEstimator`,
policy, routes, UI, sympy/pint deps.

**Why this order:** the review's point — contracts outlast implementations.
Elo will be replaced (Phase C), one checker becomes six (§3.3b), the routes
will be rewritten. `KnowledgeState`, `Verdict`, and the `p_correct` convention
will not. Freezing them costs a day now and saves a migration later. The
`GoldAnswerChecker` is included so the registry has a real implementation to
prove the dispatch against — a Protocol with no implementor is a guess.

### Acceptance (the "prove it", P3 style)

1. `pytest backend/tests/` — existing **38 tests stay green** (A.0 imports
   nothing from `routes/`, `orchestrator/`, or `models/`; a test asserts this
   import-cleanliness, which also protects the verifier-API pivot).
2. New tests cover: `Verdict` aggregation truth table (any FAIL ⇒ FAIL;
   all INAPPLICABLE ⇒ INAPPLICABLE, **never** PASS — the edge #4 rule as a
   test, not a comment); `GoldAnswerChecker` on numeric tolerance (rel 1e-3),
   unit mismatch ⇒ FAIL, unparseable ⇒ INAPPLICABLE, MCQ exact match.
3. `StateEstimator`/`Policy` Protocols have a `FakeEstimator`/`FakePolicy` in
   tests proving the contracts are implementable — and that `observe()` is pure
   (same input ⇒ same `StateDelta`, no I/O).
4. No new runtime dependency in `requirements.txt` (stdlib + pydantic only —
   sympy/pint arrive with P5.0).

### Then, in order

| PR | Contents | Gate |
|---|---|---|
| **A.0** | contracts + registry + gold checker (above) | none — start now |
| **A.1** | migrations A.1–A.4 in `schema.sql` + a `docs/Build/` KC-tagging guide; RLS mirroring `sessions` | A.0 merged |
| **A.2** | KC graph seed for ONE chapter (~50 KCs + prereq edges) as a reviewable YAML/CSV → ingest CLI (`app/ingest/` already exists) | A.1 |
| **A.3** | item-bank ingest: `items` rows w/ `answer_gold`; **tag the P3 golden problems with `kc_id`** (curate once, use twice) | A.2 + item sourcing owner assigned |
| **B.1** | `EloEstimator` implementing `StateEstimator`; `rebuild()` replay from `attempts`; unit tests vs a hand-computed Elo trace | A.1 |
| **B.2** | `policy.py` + `routes/practice.py` (`GET /v1/next`, `POST /v1/attempts`); logs `reason` + `policy` version | B.1 + A.3 |
| **B.3** | UI practice screen + the still-missing feedback UI (UI lane) | B.2 |

**The one human blocker, unchanged:** A.3 needs an owner for sourcing ~150
items for the first chapter (NCERT exemplar + past JEE papers, same sourcing
and attribution rules as the P3 golden set). That is curation hours, not code
— it is the (2) in Squirrel's advantage list (§1.3), and the thing this plan
most underestimates if left unassigned. **A.0–A.2 and B.1 do not block on it**,
so start now and assign in parallel.

**Suggested first chapter:** whichever chapter the P3 golden set seeds from
(Physics–Optics is already queued for ingest per [[Status]]) — the golden
problems become the first items for free.

## Connections
- Decisions → [`docs/Decisions/`](../Decisions/README.md) (ADR-001…010 — the
  "why is this weird?" records; write one when a future reader would ask)
- Extends → [[Student-Model]] (resolves its v1-mastery decision: Elo, [[ADR-007]]) ·
  Plugs into → [[Opus-Execution-Plan]] (P1 seams, P3 golden set, P5 verifier)
- Economics guard → [[Viability-Brutal-Honesty]] §3.1 · Moat logic →
  [[Durable-Moat]] · Verifier spec → [[Verification-Engine]]
- Status board → [[Status]] · Hub → [[Startup-MOC]]
