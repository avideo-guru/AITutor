---
tags: [type/moc, domain/startup, status/active]
updated: 2026-06-28
---
# 🧠 Startup — Map of Content (idea_1)

> **One-line:** We are not building an AI tutor. We are building a **[[Verified-Reasoning-Engine]]** — a system that checks its own reasoning before it teaches — and the first product it powers is a JEE/NEET tutor that is *never confidently wrong*.

> **Who we are:** 4 first-year Math + CS students, low/moderate funding, India. Our edge is **math**, not capital. Our method is **research → build → research → build**. See [[Durable-Moat]] for why that wins.

---

## 🌟 Start here (the 3 ideas that define us)
- [[Verified-Reasoning-Engine]] — the core thesis. Verified reasoning is the *platform*; the tutor is product #1.
- [[Human-vs-AI-Tutor-Gap]] — *why a human tutor still beats every AI in 2026*, and how we close the gap. Our roadmap falls out of this.
- [[Durable-Moat]] — how we build a company that **survives AI changing every 3 months**. Level 1 / 2 / 3 startups; the Replaceability Principle.

## 🏗️ Architecture (the intelligence layer)
- [[Architecture-Options]] — 🆕 the three candidate designs (pipeline → gateway → agentic), model/API matrix, orchestration best practices. **Resolves the "how agentic in v1?" question: not agentic.**
- [[Cognitive-Architecture]] — the 5 layers + the model router. We build an "AI OS," not a chatbot.
- [[Verification-Engine]] — 🥇 **the moat**. "LLM proposes, math disposes." (deep dive → [[A1-Math-Verified-Tutor-Dev-Plan]] §1)
- [[Retrieval-Knowledge-Layer]] — retrieve *knowledge*, not documents. Content quality > model.
- [[Student-Model]] — the "active student state": intent, memory, misconceptions, mastery (BKT/IRT).

## 🎁 Product surface
- [[PRD]] — 🆕 the combined BRD/PRD: personas, functional requirements (F1–F7), NFRs (incl. DPDP), release plan, metrics.
- [[Lecture-Companion-Overlay]] — meet the student *inside the lecture they're already watching*; our verifier catches the teacher's mistakes live.
- [[Fast-vs-Guided-Toggle]] — "just verify" vs "walk me through," per-problem; the anti-cognitive-offloading nudge.

## 💻 Build / codebase
- [[Codebase-AITutor]] — the Angular 18 frontend prototype ([repo](https://github.com/avideo-guru/AITutor)). Currently a UI shell with a *fake* tutor service; the note maps where the real backend plugs in.

## 💡 Idea pipeline
- [[Startup-Idea-Radar]] — 🆕 rolling 3-pass scouting doc: idea-identification canon (Altman CS183B, PG/YC, 2026 RFS) + scored idea batches. Keeps us idea-rich and pressure-tests idea #1.

## 📈 Strategy & market
- [[Viability-Brutal-Honesty]] — 🆕 **read before pitching anyone**: the five brutal truths (melting accuracy wedge, engagement > accuracy, pricing vs free, untested GTM, autoformalization risk), competitor+human-tutor gap map, economics, and pre-registered kill criteria.
- [[Competitive-Landscape]] — the 4 failures every existing tutor has (and which one we each answer).
- [[Market-and-GTM]] — India, the two lanes, B2B2C through coaching institutes, pricing.
- [[Roadmap]] — phases, the 2-week kickoff, team roles.

## 🔬 Research engine (we are a research-first team)
- [[Research-Questions]] — the open questions driving each build cycle.
- [[Reading-List]] — papers & tools to digest (RLVR, knowledge tracing, autoformalization…).
- [[Papers-Index]] — 📚 **25 downloaded papers** in 8 topic folders (`Research/Papers/`), mapped to our architecture.
- [[Glossary]] — RLVR, BKT/IRT, Schwartz–Zippel, autoformalization, GRPO…

## 📚 Source docs (the originals — don't edit, link)
- [[A1-Math-Verified-Tutor-Dev-Plan]] — the full dev plan (verifier, roadmap, KPIs, team).
- [[AI-Startup-Ideas-US-Europe-to-India]] — the idea shortlist & decision matrix.
- [[High Level Architecture]] — the AI-native backend reference.

## 🗣️ Brainstorm log (raw thinking — provenance)
- [[brainstorming with claude]] — Cluely/Sarvam, lecture overlay, fast/guided toggle, competitor research.
- [[Brainstorming with Chatgpt]] — verified-reasoning-as-platform, the 10 gaps, cognitive architecture.

---

## 🧭 How to use this vault
1. **Decisions live in the spoke notes**, not in chat. When we settle something, it gets written into the relevant note above.
2. **ChatGPT's POV + Claude's POV get merged here** — see the `## Open / contested` sections in each note. Tag unresolved calls `#decision/open`.
3. **Every research dive ends in a note** under [[Research-Questions]] → then a build → then back. That loop *is* the company.

> Next physical step is always in [[Roadmap]] → "Right now".
