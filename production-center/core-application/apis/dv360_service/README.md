# DV360 Service API

API para gerar relatórios do DV360 (DoubleClick Bid Manager) e carregar em uma tabela do BigQuery.

## Endpoints

- `GET /health` — Health check.
- `POST /load` — Executa a query e carrega o CSV gerado pelo DV360 no BigQuery.

## Exemplo de payload

```json
{
  "advertiser_ids": ["123456"],
  "metrics": ["METRIC_IMPRESSIONS", "METRIC_CLICKS"],
  "dimensions": ["FILTER_ADVERTISER", "FILTER_LINE_ITEM"],
  "file_name": "dv360_report",
  "reprocess_last_x_days": 7,
  "secret_project_id": "my-secrets-project",
  "dv360_secret_id": "dv360-service-account",
  "bq_secret_id": "bigquery-service-account",
  "destination_project_id": "my-gcp-project",
  "destination_dataset": "raw",
  "destination_table": "tb_dv360",
  "delete_existing": false,
  "partition_column": "date"
}
```

## Secrets esperados

- `dv360_secret_id`: JSON de conta de serviço com acesso ao DV360 e GCS.
- `bq_secret_id`: JSON de conta de serviço do BigQuery.
