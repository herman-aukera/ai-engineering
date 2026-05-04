#!/bin/bash
set -e
mkdir -p ~/.cline/data
cp /workspaces/ai-engineering/.devcontainer/cline-config/globalState.template.json ~/.cline/data/globalState.json
cat > ~/.cline/data/secrets.json << EOF
{
  "moonshotApiKey": "${KIMI_API_KEY}",
  "deepSeekApiKey": "${DEEPSEEK_API_KEY}"
}
EOF
chmod 600 ~/.cline/data/secrets.json
echo "✅ Cline OOTB configured"
