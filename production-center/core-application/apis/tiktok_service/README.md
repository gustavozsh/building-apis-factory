# TikTok Service API

API para extrair relatórios do TikTok Ads e carregar em uma tabela do BigQuery.

## Endpoints

- `GET /health` — Health check.
- `POST /load` — Executa a extração e carga no BigQuery.

## Exemplo de payload

```json
{
  "account_ids": ["1234567890"],
  "dimensions": ["ad_id", "stat_time_day"],
  "metrics": ["ad_name", "spend", "impressions"],
  "level": "AUCTION_AD",
  "report_type": "BASIC",
  "reprocess_last_x_days": 1,
  "secret_project_id": "my-secrets-project",
  "tiktok_secret_id": "tiktok-access-token",
  "bq_secret_id": "bigquery-service-account",
  "destination_project_id": "my-gcp-project",
  "destination_dataset": "raw",
  "destination_table": "tb_tiktok_ads",
  "delete_existing": true
}
```

## Secrets esperados

- `tiktok_secret_id`: pode ser apenas o `access_token` ou um JSON com `access_token`.
- `bq_secret_id`: JSON de conta de serviço do BigQuery.
