#!/usr/bin/env bash
# Optional helper to push secrets to FastAPI Cloud.
# Usage: ./deploy/setup-secrets.sh
set -euo pipefail

echo "Set secrets interactively (values hidden):"
echo ""

read -r -p "API_KEY: " -s API_KEY && echo
fastapi cloud env set --secret API_KEY "$API_KEY"

read -r -p "Set OPENAI_API_KEY? [y/N] " ans
if [[ "${ans,,}" == "y" ]]; then
  read -r -p "OPENAI_API_KEY: " -s val && echo
  fastapi cloud env set --secret OPENAI_API_KEY "$val"
fi

read -r -p "Set SUPABASE_URL + key? [y/N] " ans
if [[ "${ans,,}" == "y" ]]; then
  read -r -p "SUPABASE_URL: " url
  fastapi cloud env set SUPABASE_URL "$url"
  read -r -p "SUPABASE_SERVICE_ROLE_KEY: " -s key && echo
  fastapi cloud env set --secret SUPABASE_SERVICE_ROLE_KEY "$key"
fi

echo ""
echo "Done. Redeploy for changes to take effect: fastapi deploy"
