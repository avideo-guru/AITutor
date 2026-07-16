"""The adaptive plane — the loop that decides what a student does next
([[Adaptive-Loop-Architecture]]).

A.0 ships contracts only. The implementations land behind them:
  - `state.py`  — EloEstimator (B.1), Student-JEPA (Phase C), both implementing
    `StateEstimator`.
  - `policy.py` — next-item selection (B.2) implementing `Policy`.

Import rule (enforced by test_adaptive_contracts.py): this package must not
import `app.routes`, `app.orchestrator`, or `app.models`. The adaptive plane is
consumed BY the routes, never the other way round — the same direction the P1
seams established, and what keeps the loop testable without a DB or an LLM.
"""
