---
tags: [type/note, domain/startup, startup/architecture, decision/anchor]
updated: 2026-07-11
status: PROPOSED — becomes LOCKED once ratified
---
# 🔩 Target Architecture (the locked blueprint)

> This is the single reference for **how the whole system is wired** — high level
> and low level. It unifies [[Cognitive-Architecture]] (the 5 layers),
> [[Retrieval-Knowledge-Layer]] (multi-retrieval), [[Verification-Engine]] (the
> gate), [[Student-Model]] (memory), and [[Durable-Moat]] (replaceability) into
> one blueprint, and maps it onto the actual repo (`backend/app/`). Concept docs
> say *why*; this doc says *what talks to what, through which interface*.
>
> **Design bet, stated once:** the model is a rented commodity; we own the
> orchestration, the knowledge base, the verifier, and the trace data. Every
> vendor-facing thing sits behind an interface we control, so model churn is a
> config change + eval run — never a rewrite.

## 1. High level — six planes

```
┌─────────────────────────────────────────────────────────────────┐
│ INTERFACE      Expo clients ── SSE event protocol (versioned)   │
├─────────────────────────────────────────────────────────────────┤
│ ORCHESTRATOR   fixed pipeline (v1), stages behind Protocols:    │
│    Understand → Retrieve(multi) → Reason → Verify → Teach → Log │
├───────────────────────────┬─────────────────────────────────────┤
│ KNOWLEDGE                 │ MODEL                               │
│  curated chunks(pgvector) │  adapter registry (DeepSeek,        │
│  keyword FTS · formula DB │  Gemini, …) + Router                │
│  examples · [KG deferred] │  (policy-as-data)                   │
├───────────────────────────┴─────────────────────────────────────┤
│ VERIFICATION   deterministic checkers + the gate                │
│                (show / repair / abstain)   ← the moat           │
├─────────────────────────────────────────────────────────────────┤
│ MEMORY & FEEDBACK   trace log (full pipeline record) ·          │
│  student model · explicit+implicit feedback · eval harness      │
└─────────────────────────────────────────────────────────────────┘
```

Planes only touch each other through the interfaces in §3. The orchestrator is
the only component that knows the pipeline order; no stage knows what runs
before or after it.

## 2. The orchestrator — fixed pipeline, not an agent framework

**Locked decision:** v1 orchestration is a *fixed, explicit pipeline in plain
Python* — no LangChain/LlamaIndex/agent framework, no dynamic planning. This
resolves [[Cognitive-Architecture]]'s open question "how agentic in v1?" the
way [[A serious question]] Reason 4 warned: over-orchestration adds latency and
bugs before it adds intelligence. Agentic behavior (re-retrieval, tool loops)
arrives later as *bounded loops inside a stage*, never as a free-running agent.

```
AskTask ─▶ Understand   classify: subject · type(math/theory/numerical) ·
        │               difficulty · needs_vision   (cheap model or heuristic)
        ├▶ Retrieve     fan-out to retrievers picked by the classification,
        │               merge with reciprocal-rank fusion (§4)
        ├▶ Reason       Router picks model+prompt; adapter streams
        ├▶ Verify       gate: pass ▸ show | step fails ▸ repair (≤N) |
        │               else ▸ abstain honestly     (§6; v1 = post-stream)
        ├▶ Teach        format for client (LaTeX, citations, Fast/Guided mode)
        └▶ Log          write the FULL trace (§7) — never optional
```

Each stage is a small class implementing one Protocol. Stages are pure with
respect to the pipeline: input → output + trace events. That is what makes
every one of them swappable, testable, and — later — distillable.

## 3. Low level — the stable contracts (this is what "locked" means)

These interfaces are the constitution. Implementations churn freely;
signatures change only with a deliberate migration.

```python
class Retriever(Protocol):                          # N implementations
    async def retrieve(self, q: Query) -> list[Chunk]: ...
    # VectorRetriever · KeywordRetriever · FormulaRetriever
    # HistoryRetriever(student) · [GraphRetriever — deferred]

class Reasoner(Protocol):                           # one per vendor/model
    def stream(self, task: ReasonTask) -> AsyncIterator[Event]: ...
    # yields TokenEvent | StepEvent | UsageEvent — vendor quirks die here

class Router(Protocol):                             # policy-as-DATA
    def pick(self, features: TaskFeatures) -> ModelChoice: ...
    # routing table lives in config/DB (subject × difficulty × modality
    # → model, temperature, max_retries). Changing routing = editing a
    # row, running the eval (§8), done. Never an if-ladder in code.

class Verifier(Protocol):                           # one per check type
    def check(self, step: Step, ctx: ProblemCtx) -> Verdict: ...
    # Verdict = PASS | FAIL(reason) | INAPPLICABLE — the gate composes
    # verdicts; checkers never talk to models or the DB.

class Tool(Protocol):                               # borrow-a-feature slot
    async def run(self, args: dict) -> ToolResult: ...
    # sympy_eval · unit_check · plot · OCR — competitor features we want
    # (graphing, formula lookup, notebook import) enter HERE as tools or
    # retrievers, not as pipeline rewrites.

class StudentModel(Protocol):
    async def state(self, user_id) -> KnowledgeState: ...
    async def observe(self, evt: LearningEvent) -> None: ...
```

**SSE event protocol** (interface plane's contract, versioned so clients and
backend evolve independently):
`token · step · verify(step_id, verdict) · meta(sources, model, cost) ·
done · error`. v1 emits `token/meta/done/error` (what ships today); `step` and
`verify` are additive — old clients ignore them.

## 4. Knowledge plane — multi-retrieval, staged honestly

Locked shape (from [[Retrieval-Knowledge-Layer]]): retrieval is **several
engines merged**, but engines are added only when the eval shows failures
their absence explains.

- **v1 (now):** VectorRetriever (pgvector, exists) + KeywordRetriever
  (Postgres FTS — free, catches exact formula/term queries vectors fuzz) +
  HistoryRetriever (this thread's prior exchanges). Merge = reciprocal-rank
  fusion, then similarity floor.
- **v2:** FormulaRetriever (curated formula table with conditions-of-validity)
  + Student-history retrieval (past misconceptions from [[Student-Model]]).
- **Deferred (locked):** knowledge graph / Neo4j. Both open questions in
  [[Cognitive-Architecture]] and [[Retrieval-Knowledge-Layer]] lean defer;
  this doc locks it: **no KG until the eval set shows multi-hop failures the
  merged retrievers can't fix.** Revisit trigger, not a date.
- Ingestion (`app/ingest/`) is the quality choke point: every chunk carries
  `source_ref`, chapter, type (theory/example/formula/misconception), and
  license class. Content quality > model ([[Retrieval-Knowledge-Layer]]).

## 5. Model plane — rented, routed, replaceable

- One adapter file per vendor implementing `Reasoner`/`Embedder`/`Vision`.
  Today: DeepSeek (text), Gemini (vision + failover) — already isolated in
  `core/llm.py`; the refactor splits it into `models/deepseek.py`,
  `models/gemini.py`, `models/router.py`.
- The Router replaces the current hardcoded three-way if. Policy lives in a
  table, chosen on `TaskFeatures` from Understand. Cost/latency/quality per
  route are measured from the trace log, so routing decisions are evidence,
  not vibes.
- **Model-swap playbook (the churn defense):** new model ships → add adapter
  (~1 file) → run eval harness (§8) → if it beats the incumbent on *our*
  metrics (verified-precision, cost/solved, p95 latency), flip the routing
  row. If a frontier model absorbs a capability we built (better OCR, native
  step-structure), we *delete an adapter or a tool* — the pipeline doesn't
  notice. Small/local models (7–8B → 3B) enter the same way: another
  `Reasoner` adapter, promoted route-by-route as it wins evals. RLVR
  fine-tuning ([[Durable-Moat]]) just makes that adapter's model ours.

## 6. Verification plane — the gate (unchanged from spec, placed precisely)

The [[Verification-Engine]] design is adopted as-is (structured steps,
checker table, `generate → verify → show/repair/abstain`, step-precision ≥99%
before coverage). What this doc adds is *where it sits*:

- **v1 placement — post-stream, async:** tokens stream to the student
  unchanged; a parser extracts steps; checkers run; `verify` events badge
  each step seconds later ("✓ verified" / correction). Zero latency cost,
  verification becomes a visible product feature immediately.
- **v2 placement — step-gated streaming:** the model emits delimited steps;
  the gate holds each step (checks are milliseconds), releases it verified,
  re-prompts on failure. The student only ever sees verified math.
- Scope stays staged per [[Verification-Engine]]: curated bank first.
- Checkers are pure functions (`Verifier` Protocol) — they never call models.
  The repair loop is the *orchestrator's* bounded loop, not the checker's.

## 7. Memory & feedback plane — the trace is the flywheel

**Locked rule: every ask writes a full trace, from day one.** The trace is
simultaneously (a) debugging, (b) the eval seed-set, (c) the routing evidence,
(d) the RLVR/distillation dataset, (e) the [[Student-Model]] event stream.
It cannot be reconstructed later; it is the data moat accumulating.

Trace record (one per ask):
```
question · image_ref · classification · retrievers_used ·
chunks[{id, source_ref, score, rank}] · prompt_hash · model · raw_output ·
steps[{expr, verdict, checker}] · gate_outcome(show/repair/abstain) ·
repairs · tokens/cost/latency per stage · feedback{explicit: 👍👎+reason,
implicit: follow_up_asked, copied, session_abandoned}
```
Today's `sessions` table stores the accounting subset (Q/A/model/cost); the
trace extends it — additive migration, no breaking change. Explicit feedback
is one new endpoint + one column; implicit signals are derived from events
already happening.

## 8. The eval harness — the immune system for change

Adaptation to model churn and competitor features is a *process*, and the
eval harness is its gatekeeper:

- **Golden set:** versioned exam problems (start ~100–200 curated: JEE/NEET
  past papers where we hold ground truth) + real traces promoted from
  production failures.
- **Metrics (in priority order):** step/answer verified-precision →
  abstention honesty (abstained when actually wrong) → cost per solved
  question → p95 first-token latency → retrieval hit-rate.
- **The rule:** *nothing* — new model, new retriever, new prompt, new stage —
  ships into routing unless the harness shows it improves these metrics.
  This is [[Durable-Moat]]'s "rigorous eval decides swaps" made operational,
  and it's also the anti-shiny-object guardrail: features borrowed from
  competitors enter as a `Tool`/`Retriever` + an eval question ("does this
  move a metric?"), not as strategy changes.

## 9. Repo mapping (target module layout — refactor, not rewrite)

```
backend/app/
  routes/ask.py          → thin: parse request, quota, call orchestrator
  orchestrator/pipeline.py   stages, gate loop, SSE emission
  retrieval/{base,vector,keyword,history,merge}.py
  models/{base,router,deepseek,gemini}.py     (split of core/llm.py)
  verify/{base,parser,answer,dimensional,gate}.py
  teach/prompts.py       (core/prompts.py moves; cache-prefix rule stays)
  memory/{trace,student}.py
  tools/{base,sympy_eval}.py
  ingest/                (stays; gains chunk-type + license tagging)
```
Current code maps cleanly: `core/rag.py` becomes the first `Retriever`;
`core/llm.py` splits into two adapters + router; `ask.py`'s inline generator
becomes the pipeline. Nothing is thrown away.

## 10. Build order (each step is shippable alone)

1. **Trace + feedback** (§7) — schema migration, thumbs endpoint, wire
   history into prompts. Starts the flywheel; smallest work, biggest regret
   if skipped.
2. **Pipeline refactor** (§2, §9) — same behavior, new seams. Pure refactor.
3. **KeywordRetriever + RRF merge** (§4) — first multi-retrieval win.
4. **Eval harness v0** (§8) — 100 golden problems + a script. Prereq for
   everything after.
5. **Router policy-as-data** (§5) — unlocks cheap-model routing for easy
   questions (the cost arbitrage).
6. **Verifier v1** (§6) — post-stream badges on curated-bank math.
7. Then, evidence-driven: step-gating, formula retriever, student model v0,
   RLVR exploration.

## Decisions this doc locks (superseding "open" markers elsewhere)
- Orchestration v1 = **fixed pipeline, no agent framework** (was open in
  [[Cognitive-Architecture]]).
- Knowledge graph = **deferred behind an eval trigger** (was open in
  [[Cognitive-Architecture]] + [[Retrieval-Knowledge-Layer]]).
- Verifier v1 = **post-stream async badging**, step-gating v2 (placement was
  unspecified).
- **Full trace logging from day one** is non-negotiable infrastructure.
- Model swaps/feature borrowing go through the **eval harness**, always.

## Connections
- Concretizes → [[Cognitive-Architecture]], [[Durable-Moat]],
  [[Verified-Reasoning-Engine]]
- Adopts → [[Verification-Engine]] (gate), [[Retrieval-Knowledge-Layer]]
  (multi-retrieval), [[Student-Model]] (memory plane)
- Maps onto → [[AITutor-MVP-Architecture]] (current code) ·
  Hub → [[Startup-MOC]]
