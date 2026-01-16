# Azure Deployment Configurations

## Azure Container Instances

### Build and Push to Azure Container Registry
```bash
# Login to Azure
az login

# Create resource group
az group create --name building-apis-rg --location eastus

# Create container registry
az acr create --resource-group building-apis-rg --name buildingapisacr --sku Basic

# Login to ACR
az acr login --name buildingapisacr

# Build and push image
docker build -t buildingapisacr.azurecr.io/building-apis-factory:latest .
docker push buildingapisacr.azurecr.io/building-apis-factory:latest

# Deploy to Azure Container Instances
az container create \
  --resource-group building-apis-rg \
  --name building-apis-factory \
  --image buildingapisacr.azurecr.io/building-apis-factory:latest \
  --cpu 1 --memory 1 \
  --registry-login-server buildingapisacr.azurecr.io \
  --registry-username YOUR_USERNAME \
  --registry-password YOUR_PASSWORD \
  --dns-name-label building-apis-factory \
  --ports 8000 \
  --environment-variables ENV=production
```

## Azure App Service

Deploy as a containerized web app:
```bash
# Create App Service plan
az appservice plan create --name building-apis-plan --resource-group building-apis-rg --is-linux --sku B1

# Create web app
az webapp create --resource-group building-apis-rg --plan building-apis-plan --name building-apis-factory --deployment-container-image-name buildingapisacr.azurecr.io/building-apis-factory:latest

# Configure app settings
az webapp config appsettings set --resource-group building-apis-rg --name building-apis-factory --settings ENV=production
```

## Azure Kubernetes Service (AKS)

See `k8s-deployment.yaml` for Kubernetes deployment configuration.
