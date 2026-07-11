---
tags: [type/plan, domain/startup, startup/execution, decision/anchor]
updated: 2026-07-11
status: ACTIVE — the working implementation plan
executor: written for Claude Opus (or any engineer) to execute cold, phase by phase
---
# 🗺️ Execution Plan — from deployed MVP to verified tutor

> **How to use this doc (read first):** this is the self-contained implementation
> plan. Each phase says *what to build, why (with the real-world company lesson
> behind it), the exact files/schema, the edge cases that will bite, and how to
> prove it works before moving on*. Execute phases **in order** — each is
> shippable alone, and each later phase assumes the earlier ones. Do not skip
> ahead to the verifier; the boring phases (traces, seams, evals) are what make
> the verifier land. Architecture reference → [[Target-Architecture]] ·
> Business rationale → [[Viability-Brutal-Honesty]] · Verifier spec →
> [[Verification-Engine]] + [[A1-Math-Verified-Tutor-Dev-Plan]].

## 0. Context snapshot (what is true today, 2026-07-11)

- **Deployed MVP:** Expo web frontend (Cloudflare), FastAPI backend (container
  host), Supabase (auth + Postgres/pgvector + storage). Stripe billing stubbed in.
- **Backend today** (`backend/app/`): stateless single-pass RAG —
  auth → quota → pgvector retrieve (top-8, keep 4 ≥0.75 sim) → prompt →
  DeepSeek stream (Gemini for vision/failover) → SSE → save Q&A+cost to
  `sessions`. No history, no verifier, no feedback capture, accounting-only logs.
- **Business state:** pre-revenue, pre-validation. The 90-day institute
  design-partner test ([[Viability-Brutal-Honesty]] §1.4) is THE open bet;
  everything in this plan survives both its outcomes (tutor business OR
  verifier-API pivot), which is why these phases are safe to build now.
- **Economics to protect** ([[Viability-Brutal-Honesty]] §3.1): verified
  cheap-model serving ≈ ₹12/seat/mo COGS vs ≈ ₹54 on frontier models. Every
  phase below either builds toward that margin or protects it.

## 1. The real-world lessons this plan is built on

Written plainly so no step feels arbitrary. Each lesson maps to a phase.

| Company | What actually happened | What we do about it | Phase |
|---|---|---|---|
| **GitHub Copilot (early)** | Flat $10/mo subscription, unlimited compute → lost ~$80/user/mo on heavy users | Never ship an uncapped paid plan. Pro gets a generous fair-use cap | P0.1 |
| **Cursor / Anysphere** | $4B revenue, still lost money on individual subs; fixed margins by routing to cheaper models + building its own (Composer) | Cheap-model routing is the plan from day 1; the verifier is what makes cheap models safe | P4, P5 |
| **Replit** | Disclosed *negative* gross margins — didn't see per-user costs until too late | Log cost per solve per user per route from day 1; margin dashboard is a query, not a project | P0.2 |
| **Harvey (legal AI)** | Scrapped its own fine-tuned model when frontier beat it; survives on workflows + partner data | Never bet the moat on "our model is smarter." RLVR later is a *cost* play; the durable assets are the verifier, traces, and institute workflow | all |
| **Khanmigo** | Pedagogically careful, forced Socratic → "a non-event," ~15% usage | Fast answers by default, guided mode is a choice; measure D7 retention like a KPI, not a vibe | P0.3, P3 |
| **Photomath** | 220M downloads on *speed* (photo → answer), imperfect accuracy | p50 ≤ 8s is a hard budget; verification must never block the stream | P5 |
| **Doubtnut** | 30M users, sold for $10M — usage without a payer | Institutes (B2B) are the payer; B2C free tier is a funnel with a strict cost cap | P0.1 |
| **Byju's** | Burned itself on customer-acquisition cost | No paid acquisition. Distribution = institutes + WhatsApp rails | GTM track |
| **Speak** | Consumer AI edtech works — at $20/mo in Korea/Japan | Confirms ₹299 B2C can't carry the company; don't over-invest in B2C polish | scope |

## 2. System-wide edge cases (apply to every phase — the "will bite" list)

1. **Client disconnects mid-stream.** The SSE generator in `routes/ask.py` gets
   cancelled → the post-stream `sessions` insert never runs → **quota was
   consumed but no record/history exists**. Fix in P0.2: move persistence into a
   `finally:` (write partial answer + `disconnected` flag). Never refund quota on
   disconnect (abuse vector: ask, grab tokens, disconnect).
2. **LLM dies mid-stream after first token.** Failover only triggers before the
   first token (by design — can't restart a half-shown answer). Policy: emit the
   `error` SSE event AND **refund the quota claim** (decrement `questions_today`)
   — the student got nothing; charging them poisons trust. Applies only when
   zero answer tokens were persisted.
3. **Prompt injection via ingested content.** RAG chunks go into the prompt.
   System prompt already fences CONTEXT as data; also: ingestion must strip
   instruction-looking text, and traces make audits possible. Never put
   user-supplied documents into the shared bank without review.
4. **LaTeX breaks everything downstream.** Model output LaTeX can be malformed
   (client render fails) and is hard to parse (verifier). Prompt already forces
   `$...$`/`$$...$$`; the P5 parser must treat unparseable math as
   `INAPPLICABLE` (no verdict), **never** as `FAIL` — a false "wrong" shown to a
   student is as bad as a false "verified."
5. **Photo questions are the expensive path** (~₹1/solve Gemini vs ~₹0.08 text)
   and India is photo-first. P4 adds OCR→text downgrade; until then, watch the
   vision share in the cost dashboard. Also: image fetch can fail/timeout, can
   be huge (cap at ~4MB, downscale), can be a non-image (check content-type,
   reject politely).
6. **Hinglish and vernacular input.** Students type "kya ye formula sahi hai".
   Embeddings handle it roughly; Postgres FTS (P2) does NOT (English stemmer).
   RRF merge must tolerate one retriever returning garbage. Don't block on
   vernacular; note it, revisit with Sarvam/AI4Bharat when voice lands.
7. **Exam-season traffic spikes** (Jan/Apr JEE, May NEET): 10× load bursts.
   Managed Postgres + one container scale fine at MVP numbers; the risk is
   **LLM provider rate limits** — implement 429-aware retry with jitter in the
   adapters, and the router (P4) must treat "rate-limited" as a failover reason.
8. **DPDP Act (minors' data).** Traces (P0.2) store questions + behavior of
   users likely under 18. Minimize: no name/phone in traces, region = India,
   retention policy documented, parental consent flows through institute
   onboarding (see [[Viability-Brutal-Honesty]] G9). Never log raw images —
   store the storage ref only.
9. **Question repeats are the margin** (cache), but exact-match caching fails on
   trivial rephrasings. Don't build semantic cache cleverness early — it's a
   correctness risk (wrong cached answer to a subtly different question). Defer
   to post-P5; the verifier makes cached-answer reuse auditable.
10. **Free-tier abuse:** multiple accounts to reset daily quota. Accept at MVP
    (Supabase auth friction is enough); revisit if cost dashboard shows it.

---

## Phase 0 — Margin guardrails + the data flywheel (≈1 week)

**Why first:** every later phase is measured through the data this phase starts
collecting, and the two margin holes (Copilot trap, Replit blindness) are live
in production *today*. Nothing here changes user-visible behavior.

### P0.1 Pro fair-use cap (the Copilot fix)
- `config.py`: add `pro_monthly_limit` (default **1500**/mo — no honest student
  hits 50/day; a scraper does).
- `routes/ask.py` quota SQL: replace the `plan = 'pro'` bypass with a monthly
  counter (`questions_month`, `questions_month_reset_on` on `profiles`,
  additive migration). Same atomic lazy-reset pattern as the daily one.
- Error copy for 402 on Pro: "fair-use limit" wording, support contact — never
  "quota exceeded" to a paying user.
- **Edge:** month boundary = calendar month (IST, not UTC — students live in
  IST; use `(now() at time zone 'Asia/Kolkata')::date`).
- **Prove it:** unit test the SQL both plans × both boundaries; existing tests
  in `backend/tests/` stay green.

### P0.2 Trace logging (the Replit fix + the flywheel)
- Additive migration: `traces` table keyed to `sessions.id`:
  `classification jsonb · retrievers_used text[] · chunks jsonb
  [{id, source_ref, score, rank}] · prompt_hash text · gate_outcome text ·
  verify jsonb · stage_latency_ms jsonb · disconnected bool` (cost/tokens stay
  on `sessions`). Index on `created_at`.
- `routes/ask.py`: persistence moves into `try/finally` around the stream
  (fixes edge #1); write the trace row in the same transaction as the session
  row.
- Refund path for edge #2 (mid-stream failure with zero tokens persisted).
- **Edge:** trace writes must never fail the user request — wrap in
  try/except-log. Traces are the *only* table allowed to grow unbounded; add
  the retention note now (raw traces 18mo, aggregates forever).
- **Prove it:** ask 3 questions (text, photo, one forced-failure), verify 3
  session rows + 3 trace rows with sane contents; kill the client mid-stream
  and verify the partial trace lands with `disconnected=true`.

### P0.3 Feedback + history (the Khanmigo-measurement fix)
- `POST /v1/sessions/{id}/feedback` `{rating: up|down, reason?: text}` →
  columns on `sessions`. Auth: session must belong to caller. Idempotent
  (upsert). One tap in the frontend thread screen.
- **History wiring:** add `thread_id uuid` to `sessions`; `AskRequest` gains
  optional `thread_id`; when present, load that thread's last 4 Q/A pairs
  (owned by caller!) and pass as `history` to `build_messages` — the parameter
  already exists and is called with `[]` today.
- **Edges:** history token budget — truncate each prior answer to ~1k chars
  (keep the boxed final answer line); history goes *after* the system prompt so
  the DeepSeek cache prefix stays byte-stable ([[Target-Architecture]] §5,
  `core/prompts.py` docstring); cross-user thread access must 404, not 403
  (don't leak existence).
- **Prove it:** follow-up question referencing "that answer" is answered in
  context; feedback lands; another user's thread_id 404s.

**Phase 0 exit:** margin protected, flywheel spinning, follow-ups work.

---

## Phase 1 — Pipeline seams (pure refactor, ≈1–2 weeks)

**Why:** every later phase plugs into these seams. This is
[[Target-Architecture]] §9 made real. **Zero behavior change** — that's the
acceptance test.

- Create the module layout: `orchestrator/pipeline.py`,
  `retrieval/{base,vector}.py`, `models/{base,router,deepseek,gemini}.py`,
  `verify/` (empty stub), `teach/prompts.py`, `memory/trace.py`.
- `core/rag.py` → `retrieval/vector.py` implementing the `Retriever` Protocol.
  `core/llm.py` → split into the two adapters + a hardcoded `Router` (same
  three-way logic, now behind the interface). `routes/ask.py` → thin (parse,
  quota, call pipeline, return StreamingResponse).
- Define the SSE event protocol constants in one module — `token · meta ·
  done · error` now; `step · verify` reserved (additive, old clients ignore).
- **Edges:** don't "improve" anything while moving it (scope discipline — a
  refactor with behavior changes can't be verified); keep `core/` re-exports
  one release so nothing external breaks; the failover subtlety in
  `stream_answer` (failover only before first token) must move intact — it
  encodes edge #2.
- **Prove it:** full test suite green; byte-identical SSE transcript for a
  fixed question against a recorded run (temperature makes tokens differ —
  compare event *structure*, plus one mocked-LLM test for exact equality).

---

## Phase 2 — Multi-retrieval (≈1 week)

**Why:** vectors miss exact-term queries ("state Raoult's law", formula names).
FTS is free and precise; the merge is where retrieval stops being one engine
([[Retrieval-Knowledge-Layer]]).

- Migration: `tsvector` generated column on `chunks` + GIN index.
- `retrieval/keyword.py` (`websearch_to_tsquery('english', $1)`), and
  `retrieval/merge.py` — Reciprocal Rank Fusion: `score = Σ 1/(60 + rank_i)`,
  then the existing similarity floor on the vector side only.
- Orchestrator fans out to both (they're both one Postgres round-trip; run
  concurrently with `asyncio.gather`), merges, keeps 4. Log `retrievers_used`
  + per-retriever ranks into the trace.
- **Edges:** LaTeX/symbols in the query break tsquery — sanitize to plain
  words, and empty tsquery must return `[]` not error; Hinglish returns junk
  from FTS (edge #6) — RRF naturally down-weights a retriever whose results the
  other doesn't corroborate, but verify this on a Hinglish sample manually;
  chapter filter applies to both retrievers.
- **Prove it:** 20-question A/B (10 conceptual, 10 formula-lookup): merged
  retrieval must beat vector-only on formula lookups and not regress
  conceptual. Save the 20 as the seed of the P3 golden set.

---

## Phase 3 — Eval harness (≈1–2 weeks) — **the gatekeeper**

**Why:** [[Durable-Moat]]'s model-churn defense and [[Target-Architecture]] §8.
After this phase, "should we swap/route/change X?" is a command, not a debate.
This is also the **Phase 0 accuracy gate** instrument from
[[Viability-Brutal-Honesty]] §5 kill-criterion 1.

- `backend/evals/`: `golden.jsonl` (id, question, chapter, gold answer as a
  sympy-parseable expression + numeric value + unit, difficulty, source),
  `run.py` (runs the *real* pipeline against a branch/config, writes a report),
  seeded with **100–200 problems**: NCERT exemplar + past JEE Mains (public
  papers; keep source attribution — see licensing note in
  [[Retrieval-Knowledge-Layer]]).
- Metrics per run: final-answer accuracy (sympy equivalence + numeric fallback
  with unit normalization via `pint`) · retrieval hit-rate (did any chunk
  contain the needed concept — hand-label once) · cost/question · p50/p95
  latency · (post-P5) step-precision & false-verified rate.
- **Edges:** answer grading is the hard part — accept equivalent forms
  (`1/√2` vs `√2/2`), tolerate sig-figs (relative tol 1e-3), units required for
  physics; **contamination** — frontier models have seen past JEE papers, so
  absolute scores flatter the model, but we're measuring *our pipeline deltas*
  (retrieval/routing/verifier), which contamination affects equally on both
  sides of an A/B; still, tag ~30 problems as "rephrased/renumbered" (change
  the numbers, recompute gold) for an uncontaminated subset.
- **Prove it:** two runs on identical config differ by <2% (sampling noise
  bounded); a deliberately broken config (retrieval off) shows a clear drop.
- **THE RULE from here on:** no model swap, prompt change, retriever addition,
  or route change merges without an eval run attached. This replaces "trust me."

---

## Phase 4 — Router policy-as-data (≈1 week)

**Why:** the Cursor lesson — routing is the margin lever. Today's three-way if
becomes a table you can edit and eval.

- `model_routes` table (or versioned YAML in-repo — pick YAML first: reviewable,
  no admin UI needed): match on `{has_image, subject?, difficulty?}` →
  `{model, temperature, max_retries, fallback}`. `models/router.py` reads it;
  hardcoded logic becomes the default rows.
- `Understand` stage v1 = **heuristics only** (has_image, chapter, text length,
  presence of `$…$`/numbers). No classifier model yet — a cheap-model classifier
  is itself a route to eval later.
- OCR-downgrade route (the photo-margin fix, edge #5): image → cheap vision
  extraction ("transcribe the problem exactly, LaTeX for math") → text pipeline
  via DeepSeek. Eval it against direct-Gemini on photo questions: if accuracy
  holds within the eval's noise band, flip the default — that's the blended
  cost dropping toward ₹0.2/solve, i.e. §3.1's ₹12/seat claim becoming real.
- **Edges:** a route must always resolve (final catch-all row → current
  behavior); rate-limit (429) is a failover *reason* distinct from error;
  route name goes into the trace so cost-per-route is a GROUP BY.
- **Prove it:** eval run per route change; cost dashboard query shows per-route
  cost/solve; OCR-downgrade A/B documented either way.

---

## Phase 5 — Verifier v1 (≈3–5 weeks) — **the moat, built honestly**

**Why last in this plan:** it needs the seams (P1), the golden set (P3), and
the traces (P0) to be provable. Spec: [[Verification-Engine]]; placement:
[[Target-Architecture]] §6 (post-stream async, never blocking — the Photomath
latency lesson). Scope: **curated-bank math/physics-numerical only** (v1).

- **P5.1 Structured steps:** prompt update forcing delimited steps
  (`<step n>…</step>` with a final `<answer>` block, LaTeX inside). Eval before
  proceeding — structure must not cost answer accuracy (it sometimes does;
  if >1–2% drop, iterate on the prompt, don't accept it).
- **P5.2 Parser** (`verify/parser.py`): extract steps; LaTeX → SymPy via
  `parse_latex` with a cleanup pass. **Unparseable = INAPPLICABLE** (edge #4).
  Expect only ~60–80% of steps to be checkable at first — that's fine and must
  be visible in metrics, not hidden.
- **P5.3 Checkers** (each a pure function, `Verifier` Protocol):
  1. Final-answer equivalence vs gold (curated bank) — symbolic, numeric
     fallback, `pint` units.
  2. Step-transition equivalence — random numeric evaluation at 5–7 sample
     points (Schwartz–Zippel logic; see [[Glossary]]): substitute random values
     for free symbols into step_i and step_{i+1}, compare. **Edges:** domain
     restrictions (√, log: sample within valid domain), branch cuts, trig
     periodicity (tolerance + multiple points), equations-vs-expressions
     (rearrangement is equivalence of solution sets, not of expressions —
     handle `Eq` separately), timeouts (SymPy can hang: hard 2s per check in a
     process pool).
  3. Dimensional homogeneity (`pint`) for physics.
- **P5.4 Gate + events:** run post-stream (already have the full answer in
  memory before `meta`); verdicts → trace + new SSE `verify` events + stored on
  the session so History shows badges. Repair loop (re-prompt on failed step,
  ≤2 attempts) only AFTER precision is proven — start with **detect and
  badge/abstain only**.
- **Badge copy (the false-positive nightmare, [[Viability-Brutal-Honesty]]
  §1.5):** a consistent-but-wrongly-modeled physics solution passes symbolic
  checks. Therefore the badge says **"computation verified"** — never "solution
  verified" — and the curated bank's final-answer check (gold answers) is the
  backstop that catches wrong models. Red-team set: 30 hand-written
  wrong-but-consistent solutions; **false-verified rate <1% on it or the badge
  does not ship** (kill-criterion 4).
- **Prove it:** eval report showing step-coverage %, step-precision ≥99% on
  checkable steps, false-verified <1% on red-team, p50 latency unchanged
  (async), badge visible in History. This report doubles as the **public
  accuracy report** (G1 in [[Viability-Brutal-Honesty]]) — the sales asset.

---

## Parallel track — business gates (not Opus's job, but Opus must respect them)

- **90-day institute kill-switch is running concurrently.** If it fails
  (zero pilots), P5 assets pivot to the verifier-API product — which is why
  `verify/` must stay import-clean of tutor-specific code (no profile/session
  imports inside checkers).
- **KPIs live from P0 data:** D7/D30 retention, cost/solve/route, margin per
  seat *net of 18% GST + payment fees* (~₹47–50 on a ₹60 seat), p50 latency,
  feedback ratio. One SQL view each; check weekly.
- **Kill criteria** (pre-registered, [[Viability-Brutal-Honesty]] §5): accuracy
  gate · 90-day GTM · D30 <10% · false-verified >1%. Moving these goalposts
  requires a written decision note, not a vibe.

## Resources
- **In-repo:** [[Target-Architecture]] (blueprint) · [[Verification-Engine]] +
  [[A1-Math-Verified-Tutor-Dev-Plan]] (verifier spec & schema) ·
  [[Viability-Brutal-Honesty]] (economics, §3.1 unicorn benchmark, kill
  criteria) · [[Retrieval-Knowledge-Layer]] · [[Student-Model]] (post-P5) ·
  `backend/README.md`, `backend/schema.sql` (current schema).
- **Tech:** SymPy `parse_latex` & `simplify` (docs.sympy.org) · pint
  (pint.readthedocs.io) · Postgres FTS `websearch_to_tsquery` + pgvector
  (supabase.com/docs/guides/ai) · RRF: Cormack et al. 2009 (the `1/(60+rank)`
  constant comes from this paper) · FSRS (github.com/open-spaced-repetition)
  for the later Student-Model phase.
- **Business evidence:** sources in [[Viability-Brutal-Honesty]] §Sources
  (Cursor/Harvey/Speak/margins — July 2026) — re-verify before quoting to
  investors; this market moves quarterly.

## Connections
- Executes → [[Target-Architecture]] · Gated by → [[Viability-Brutal-Honesty]]
  §5 · Supersedes → [[Backend-Implementation-Plan]] (Angular-era; its verifier
  scope folded into P5 here) · Hub → [[Startup-MOC]]
