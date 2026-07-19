---
tags: [type/note, domain/startup, startup/roadmap, status/active]
updated: 2026-07-19
---
# 🗺️ Roadmap — from deployed frontend to verified adaptive tutor

> Consolidated from a full-repo analysis (2026-07-19). Merges the three plan
> tracks into one dependency-ordered view: **[[Opus-Execution-Plan]]** (ask
> lane, P0–P5), **[[Adaptive-Loop-Architecture]]** §4 (practice lane, A–D),
> and the infra/GTM lanes tracked on [[Status]]. Kill criteria still live in
> [[Viability-Brutal-Honesty]] §5 — check every phase against them.

## Where we are (2026-07-19)

**Done, on `main` (194 backend tests):** P0 margin guardrails + trace
flywheel · P1 pipeline seams + SSRF fix · adaptive A.0 contracts, A.1
migration (written, **never executed**), A.2 Mechanics KC graph (57 KCs) ·
frontend redesign + real chat thread (threads, feedback UI, session lookup,
chat polish) **live at aksharaverse.com**.

**Open PRs:** [#11](https://github.com/aksharaverse/AITutor/pull/11) (A.3
content pipeline) → [#12](https://github.com/aksharaverse/AITutor/pull/12)
(A.3a content ops), both reviewed green, stacked.

**The honest gap:** the live site is a UI with no backend behind it. Nothing
has ever run end-to-end in production. The item bank is 8 items (5/57 KCs).
There is no CI. Everything below is ordered by what unblocks what.

## The critical path

```
gcloud auth (HUMAN) ──► Cloud Run deploy ──► wire EXPO_PUBLIC_API_URL
                                          ──► ingest Physics–Optics corpus
                                          ──► P0 prove-it (live e2e)   ◄── everything queues behind this
CI (pytest + postgres) ──► A.1 migration proven ──► supabase db push (after ledger repair)
item bank ≥150 (HUMAN curation) ──► B.1 Elo ──► B.2 routes ──► B.3 practice UI
golden set 100–200 (same curation pass) ──► P3 eval harness ──► P2/P4/P5 become provable
```

Two of the four root blockers are human, not code: **gcloud auth** and
**content curation hours**.

## Horizon 1 — Make it real (this week, ≈0 new code)

| # | Item | Owner/lane | Blocker |
|---|---|---|---|
| 1 | Merge PR #11, then rebase-merge #12 | backend acct (one click) | none |
| 2 | `gcloud` auth + run `backend/deploy/cloudrun.sh` (zero-spend variant: `us-central1`, `--max-instances 1`, `GEMINI_MODEL=gemini-2.5-flash`, ≤6 secrets, no DeepSeek key) | **human** | GCP auth |
| 3 | Set `EXPO_PUBLIC_API_URL` in Workers build config → redeploy | UI/infra acct | needs #2's URL |
| 4 | **CI** — `.github/workflows/`: pytest + postgres service container; fresh-DB migration apply = the schema-drift check ADR-011 wanted | either acct | none — biggest infra gap |
| 5 | Supabase ledger reconciliation (`supabase link` → `migration list` → `repair`), then `db push` A.1 | **human** (authenticated CLI) | blocks live adaptive tables |
| 6 | Ingest Physics–Optics notes (`PHY::optics::12`) → run the **P0 prove-it** live; UptimeRobot pinger on `/healthz` | infra lane | needs #2 |

**Exit:** a student can sign in on aksharaverse.com, ask a question, get a
streamed grounded answer, leave feedback — and CI guards every merge after.

## Horizon 2 — Content + closed loop (weeks 2–5)

The risk is operational now, not architectural ([[Status]] 2026-07-17):
throughput, quality, telemetry — in that order.

- **A.3b — first corpus, ~300 items** (57 KCs × ~5-6). **Still no owner.**
  Process exists ([[Content-Authoring]], linter, curation dashboard). Source:
  past JEE + NCERT exemplar. **Curate once, use twice:** tag the P3 golden-set
  problems with `kc_id` and they double as items. Breadth before depth
  (`LADDER_FLOOR=5` is machine-checked). Do **not** build 5,000 before D7 is
  measured.
- **P3 — eval harness** (backend lane, highest-leverage code gap):
  `backend/evals/` + `golden.jsonl` (100–200 problems) + `run.py`. From then
  on: *no model/prompt/retriever/route change merges without an eval run.*
  Also the instrument for kill-criterion 1.
- **B.1 — Elo estimator** (`observe(ev, prior)` per ADR-002) + `rebuild()`
  replay. Gate: item bank ≥150 for the chapter. Instruments: `rebuild()` wall
  time, ECE calibration.
- **B.2 — `GET /v1/next` + `POST /v1/attempts`** (pure SQL, ≈₹0/decision) +
  FSRS `due_at`. Instruments: p50/p95 (<100ms), event-log growth,
  attempts-to-mastery.
- **B.3 — practice screen** (UI lane): serve item → attempt → feedback loop.

**Exit:** the closed practice loop runs on Elo alone; **D7 retention on
practice is measurable** — the number that gates everything speculative.

## Horizon 3 — Better answers, provable margin (weeks 5–10)

All of these exist as specs in [[Opus-Execution-Plan]]; all become *provable*
only after P3 exists.

- **P2 — multi-retrieval:** FTS (`tsvector` + GIN) + RRF merge. Prove on the
  20-question A/B (formula lookups must win, conceptual must not regress).
- **P4 — router policy-as-data:** YAML routes + heuristic Understand stage +
  the **OCR-downgrade route** — the blended-cost lever toward ₹0.2/solve.
- **P5 — verifier v1** (3–5 wks, the moat): sympy + pint in a process pool →
  structured steps → parser → checkers (final-answer, step-transition via
  random evaluation, dimensional) → post-stream verdicts as SSE `verify`
  events. Checkers register on `app.verify.base.Verifier` / `Registry`
  (ADR-001) — A.0 already built the sockets. Badge says **"computation
  verified"**, never "solution verified". Ship gate: step-precision ≥99%,
  **false-verified <1% on the 30-problem red-team set or the badge does not
  ship** (kill-criterion 4). The eval report doubles as the public accuracy
  report — the sales asset.

## Horizon 4 — Gated bets (not scheduled)

- **C — learned estimator** (SAKT/AKT → Student-JEPA; "JEPA-inspired" until
  an encoder predicts latent states, ADR-008). Gate: **≥100k logged attempts**
  or public-data pretrain. Free GPU lane; A/B vs Elo under P3 discipline.
- **D — own model (RLVR distillation on P5 verdicts).** Gate: funding + paid
  tier + P5 shipped with false-verified <1%.
- **End of ₹0 phase** is a privacy line, not a budget line: first real
  student ⇒ paid Gemini tier (free tier trains on inputs; DPDP), restore
  DeepSeek/2.5-pro routing, flip region back to `asia-south1`.

## Parallel track — business (runs against the calendar, not the repo)

- **90-day institute kill-switch is running.** 3+ design-partner
  conversations; zero pilots in 90 days ⇒ P5 assets pivot to a verifier-API
  product (hence `verify/` stays import-clean of tutor code — tested).
- Razorpay/UPI vs Stripe decision for ₹299 India B2C · WhatsApp funnel ·
  credits applications (Google/AWS/Anthropic/Sarvam). **None have an owner.**
- KPIs live from P0 data (one SQL view each, weekly): D7/D30, cost/route,
  margin net of GST, feedback ratio.

## Kill criteria (pre-registered — moving them requires a written note)

1. Accuracy gate: ≥95% final-answer, ≥99% step-precision (P3 measures it)
2. 90 days / zero institutes ⇒ pivot
3. D30 < 10% ⇒ the loop doesn't retain; no model fixes it
4. False-verified > 1% ⇒ the badge does not ship

## Connections
- Executes → [[Opus-Execution-Plan]] (ask lane) + [[Adaptive-Loop-Architecture]] (practice lane)
- Board → [[Status]] · Gated by → [[Viability-Brutal-Honesty]] §5 · Hub → [[Startup-MOC]]
- Superseded detail → [[A1-Math-Verified-Tutor-Dev-Plan]] §4/§9 (the 2026-06-28 version of this note pointed there; its Phase 0–3 framing is folded into the horizons above)
