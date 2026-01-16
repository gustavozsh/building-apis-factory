import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import yaml
from google.cloud import bigquery
from google.cloud import secretmanager
from google.oauth2 import service_account

from TikTok import TikTok


LOGGER = logging.getLogger("tiktok_api")
logging.basicConfig(level=logging.INFO)


def load_config() -> dict[str, Any]:
    config_path = Path(__file__).with_name("config.yaml")
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def get_parameter(
    payload: dict[str, Any],
    key: str,
    default: Any = None,
    required: bool = False,
) -> Any:
    if key in payload and payload[key] not in (None, ""):
        return payload[key]
    if required:
        raise ValueError(f"Missing required parameter: {key}")
    return default


def parse_secret_payload(payload: str) -> Any:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload


def access_secret(
    client: secretmanager.SecretManagerServiceClient,
    project_id: str,
    secret_id: str,
    version: str = "latest",
) -> str:
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("utf-8")


def compute_date_range(
    timezone: str,
    start_date: str | None,
    end_date: str | None,
    reprocess_last_x_days: int,
) -> tuple[date, date]:
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).date()

    if reprocess_last_x_days and (start_date or end_date):
        raise ValueError(
            "If using start_date/end_date, set reprocess_last_x_days to 0."
        )

    if reprocess_last_x_days > 0:
        start = today - timedelta(days=reprocess_last_x_days)
        end = today - timedelta(days=1)
        return start, end

    if start_date and end_date:
        return (
            datetime.strptime(start_date, "%Y-%m-%d").date(),
            datetime.strptime(end_date, "%Y-%m-%d").date(),
        )

    default_day = today - timedelta(days=1)
    return default_day, default_day


def build_date_list(start: date, end: date) -> list[str]:
    dates: list[str] = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df["created_time"] = pd.to_datetime(df["created_time"], errors="coerce")
    df["ingestion_time"] = pd.to_datetime(df["ingestion_time"], errors="coerce")

    for column in df.columns:
        if column not in {"created_time", "ingestion_time"}:
            df[column] = df[column].astype("string")

    return df


def delete_existing_rows(
    client: bigquery.Client,
    table_id: str,
    start_date: date,
    end_date: date,
    account_ids: list[str],
) -> None:
    query = f"""
        DELETE FROM `{table_id}`
        WHERE DATE(created_time) BETWEEN @start_date AND @end_date
          AND account_id IN UNNEST(@account_ids)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            bigquery.ArrayQueryParameter("account_ids", "STRING", account_ids),
        ]
    )
    job = client.query(query, job_config=job_config)
    job.result()
    LOGGER.info("Removed existing rows for date range %s - %s", start_date, end_date)


def load_dataframe_to_bigquery(
    df: pd.DataFrame,
    credentials: service_account.Credentials,
    project_id: str,
    dataset_id: str,
    table_id: str,
    start_date: date,
    end_date: date,
    account_ids: list[str],
    delete_existing: bool,
) -> int:
    client = bigquery.Client(credentials=credentials, project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    if delete_existing and not df.empty:
        delete_existing_rows(client, table_ref, start_date, end_date, account_ids)

    if df.empty:
        LOGGER.info("No rows to load for %s", table_ref)
        return 0

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
    )
    load_job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    result = load_job.result()
    LOGGER.info("Loaded %s rows into %s", result.output_rows, table_ref)
    return result.output_rows


def build_report_dataframe(
    tiktok_service: TikTok,
    account_ids: list[str],
    dates: list[str],
    dimensions: list[str],
    metrics: list[str],
    level: str,
    report_type: str,
) -> pd.DataFrame:
    dataframes: list[pd.DataFrame] = []

    for advertiser_id in account_ids:
        for date_str in dates:
            df = tiktok_service.request_report(
                advertiser_id=advertiser_id,
                start_date=date_str,
                end_date=date_str,
                dimensions=dimensions,
                metrics=metrics,
                level=level,
                report_type=report_type,
            )
            if df.empty:
                continue
            df["account_id"] = advertiser_id
            df["created_time"] = date_str
            df["ingestion_time"] = datetime.utcnow().isoformat()
            dataframes.append(df)

    if not dataframes:
        return pd.DataFrame()

    return pd.concat(dataframes, ignore_index=True)


def main(request):
    LOGGER.info("Starting TikTok API load")
    request_json = request.get_json(silent=True) or {}
    config = load_config()

    timezone = get_parameter(
        request_json, "timezone", config.get("timezone", "America/Sao_Paulo")
    )
    start_date = get_parameter(request_json, "start_date")
    end_date = get_parameter(request_json, "end_date")
    reprocess_last_x_days = int(
        get_parameter(request_json, "reprocess_last_x_days", 1)
    )

    account_ids = get_parameter(request_json, "account_ids", required=True)
    dimensions = get_parameter(request_json, "dimensions", required=True)
    metrics = get_parameter(request_json, "metrics", required=True)
    level = get_parameter(request_json, "level", "AUCTION_AD")
    report_type = get_parameter(request_json, "report_type", "BASIC")

    secret_project_id = get_parameter(
        request_json, "secret_project_id", config.get("secret_project_id"), True
    )
    tiktok_secret_id = get_parameter(
        request_json, "tiktok_secret_id", config.get("tiktok_secret_id"), True
    )
    bq_secret_id = get_parameter(
        request_json, "bq_secret_id", config.get("bq_secret_id"), True
    )

    destination_project_id = get_parameter(
        request_json,
        "destination_project_id",
        config.get("destination_project_id"),
        True,
    )
    destination_dataset = get_parameter(
        request_json, "destination_dataset", config.get("destination_dataset"), True
    )
    destination_table = get_parameter(
        request_json, "destination_table", config.get("destination_table"), True
    )
    delete_existing = bool(get_parameter(request_json, "delete_existing", True))

    start_dt, end_dt = compute_date_range(
        timezone, start_date, end_date, reprocess_last_x_days
    )
    dates = build_date_list(start_dt, end_dt)

    secret_client = secretmanager.SecretManagerServiceClient()
    tiktok_secret_value = access_secret(
        secret_client, secret_project_id, tiktok_secret_id
    )
    tiktok_payload = parse_secret_payload(tiktok_secret_value)
    if isinstance(tiktok_payload, dict):
        access_token = tiktok_payload.get("access_token")
    else:
        access_token = tiktok_payload

    if not access_token:
        raise ValueError("TikTok access token was not found in the secret payload.")

    bq_secret_value = access_secret(secret_client, secret_project_id, bq_secret_id)
    bq_payload = parse_secret_payload(bq_secret_value)
    if not isinstance(bq_payload, dict):
        raise ValueError("BigQuery secret must be a service account JSON payload.")

    credentials_bigquery = service_account.Credentials.from_service_account_info(
        bq_payload
    )

    tiktok_service = TikTok(access_token)
    report_df = build_report_dataframe(
        tiktok_service=tiktok_service,
        account_ids=account_ids,
        dates=dates,
        dimensions=dimensions,
        metrics=metrics,
        level=level,
        report_type=report_type,
    )

    report_df = normalize_dataframe(report_df)

    rows_loaded = load_dataframe_to_bigquery(
        df=report_df,
        credentials=credentials_bigquery,
        project_id=destination_project_id,
        dataset_id=destination_dataset,
        table_id=destination_table,
        start_date=start_dt,
        end_date=end_dt,
        account_ids=account_ids,
        delete_existing=delete_existing,
    )

    response = {
        "success": True,
        "rows_loaded": rows_loaded,
        "date_range": [start_dt.isoformat(), end_dt.isoformat()],
        "destination": f"{destination_project_id}.{destination_dataset}.{destination_table}",
    }
    return json.dumps(response), 200, {"Content-Type": "application/json"}


if __name__ == "__main__":
    class LocalRequest:
        def __init__(self, payload: dict[str, Any]):
            self._payload = payload

        def get_json(self, silent: bool = True) -> dict[str, Any]:
            return self._payload

    example_payload = {
        "account_ids": ["YOUR_ADVERTISER_ID"],
        "dimensions": ["ad_id", "stat_time_day"],
        "metrics": ["ad_name", "spend", "impressions"],
        "level": "AUCTION_AD",
        "report_type": "BASIC",
        "reprocess_last_x_days": 1,
        "secret_project_id": "your-secret-project",
        "tiktok_secret_id": "tiktok-access-token",
        "bq_secret_id": "bigquery-service-account",
        "destination_project_id": "your-gcp-project",
        "destination_dataset": "raw",
        "destination_table": "tb_tiktok_ads",
    }

    main(LocalRequest(example_payload))
