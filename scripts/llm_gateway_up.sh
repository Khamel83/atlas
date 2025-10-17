#!/usr/bin/env bash
set -euo pipefail

# Run Bifrost locally, data persisted in user's home.
mkdir -p "${HOME}/.oos/bifrost"
docker run -d --restart=always \
  -p 127.0.0.1:8080:8080 \
  -v "${HOME}/.oos/bifrost:/app/data" \
  --name oos-bifrost \
  maximhq/bifrost:latest

echo "Bifrost up on http://127.0.0.1:8080  → open UI → Providers → add 'Anthropic' and 'ZAI' with your API keys."
echo "For OCI exposure, prefer SSH tunneling; only open the port in NSG + host firewall if you must."