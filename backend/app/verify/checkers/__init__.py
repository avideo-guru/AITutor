"""Checker implementations. One module per check type; each implements the
`Verifier` Protocol in `app.verify.base` and is registered on a `Registry`
([[Adaptive-Loop-Architecture]] §3.3b).

Ships in A.0: `gold` (curated final-answer compare).
Arrives with P5.0: `symbolic` (sympy equivalence), `steps` (step-transition via
random numeric evaluation), `dimensional` (pint). Later: chemistry balancing,
sandboxed execution, SMT.
"""
