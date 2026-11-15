*** Settings ***
Documentation    Host-injected managed claim. Human resolution runs separately.
Library          ManagedDecisions.py    ${DECISION_SERVICE}    ${DECISION_CALLER}    ${DECISION_EVALUATION}

*** Tasks ***
Evaluate Claimed Work Item And Retain Review Proposal
    Evaluate Current Work Item Claim
    Decision Should Require Human Review
    Replay Should Reuse Exact Decision
