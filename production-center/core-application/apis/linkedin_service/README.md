# LinkedIn Service API

API para coletar dados de organizações e posts no LinkedIn e carregar em tabelas do BigQuery.

## Endpoints

- `GET /health` — Health check.
- `POST /load` — Coleta dados e carrega em duas tabelas (geral e posts).

## Exemplo de payload

```json
{
  "organization_urn": "urn:li:organization:511241",
  "client_name": "CLIENTE NAME",
  "posts_count": 40,
  "secret_project_id": "my-secrets-project",
  "linkedin_secret_id": "linkedin-access-token",
  "bq_secret_id": "bigquery-service-account",
  "destination_project_id": "my-gcp-project",
  "destination_dataset": "raw",
  "destination_general_table": "tb_linkedin_general",
  "destination_posts_table": "tb_linkedin_posts",
  "delete_existing": false
}
```

## Secrets esperados

- `linkedin_secret_id`: pode ser apenas o `access_token` ou um JSON com `access_token`.
- `bq_secret_id`: JSON de conta de serviço do BigQuery.
