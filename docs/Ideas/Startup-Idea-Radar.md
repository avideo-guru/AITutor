---
tags: [type/note, domain/startup, startup/ideas, status/active]
updated: 2026-07-07
---
# 📡 Startup Idea Radar — rough directional brainstorm (3 passes)

> **What this is:** a deliberately rough scouting document. Not commitments — raw material to argue about, built in 3 passes. Pass 1 = how to identify ideas + "validated model → India" batch. Pass 2 = AI-native B2B/B2C/B2D batch. Pass 3 = harder/deeper problems + consolidated brutal ranking of everything.
> **Relationship to the main bet:** [[Startup-MOC]] (verified-reasoning tutor) remains idea #1. This radar exists so we're never idea-poor and so we can pressure-test #1 against alternatives.

---

## §0. How to identify ideas (the distilled canon)

### Sam Altman — CS183B "How to Start a Startup" (Stanford, the raw direction)
- Success = **Idea × Product × Team × Execution** — and idea is the *smallest* multiplier. A mediocre idea executed relentlessly beats a brilliant idea executed poorly.
- **The best ideas look bad at the beginning.** If it looked obviously great, a big company would already do it. You want "this seems like a toy / niche / bad market" ideas that ride a wave.
- **Look for anomalies** — unusual user behavior, people hacking spreadsheets/WhatsApp to do a job, markets growing faster than they should.
- Great idea test: small market today that will be **big in 10 years** (monopoly-first, per Thiel's lecture in the same course).
- Get **one small group of users to love you** — not many to like you. Love > like, depth > breadth.
- Only start it if you're **compelled by the problem**; a startup is a 10-year commitment and idea-shopping founders quit at year 2.

### Paul Graham / Jared Friedman (YC Startup School)
- **"Notice" ideas, don't "think up" ideas.** Organic ideas — problems you personally have — are where almost all the biggest YC companies came from.
- **Schlep blindness:** the best ideas are visibly painful, boring, and involve grinding through regulation/sales/ops — which is exactly why nobody does them (Stripe: thousands of devs *knew* payments were broken).
- Become a **domain expert first**; the person closest to the friction spots the opportunity first.
- Evaluate with: Is the market big (or getting big)? Founder-market fit? **Why now** — what changed (tech, regulation, cost curve) that makes this possible today and not 5 years ago?

### YC's Summer 2026 RFS — where the frontier thinks money is
The headline: *"AI has stopped being a feature and started being the foundation."* Three themes: (1) AI as infrastructure not feature, (2) AI pushed into the **physical/regulated/capital-intensive** world, (3) **replace, don't assist**. The 16 asks: low-pesticide agriculture AI, AI-native discovery engines, **AI-native service companies** (replace the accounting/insurance/compliance firm, not sell it software), AI personalized medicine, **Company Brain**, counter-drone-swarm defense, dynamic software interfaces, space electronics, hardware supply chain speed, space/lunar industry, agent-workflow inference chips, **SaaS challengers** (AI-native replacements of vulnerable incumbents), **software built for agents not humans**, startups selling straight to Fortune 100, semiconductor supply-chain visibility, the **AI Operating System for companies**.
→ For a low-capital Indian student team, the *usable* subset is: AI-native services, Company Brain, SaaS challengers, software-for-agents, dynamic interfaces. The hardware/space/defense half is out of reach and that's fine.

### The 2×-founder street advice (the Reddit post, distilled — keep this taped to the wall)
1. **Ideas have no inherent value; execution does.** ≥100 people in India are working on your idea right now. Share it openly; feedback compounds, secrecy doesn't.
2. Decide honestly: **"startup" (must be able to become $1B + scalable, measured on growth rate) vs "business" (fine, but different game).** Don't use startup metrics on a business or vice versa.
3. **Parents/friends are not validation.** The only validation: strangers who fit the ICP saying *how much* they'll pay — and then paying.
4. Unless it's SaaS, you don't need a tech person for months. (Inverted for us: we ARE the tech people — our risk is the opposite: building before selling.)
5. Incubators: apply *after* the first customer, not before.
6. **Your very first job is to find a customer. Sell before you build.**

### Our house rubric (used to score every idea below)
| Axis | 1 | 5 |
|---|---|---|
| **Crowded** (work already done on it) | virgin territory | saturated / funded incumbents |
| **Feasible** (for 4 math/CS students, low capital) | needs licenses/fleets/years | buildable in a semester |
| **Scalable** | field-sales/services shaped | software/PLG shaped |
| **Viable ₹** | unclear payer / thin ARPU | urgent pain + rich payer |
| **Why-now** | could've been done in 2019 | only possible since ~2025 |
| **Moat potential** | prompt + UI | data flywheel / domain logic / workflow lock-in |

**Brutal-honesty rule inherited from [[Viability-Brutal-Honesty]]:** for every idea ask (a) what kills it, (b) who pays and how much, (c) why hasn't it been done — "nobody thought of it" is never the real answer.

---

## §Pass 1 — Batch A: Validated model → India (10 ideas, easy → complex)

> Lane logic from [[AI-Startup-Ideas-US-Europe-to-India]]: the arbitrage is NOT "cheaper AI," it's *proven workflow, rebuilt on Indian rails (WhatsApp/UPI/vernacular/Tally), with a data or logic moat the US player will never build for India.*

### A1. NRI Elder-Care Command Center 🟢 easy-to-start
- **Validated by:** Honor/Papa/CareYaya (US home-care coordination, $B outcomes).
- **India twist & why the problem exists:** 30M+ NRIs earn in dollars while parents age alone in India; care today = a panicked WhatsApp group of relatives + an unvetted maid. Trust, verification, and coordination are absent because the *payer* (NRI child) and the *service* (local care) are 12,000 km apart.
- **Build:** subscription care-coordination: vetted aides + doctor visits + meds + emergency SLA, with an AI layer doing scheduling/monitoring/weekly reports to the NRI child. AI-native services play (YC RFS #3): *be* the agency, don't sell software to agencies.
- **Scores:** Crowded 2 · Feasible 3 (ops-heavy, city-by-city) · Scalable 2–3 · Viable ₹ **5** (dollar revenue, emotional purchase, ₹15–40k/mo) · Why-now 3 · Moat 3 (trust brand + ops playbook).
- **Brutal verdict:** the best *business* on this list and the worst *startup* — ops-shaped, scales like a franchise, not software. Money printer if you want cash flow; VC story is weak. Not a math-team company.

### A2. AI Health-Insurance Claim Fighter (B2C India) 🟢 easy
- **Validated by:** US claim-denial fighters (Claimable etc.) riding the "AI vs insurer AI" wave.
- **Why the problem exists:** Indian health-insurance claim rejection/short-settlement is rampant (opaque policy language, deliberate friction, IRDAI complaints piling up); policyholders don't know their rights and ombudsman processes are alien to them.
- **Build:** upload policy + rejection letter → AI parses policy clauses, drafts the appeal/ombudsman complaint, tracks deadlines. Charge success fee or flat ₹499–1999/claim.
- **Scores:** Crowded 1–2 (India: nearly nobody) · Feasible **5** (documents + LLM + workflow) · Scalable 4 · Viable ₹ 4 (clear desperate payer at the moment of pain) · Why-now 4 · Moat 2–3 (clause/outcome dataset over time).
- **Brutal verdict:** genuinely underbuilt, cheap to test in weeks, and distribution is the killer — people only need you once (low LTV, no retention), CAC via content/SEO must be near-zero to work. Great first-customer discipline test (§0.6: sell before build — post in insurance-complaint forums TODAY).

### A3. GST/Compliance Autopilot as an AI-native CA service 🟡 medium
- **Validated by:** Pilot/Bench/Digits (US), YC's AI-native-services thesis; overlaps our old A-4 card but *inverted*: don't sell SaaS to CAs — **be the AI-native CA firm** for SMBs at ₹999/mo where a human CA charges ₹3–5k.
- **Why it exists:** GST is mandatory, monthly, penalty-backed, and 60M+ SMBs handle it with WhatsApp-and-shoebox chaos; CA capacity is the bottleneck.
- **Scores:** Crowded 3 (ClearTax et al. serve the top; the bottom 90% untouched) · Feasible 4 · Scalable 4 (AI does the work; humans only review) · Viable ₹ 4 (recurring, mandatory) · Why-now 4 (agents can now do full workflows) · Moat 3–4 (workflow ownership + corrections dataset).
- **Brutal verdict:** boring, real, recurring — the strongest "startup-grade" India play in this batch. Kill risks: CA-regulation (may need a CA in the loop/on the board), and trust ("who signs my filing?"). Needs one CA co-founder/advisor. Very schlep-blind — which is the argument *for* it.

### A4. WhatsApp-native Clinic/Lab Front Office (vertical AI agent) 🟡 medium
- **Validated by:** Toothy AI, Kairo Health (YC) — same card as A-2 in [[AI-Startup-Ideas-US-Europe-to-India]], kept here because it *still* isn't solved in India.
- **Why it exists:** millions of clinics run on paper + a receptionist's phone; no-shows and unanswered calls bleed revenue; US products will never integrate Tally/UPI/vernacular.
- **Scores:** Crowded 3 · Feasible 4 · Scalable 3 (city-by-city sales) · Viable ₹ 4 (₹2–5k/mo vs a salary is easy math) · Why-now 4 · Moat 4 (system-of-record lock-in).
- **Brutal verdict:** proven pain, fast revenue, modest ceiling. The trap: it becomes 50 bespoke integrations and you wake up a services company. Pick ONE sub-vertical (e.g. diagnostic labs) or don't do it.

### A5. Study-Abroad Counselor AI 🟡 medium
- **Validated by:** ApplyBoard/Leverage Edu proved the market; US "AI college counselor" wave proved the AI form factor.
- **Why it exists:** Indian agents are commission-driven (they push whichever university pays them), non-transparent, and concentrated in metros; 1.3M+ Indian students go abroad yearly and Tier-2/3 families fly blind.
- **Build:** student-side AI counselor — profile eval, university shortlist with honest admit-probability, SOP drafting, visa checklist — flat fee ₹5–15k vs agent's hidden ₹1–3L commissions. B2C + B2B2C via schools.
- **Scores:** Crowded 3–4 · Feasible 5 · Scalable 4 · Viable ₹ 3–4 (willingness-to-pay proven but seasonal, once-per-life) · Why-now 3 · Moat 2 (thin; outcomes data over years).
- **Brutal verdict:** easy to build, hard to defend; incumbents can bolt AI on. Only works if the wedge is *provable honesty* (publish admit-rate calibration — same "trust via verification" DNA as our tutor). Otherwise skip.

### A6. Tally-native "Company Brain" for Indian SMBs 🔴 complex
- **Validated by:** YC RFS #5 (Company Brain) + #16 (AI OS for companies) — the hottest global thesis, zero India-native player.
- **Why it exists:** the Indian SMB's "systems" are Tally + WhatsApp + Excel + the owner's head. No US Company-Brain startup will ever build Tally/GSTN/UPI/vernacular ingestion. Whoever owns that ingestion owns the Indian SMB AI layer.
- **Build:** connectors (Tally, bank statements, GST portal, WhatsApp Business) → unified knowledge/actions layer → agents that answer "which customer is 60 days overdue?" and then *act* (send the reminder, reconcile the payment).
- **Scores:** Crowded 2 (India-native) · Feasible 3 (connector hell) · Scalable 4–5 · Viable ₹ 4 · Why-now 5 · Moat **5** (integration + workflow + data trifecta).
- **Brutal verdict:** the biggest ceiling in Batch A and the most execution-risky: 18 months of unglamorous connector engineering before magic. Classic schlep-blindness candidate — which is exactly why it might still be open. Would need us to *live* inside 10 SMBs first (organic-idea rule: become the domain expert).

### A7. AI Property Due-Diligence & Title Search 🔴 complex
- **Validated by:** US title-tech (Doma etc. — mixed results) + legal-AI boom (Harvey).
- **Why it exists:** Indian property fraud is endemic; title records are fragmented across sub-registrar offices, states, languages, and decades of paper; buyers pay lawyers ₹25–100k for due diligence of wildly varying quality.
- **Scores:** Crowded 1–2 · Feasible 2 (records access is the wall — many states digitized but messy/gated) · Scalable 3 (state-by-state) · Viable ₹ 4–5 (high-stakes purchase, real fees) · Why-now 3–4 (Digital India land-records digitization + vernacular OCR finally good) · Moat 4 (parsed-registry dataset compounds).
- **Brutal verdict:** huge if the data access problem is solvable, dead if not. Needs a 2-week feasibility spike (can we programmatically pull + parse EC/title docs in 2 states?) before any further thought. High reward, high regulatory schlep.

### A8. Vernacular Voice Agent for ONE vertical: NBFC collections 🟡 medium
- Carried from [[AI-Startup-Ideas-US-Europe-to-India]] A-3 — still valid, still crowded (Bolna etc. funded). Only enter with an eval/quality wedge (our math). **Verdict unchanged: differentiate hard or skip.** Scores: Crowded 4 · Feasible 3 · Scalable 4 · Viable ₹ 4 · Why-now 4 · Moat 2–3.

### A9. Skilled-Trades Marketplace with AI verification 🟢 easy-to-describe, 🔴 hard-to-win
- **Validated by:** US trades boom (Angi→ Jobber-style vertical SaaS); India: UrbanCompany proved managed marketplaces.
- **Why it exists:** finding a *competent* electrician/plumber outside metros is word-of-mouth roulette; UC covers ~40 cities and squeezes workers.
- **Brutal verdict:** marketplaces need capital + ops armies; UC's shadow is long; a 4-person student team gets crushed. **Listed to show what a NO looks like.** Scores: Crowded 4 · Feasible 1–2 · Scalable 3 · Viable ₹ 3 · Moat 2.

### A10. Exam/Board "Answer-Sheet Grading AI" for schools & coaching 🟡 medium — *adjacent to our tutor*
- **Validated by:** Gradescope (acquired, US universities standard) — a proven model with NO Indian equivalent at K-12/coaching scale.
- **Why it exists:** teachers in coaching institutes hand-grade thousands of mock-test sheets weekly; feedback latency kills learning loops; nobody trusts pure-LLM grading (same trust problem as tutoring!).
- **Build:** scan handwritten answer sheets → OCR → rubric-based AI grading with **verification/consistency guarantees** (our DNA) → analytics to the institute. Sells to the same coaching institutes as the tutor — **same GTM channel, second product.**
- **Scores:** Crowded 2 (India) · Feasible 4 (handwriting OCR is the hard bit) · Scalable 4 · Viable ₹ 4 (saves teacher-hours = easy ROI math) · Why-now 4 · Moat 3–4 (rubric + error datasets, institute lock-in).
- **Brutal verdict:** quietly the most strategic idea in this batch *for us specifically* — same buyer, same trust-via-verification moat, and it monetizes even if students never chat with an AI. Should be evaluated as the tutor's companion product, not a separate company.

---

## §Pass 1 → Pass 2 handoff (do not delete — loop state)
- **Pass 2 (next):** AI-native B2B/B2C/B2D batch — dev-tools/agent-infra (B2D), consumer AI, SaaS-challenger plays; mine YC W26/S25 batch lists + "software for agents" + eval-infra adjacencies; add 8–10 idea cards with same rubric.
- **Pass 3 (last):** complex/deep problems (research-flavored: verification-as-infra, Indic data engines, personalized-medicine-lite, agri-intelligence) + **consolidated ranking table of ALL ideas across passes** + final brutal shortlist of top 3 with next-action for each. Then close the loop.

## Sources (Pass 1)
- [YC Requests for Startups (Summer 2026)](https://www.ycombinator.com/rfs) · [TheVCCorner — all 15 + 150 concrete ideas](https://www.thevccorner.com/p/yc-summer-2026-requests-for-startups-ideas) · [TNW on YC's hard-tech pivot](https://thenextweb.com/news/yc-summer-2026-rfs-hard-tech-pivot)
- [Sam Altman — How to Start a Startup (course site)](https://startupclass.samaltman.com/) · [CS183B notes](https://iampurvil.com/2021/10/15/notes-on-sam-altmans-how-to-start-a-startup/) · [Lecture 1 transcript](https://www.bnjs.co/2014/09/25/transcript-lecture-1-how-to-start-a-startup/)
- [YC — How to get startup ideas](https://www.ycombinator.com/library/8g-how-to-get-startup-ideas) · [Jared Friedman framework notes](https://alex-goff.medium.com/jared-friedmans-how-to-generate-startup-ideas-9120352016b0) · [PG's advice distilled](https://www.gavrilobozovic.com/thoughts/paul-graham)
- [India startup ecosystem 2026 — funding trends](https://valueaddvc.com/blog/india-startup-ecosystem-2026-funding-trends-top-investors-and-breakout-companies) · [Inc42 — Indian startups 2026 predictions](https://inc42.com/features/indian-startups-in-2026-trends-predictions/) · [Vertical SaaS 2026 niches](https://qubit.capital/blog/rise-vertical-saas-sector-specific-opportunities)

## Connections
- Method inherited from → [[Viability-Brutal-Honesty]] (brutal rubric) · Prior shortlist → [[AI-Startup-Ideas-US-Europe-to-India]]
- Hub → [[Startup-MOC]]
