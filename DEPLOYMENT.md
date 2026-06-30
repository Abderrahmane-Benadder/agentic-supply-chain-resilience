# Google Cloud Deployment Guide

This project can be deployed as an ADK FastAPI service on Google Cloud Run. Cloud Run is the recommended first deployment target for this capstone because the repository already includes a Dockerfile and `adk_app.fast_api_app:app`.

## Current Local Status
- Docker is installed.
- `gcloud` is installed at `C:\Users\aben5\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`.
- The ADK backend has a Cloud Run-ready Dockerfile.
- The Streamlit dashboard has a separate `Dockerfile.streamlit`.
- `.env` is ignored and must not be copied into the image.
- Cloud Run deployment succeeded for project `kaggle-project-500912`.
- Live Streamlit dashboard URL: `https://supply-chain-dashboard-xxzkv6nlxa-ue.a.run.app`
- Live ADK backend URL: `https://supply-chain-resilience-xxzkv6nlxa-ue.a.run.app`

## Before Deploying
Install Google Cloud CLI:

https://cloud.google.com/sdk/docs/install

Then authenticate:

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Confirm:

```powershell
gcloud --version
gcloud config list
gcloud auth list
```

Confirm billing is enabled before enabling APIs or deploying:

```powershell
gcloud billing accounts list
gcloud beta billing projects describe YOUR_PROJECT_ID
```

If `billingEnabled` is not `true`, open Google Cloud Console, attach a billing account to the project, then rerun the API enablement step. Cloud Run, Cloud Build, Artifact Registry, and Secret Manager cannot be enabled without billing.

## Enable Required APIs
```powershell
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  secretmanager.googleapis.com `
  aiplatform.googleapis.com `
  --project YOUR_PROJECT_ID
```

## Store Gemini API Key In Secret Manager
Do not deploy `.env`.

```powershell
echo YOUR_GEMINI_API_KEY | gcloud secrets create GEMINI_API_KEY --data-file=-
```

If the secret already exists:

```powershell
echo YOUR_GEMINI_API_KEY | gcloud secrets versions add GEMINI_API_KEY --data-file=-
```

## Deploy ADK Backend To Cloud Run
Run from the project root:

```powershell
gcloud run deploy supply-chain-resilience `
  --source . `
  --region us-east1 `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 1 `
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest `
  --set-env-vars GEMINI_MODEL=gemini-2.5-flash,GOOGLE_GENAI_USE_VERTEXAI=False
```

Cloud Run will build the Dockerfile and return a service URL.

## Deploy Streamlit Dashboard To Cloud Run
The Streamlit dashboard is deployed as a separate service so the planner UI and ADK backend can be verified independently.

```powershell
gcloud builds submit `
  --project kaggle-project-500912 `
  --config cloudbuild.streamlit.yaml `
  --substitutions _IMAGE=us-east1-docker.pkg.dev/kaggle-project-500912/cloud-run-source-deploy/supply-chain-dashboard:latest `
  .

gcloud run deploy supply-chain-dashboard `
  --project kaggle-project-500912 `
  --region us-east1 `
  --image us-east1-docker.pkg.dev/kaggle-project-500912/cloud-run-source-deploy/supply-chain-dashboard:latest `
  --allow-unauthenticated `
  --port 8080 `
  --memory 2Gi `
  --cpu 1 `
  --max-instances 3 `
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest `
  --set-env-vars GEMINI_MODEL=gemini-2.5-flash,GOOGLE_GENAI_USE_VERTEXAI=False
```

## Verify The Cloud Run Service
Open:

```text
https://supply-chain-dashboard-xxzkv6nlxa-ue.a.run.app
https://supply-chain-resilience-xxzkv6nlxa-ue.a.run.app
```

The dashboard URL should load the Streamlit planner interface. The ADK web UI should list only one app: `adk_app`. Select `adk_app`, create or use a session, then enter a prompt. Both the dashboard page and backend `/run` endpoint have been smoke-tested successfully.

Useful endpoints are served by the ADK FastAPI app. You can also inspect logs:

```powershell
gcloud logging read `
  "resource.type=cloud_run_revision AND resource.labels.service_name=supply-chain-resilience" `
  --project YOUR_PROJECT_ID `
  --limit 50 `
  --format "table(timestamp,severity,textPayload)"
```

## Optional: Deploy With Agents CLI
The project is currently marked as `deployment_target: none` in `agents-cli-manifest.yaml`. To use `agents-cli deploy`, first enhance the manifest for Cloud Run or Agent Runtime:

```powershell
agents-cli scaffold enhance . --deployment-target cloud_run --agent-directory adk_app
agents-cli deploy --project YOUR_PROJECT_ID --region us-east1
```

Use this path only after tests and eval smoke checks pass.

## Optional: Agent Runtime
Agent Runtime is more ADK-native, but requires more Google Cloud setup:

```powershell
agents-cli scaffold enhance . --deployment-target agent_runtime --agent-directory adk_app
agents-cli deploy --project YOUR_PROJECT_ID --region us-east1
```

After deployment, `deployment_metadata.json` can be used for Gemini Enterprise registration.

## Kaggle Submission Flow
Cloud deployment is optional for Kaggle. The minimum strong submission is:
1. Public GitHub repository.
2. `README.md`.
3. `KAGGLE_SUBMISSION.md`.
4. Screenshots or a short demo video.
5. Optional Cloud Run URL.

## Safety Notes
- Deployment may create billable Google Cloud resources.
- Confirm project ID and billing before deploying.
- Keep `--allow-unauthenticated` only for public demos. For private demos, remove it and use authenticated access or IAP.
- Rotate the Gemini API key after public demos if needed.

## Final Pre-Deploy Checklist
```powershell
python -m pytest
python -c "from adk_app.fast_api_app import app; print(app.title)"
adk run adk_app "Explain the agent architecture."
docker build -t supply-chain-resilience .
```
