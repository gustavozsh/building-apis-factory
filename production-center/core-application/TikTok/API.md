# API TikTok -> BigQuery

## Visao geral
Esta API foi desenvolvida para coletar dados do TikTok Ads e carregar o resultado em uma tabela do BigQuery. Ela foi pensada para rodar diariamente no Cloud Run, sendo orquestrada pelo Composer (Airflow), garantindo a ingestao de dados do dia anterior ou do intervalo configurado. O objetivo principal e padronizar a captura de dados, facilitar a manutencao e garantir historico consistente no BigQuery.

## Por que ela existe
- Automatizar a coleta de dados do TikTok em um pipeline confiavel.
- Permitir a carga diaria com reprocessamento controlado quando necessario.
- Centralizar a definicao de credenciais, datas e destino em configuracoes simples.

## Dados coletados
A API consulta o endpoint de relatorios do TikTok e retorna:
- Dimensoes solicitadas (ex.: `ad_id`, `stat_time_day`).
- Metricas solicitadas (ex.: `spend`, `impressions`, `clicks`).
- Colunas adicionadas pela API:
  - `account_id`
  - `created_time` (data referente ao registro)
  - `ingestion_time` (timestamp da carga)

## Onde os dados sao gravados
Os dados sao gravados em:
- Projeto GCP: definido no `config.yaml` ou no payload.
- Dataset BigQuery: definido no `config.yaml` ou no payload.
- Tabela BigQuery: definida no `config.yaml` ou no payload.

## Arquivos importantes
- `main.py`: funcao principal para o Cloud Run (funcao `main`).
- `config.yaml`: configuracoes basicas de projeto, dataset e tabela.
- `dags/tiktok_daily_load_dag.py`: DAG do Airflow usando Taskflow API.

## Payload esperado (exemplo)
```json
{
  "account_ids": ["7010742212912791553"],
  "dimensions": ["ad_id", "stat_time_day"],
  "metrics": ["ad_name", "spend", "impressions"],
  "level": "AUCTION_AD",
  "report_type": "BASIC",
  "reprocess_last_x_days": 1,
  "secret_project_id": "meu-projeto-secrets",
  "tiktok_secret_id": "tiktok-access-token",
  "bq_secret_id": "bigquery-sa",
  "destination_project_id": "meu-projeto",
  "destination_dataset": "raw",
  "destination_table": "tb_tiktok_ads",
  "delete_existing": true
}
```

## Como configurar o Cloud Run
1. Defina o `main.py` como entrypoint da funcao (`main`).
2. Garanta que o servico possua acesso aos Secrets do Secret Manager.
3. Configure variaveis de ambiente se preferir substituir o `config.yaml`.

## Como configurar o Airflow (Composer)
- Envie a DAG `tiktok_daily_load_dag.py` para o bucket de DAGs do Composer.
- Configure as Variaveis do Airflow:
  - `tiktok_cloud_run_url`: URL do Cloud Run.
  - `tiktok_api_config`: JSON com os parametros do payload (ver exemplo acima).

## Autor e data
- Autor: GPT-5.2-Codex (OpenAI)
- Data: 2026-01-16
