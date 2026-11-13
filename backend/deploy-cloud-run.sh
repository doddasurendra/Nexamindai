#!/usr/bin/env bash
# NexaMind AI — deploy backend to Cloud Run (run from Cloud Shell)
# Prereqs: gcloud authenticated, project set, Blaze plan enabled.
# Usage: ./deploy-cloud-run.sh

set -euo pipefail
PROJECT="${1:-nexamindai-427c1}"
REGION="${2:-asia-south1}"
SERVICE="nexamind-api"

echo "==> Deploying NexaMind AI backend to Cloud Run (project: $PROJECT, region: $REGION)"

# 1. Build env.yaml from .env if present
if [[ -f .env ]]; then
  echo "==> Converting .env to env.yaml"
  : > env.yaml
  while IFS= read -r line; do
    # skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$line" ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    echo "$key: $value" >> env.yaml
  done < .env
  echo "    env.yaml created ($(wc -l < env.yaml) vars)"
else
  echo "!! No .env found. Create env.yaml manually with your secrets (see .env.example)."
  echo "   Then re-run this script."
  exit 1
fi

# 2. Deploy from source (Cloud Build builds the image)
echo "==> Deploying to Cloud Run..."
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 600 \
  --port 8080 \
  --env-vars-file env.yaml

echo ""
echo "==> DONE. Get the service URL:"
gcloud run services describe "$SERVICE" --region "$REGION" --format="value(status.url)"
echo ""
echo "==> Then redeploy Firebase Hosting to wire the proxy:"
cd .. && firebase deploy --only hosting --non-interactive