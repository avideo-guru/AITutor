#!/usr/bin/env bash
# Deploy the FastAPI backend to Google Cloud Run (region asia-south1 / Mumbai).
#
# WHY this shape:
#   - `--source .` builds the image with Cloud Build server-side, so you do NOT
#     need Docker installed locally. It uses backend/Dockerfile.
#   - Secrets live in Secret Manager (--set-secrets), never in --set-env-vars,
#     so keys aren't visible in the service's plaintext env or `gcloud describe`.
#   - `--min-instances 0` = scale-to-zero (₹0 while idle, pre-launch). Flip to 1
#     at the institute pilot to kill cold starts.
#   - The backend streams SSE; Cloud Run allows long responses, but bump
#     --timeout so a slow LLM answer isn't cut at the default 300s.
#
# PREREQUISITES (run once, by you, in an authenticated shell — this script does
# NOT create your account or log you in):
#   1. Install the CLI:  https://cloud.google.com/sdk/docs/install
#   2. gcloud auth login
#   3. gcloud config set project <YOUR_GCP_PROJECT_ID>
#   4. gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
#        secretmanager.googleapis.com
#   5. Create the secrets (values from your real Supabase / provider dashboards):
#        printf '%s' "postgresql://..."  | gcloud secrets create DATABASE_URL              --data-file=-
#        printf '%s' "https://xdszkwjkaamyycirfslz.supabase.co" | gcloud secrets create SUPABASE_URL --data-file=-
#        printf '%s' "<service-role-key>" | gcloud secrets create SUPABASE_SERVICE_ROLE_KEY --data-file=-
#        printf '%s' "sk-..."            | gcloud secrets create DEEPSEEK_API_KEY          --data-file=-
#        printf '%s' "AI..."             | gcloud secrets create GEMINI_API_KEY            --data-file=-
#        printf '%s' "sk_test_..."       | gcloud secrets create STRIPE_SECRET_KEY         --data-file=-
#        printf '%s' "whsec_..."         | gcloud secrets create STRIPE_WEBHOOK_SECRET     --data-file=-
#        printf '%s' "price_..."         | gcloud secrets create STRIPE_PRICE_ID           --data-file=-
#      (Stripe secrets can be dummy values until billing is wired — the app only
#       reads them on the billing routes.)
#
# Then run this script from the repo root:  bash backend/deploy/cloudrun.sh
set -euo pipefail

SERVICE="aitutor-backend"
REGION="asia-south1"
FRONTEND_URL="${FRONTEND_URL:-https://aitutor.pages.dev}"  # override for your real Cloudflare domain

gcloud run deploy "$SERVICE" \
  --source backend \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 4 \
  --timeout 600 \
  --cpu 1 --memory 512Mi \
  --set-env-vars "FRONTEND_URL=${FRONTEND_URL},FREE_DAILY_LIMIT=10" \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest,SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:latest,DEEPSEEK_API_KEY=DEEPSEEK_API_KEY:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest,STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest,STRIPE_PRICE_ID=STRIPE_PRICE_ID:latest"

# After deploy, gcloud prints the service URL. Point:
#   - frontend/.env  ->  that URL (the API base)
#   - Stripe webhook ->  https://<service-url>/v1/billing/webhook
echo "Done. Set frontend API base + Stripe webhook to the URL above."
