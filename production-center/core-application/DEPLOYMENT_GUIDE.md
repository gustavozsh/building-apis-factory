# Guia de Deploy das APIs (Cloud Run + BigQuery)

Este documento descreve como preparar, configurar e fazer deploy das APIs (TikTok, Google Ads, DV360 e LinkedIn) do diretório `production-center/core-application` no **Google Cloud Run**, com carga de dados no **BigQuery**.

## 1. Pré-requisitos

- Projeto GCP com faturamento ativo.
- `gcloud` instalado e autenticado.
- APIs habilitadas:
  - Cloud Run
  - Artifact Registry
  - Secret Manager
  - BigQuery
  - (Opcional) Cloud Logging
- Permissões para criar serviços no Cloud Run e gerenciar secrets.

## 2. Estrutura das APIs

Cada API é independente e possui:

```
production-center/core-application/apis/
  ├── tiktok_service/
  ├── google_ads_service/
  ├── dv360_service/
  └── linkedin_service/
```

Cada serviço contém `main.py`, `requirements.txt` e `Dockerfile`.

## 3. Criação de Secrets

Crie secrets para:

- **Tokens/credenciais das APIs** (TikTok, Google Ads, DV360, LinkedIn).
- **Conta de serviço do BigQuery** (JSON).\

Exemplo (JSON no arquivo `bq-sa.json`):

```bash
gcloud secrets create bigquery-service-account --data-file=bq-sa.json
```

Exemplo para o token do TikTok:

```bash
echo '{"access_token": "SEU_TOKEN"}' | gcloud secrets create tiktok-access-token --data-file=-
```

Repita para os demais.

## 4. Criar dataset/tabelas no BigQuery

Crie dataset e tabelas (ou deixe que a carga crie as tabelas automaticamente quando permitido):

```bash
bq mk --dataset my-gcp-project:raw
```

## 5. Build e Push para Artifact Registry

Crie um repositório de container (uma vez):

```bash
gcloud artifacts repositories create api-services \
  --repository-format=docker \
  --location=us-central1
```

Configure Docker:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Exemplo: build da API TikTok

```bash
docker build -f production-center/core-application/apis/tiktok_service/Dockerfile \
  -t us-central1-docker.pkg.dev/my-gcp-project/api-services/tiktok-service:latest \
  .

docker push us-central1-docker.pkg.dev/my-gcp-project/api-services/tiktok-service:latest
```

Repita para as demais APIs, alterando o Dockerfile e o nome da imagem.

## 6. Deploy no Cloud Run

Exemplo para TikTok:

```bash
gcloud run deploy tiktok-service \
  --image us-central1-docker.pkg.dev/my-gcp-project/api-services/tiktok-service:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

Repita para Google Ads, DV360 e LinkedIn.

## 7. Permissões de execução

Garanta que a conta de serviço do Cloud Run tenha acesso ao Secret Manager e BigQuery.\
Exemplo (ajustar para seu serviço):

```bash
gcloud run services add-iam-policy-binding tiktok-service \
  --region us-central1 \
  --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

## 8. Como chamar as APIs

Todas as APIs possuem os endpoints:

- `GET /health`
- `POST /load`

### Exemplo de requisição

```bash
curl -X POST https://<cloud-run-url>/load \
  -H "Content-Type: application/json" \
  -d '{
    "account_ids": ["123456"],
    "dimensions": ["ad_id", "stat_time_day"],
    "metrics": ["ad_name", "spend"],
    "secret_project_id": "my-secrets-project",
    "tiktok_secret_id": "tiktok-access-token",
    "bq_secret_id": "bigquery-service-account",
    "destination_project_id": "my-gcp-project",
    "destination_dataset": "raw",
    "destination_table": "tb_tiktok_ads"
  }'
```

Consulte os READMEs individuais para payloads específicos:

- `apis/tiktok_service/README.md`
- `apis/google_ads_service/README.md`
- `apis/dv360_service/README.md`
- `apis/linkedin_service/README.md`

## 9. Observabilidade

Os logs ficam disponíveis no Cloud Logging (Console GCP).\
Recomenda-se configurar alertas e monitoramento em cima dos endpoints e do número de linhas carregadas.

## 10. Checklists por API

### TikTok
- Secret com token válido.
- Lista de contas e métricas/dimensões permitidas.

### Google Ads
- Secret com credenciais do Google Ads.
- Query válida (GAQL).

### DV360
- Conta de serviço com permissão de DV360.
- Métricas/dimensões válidas.

### LinkedIn
- Token válido.
- `organization_urn` e `client_name` corretos.
