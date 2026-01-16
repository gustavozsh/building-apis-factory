# Google Ads Service API

API para executar queries no Google Ads API e carregar em uma tabela do BigQuery.

## Endpoints

- `GET /health` — Health check.
- `POST /load` — Executa a query e carrega os dados no BigQuery.

## Exemplo de payload

```json
{
  "customer_ids": ["1234567890"],
  "query": "SELECT segments.date, metrics.clicks FROM campaign WHERE segments.date DURING LAST_7_DAYS",
  "reprocess_last_x_days": 7,
  "secret_project_id": "my-secrets-project",
  "google_ads_secret_id": "google-ads-credentials",
  "bq_secret_id": "bigquery-service-account",
  "destination_project_id": "my-gcp-project",
  "destination_dataset": "raw",
  "destination_table": "tb_google_ads",
  "delete_existing": false,
  "partition_column": "segments.date"
}
```

## Secrets esperados

- `google_ads_secret_id`: JSON com as credenciais do Google Ads API (`developer_token`, `client_id`, `client_secret`, `refresh_token`, `login_customer_id` quando aplicável).
- `bq_secret_id`: JSON de conta de serviço do BigQuery.
