# Google Cloud Platform Deployment

## Google Cloud Run

Cloud Run is the easiest way to deploy containerized applications:

```bash
# Install and authenticate gcloud CLI
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/building-apis-factory

# Deploy to Cloud Run
gcloud run deploy building-apis-factory \
  --image gcr.io/YOUR_PROJECT_ID/building-apis-factory \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENV=production \
  --port 8000
```

## Google Kubernetes Engine (GKE)

For Kubernetes deployment:

```bash
# Create GKE cluster
gcloud container clusters create building-apis-cluster \
  --num-nodes=3 \
  --zone us-central1-a

# Get credentials
gcloud container clusters get-credentials building-apis-cluster --zone us-central1-a

# Apply Kubernetes configuration
kubectl apply -f cloud/k8s-deployment.yaml
kubectl apply -f cloud/k8s-service.yaml
```

## Google Compute Engine

Standard VM deployment:
1. Create a VM instance
2. Install Docker
3. Pull and run the container
4. Configure firewall rules for port 8000

## Environment Variables

Configure in Cloud Run or GKE:
- `ENV`: production
