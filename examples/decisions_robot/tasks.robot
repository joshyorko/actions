*** Settings ***
Documentation    Serial, local Work Item decision example. Source items remain pending.
Library          DecisionsDemo.py
Library          Collections

*** Variables ***
${STATE_DIR}    ${OUTPUT_DIR}/state
${BACKEND}      synthetic

*** Tasks ***
Classify Work Items And Persist Review Only Decisions
    Open Demo    ${STATE_DIR}    ${BACKEND}
    FOR    ${document}    IN    invoice    credit_note    other
        ${item}=    Get Synthetic Work Item    ${document}
        ${receipt}=    Decide Work Item    ${item}
        Dictionary Should Contain Value    ${receipt}    NEEDS_REVIEW
        Decision Should Match    ${receipt}    ${document}
        Source Should Remain Pending    ${item}
    END
    Reopen And Replay Without Inference
