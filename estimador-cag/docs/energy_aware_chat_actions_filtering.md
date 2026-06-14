# Energy Aware Chat Actions filtering

GitHub Actions has two different views:

1. **All workflows** shows every branch and every product experiment in this repository.
2. **Energy Aware Chat CI** is the dedicated proof workflow for this product branch.

For Energy Aware Chat, do not judge the branch from the unfiltered **All workflows** page.
That page can show unrelated red runs from other branches such as Energy Aware Code.

## Proof target

Use this exact target:

- Branch: `gg-finalproject-energy-aware-chat`
- Workflow: `Energy Aware Chat CI`
- Proof script: `bash estimador-cag/scripts/check_energy_chat_ci.sh`

The proof script filters by workflow name, branch, and exact commit SHA.

## Local proof first

From the project directory:

    cd /workspaces/ai-engineering/estimador-cag
    bash scripts/validate_energy_chat.sh

## CI proof second

From the repository root:

    cd /workspaces/ai-engineering
    bash estimador-cag/scripts/check_energy_chat_ci.sh

Accepted means both local validation and the exact dedicated CI proof pass for the same commit.
