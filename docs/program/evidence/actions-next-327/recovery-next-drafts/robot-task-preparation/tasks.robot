*** Settings ***
Library    OperatingSystem

*** Tasks ***
Inspect record
    ${payload}=    Get File    %{ACTIONS_ROBOT_INPUT_FILE}
    Should Contain    ${payload}    synthetic

Inspect second record
    ${payload}=    Get File    %{ACTIONS_ROBOT_INPUT_FILE}
    Should Contain    ${payload}    synthetic
