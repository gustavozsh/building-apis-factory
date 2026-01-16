from __future__ import annotations

import io
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from google.cloud import secretmanager, storage
from google.oauth2 import service_account
from googleapiclient.discovery import build

from shared.bigquery import load_dataframe_to_bigquery, normalize_dataframe
from shared.config import get_parameter, load_yaml_config, parse_secret_payload
from shared.dates import compute_date_range
from shared.secrets import access_secret

LOGGER = logging.getLogger("dv360_service")
logging.basicConfig(level=logging.INFO)

CONFIG_PATH = Path(__file__).with_name("config.yaml")

app = FastAPI(title="DV360 API", version="1.0.0")


class DV360LoadRequest(BaseModel):
    timezone: str | None = Field(default=None)
    start_date: str | None = Field(default=None, description="YYYY-MM-DD")
    end_date: str | None = Field(default=None, description="YYYY-MM-DD")
    reprocess_last_x_days: int | None = Field(default=1)
    advertiser_ids: list[str]
    metrics: list[str]
    dimensions: list[str]
    file_name: str | None = Field(default="dv360_report")
    query_id: str | None = Field(default=None)
    secret_project_id: str
    dv360_secret_id: str
    bq_secret_id: str
    destination_project_id: str
    destination_dataset: str
    destination_table: str
    delete_existing: bool | None = Field(default=False)
    partition_column: str | None = Field(default=None)
    max_retry_count: int | None = Field(default=10)
    min_retry_interval: int | None = Field(default=30)
    max_retry_interval: int | None = Field(default=60)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    parsed = urlparse(gcs_uri)
    if parsed.scheme != "gs":
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def download_report(credentials: service_account.Credentials, gcs_uri: str) -> pd.DataFrame:
    bucket_name, blob_path = parse_gcs_uri(gcs_uri)
    client = storage.Client(credentials=credentials, project=credentials.project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    content = blob.download_as_bytes()
    return pd.read_csv(io.BytesIO(content))


def run_dv360_query(
    service,
    advertiser_ids: list[str],
    metrics: list[str],
    dimensions: list[str],
    start_date: str,
    end_date: str,
    file_name: str,
    query_id: str | None,
    min_retry_interval: int,
    max_retry_interval: int,
    max_retry_count: int,
) -> dict[str, Any]:
    filters = [{"type": "FILTER_ADVERTISER", "value": advertiser_id} for advertiser_id in advertiser_ids]
    start_date_parts = start_date.split("-")
    end_date_parts = end_date.split("-")

    query_obj = {
        "metadata": {
            "title": file_name,
            "dataRange": {
                "range": "CUSTOM_DATES",
                "customStartDate": {
                    "year": int(start_date_parts[0]),
                    "month": int(start_date_parts[1]),
                    "day": int(start_date_parts[2]),
                },
                "customEndDate": {
                    "year": int(end_date_parts[0]),
                    "month": int(end_date_parts[1]),
                    "day": int(end_date_parts[2]),
                },
            },
            "format": "CSV",
        },
        "params": {
            "type": "STANDARD",
            "groupBys": dimensions,
            "filters": filters,
            "metrics": metrics,
        },
        "schedule": {"frequency": "ONE_TIME"},
    }

    query_id_to_use = query_id
    if not query_id_to_use:
        query_response = service.queries().create(body=query_obj).execute()
        query_id_to_use = query_response["queryId"]
        LOGGER.info("Created DV360 query %s", query_id_to_use)

    report_response = service.queries().run(queryId=query_id_to_use, synchronous=False).execute()
    report_key = report_response["key"]

    get_request = service.queries().reports().get(
        queryId=report_key["queryId"], reportId=report_key["reportId"]
    )

    attempts = 0
    delay = min_retry_interval
    while attempts < max_retry_count:
        report = get_request.execute()
        status = report["metadata"]["status"]["state"]
        if status in {"DONE", "FAILED"}:
            return report
        LOGGER.info("Report %s still running, waiting %s seconds", report_key["reportId"], delay)
        time.sleep(delay)
        delay = min(delay * 2, max_retry_interval)
        attempts += 1

    raise RuntimeError("Report polling unsuccessful. Report is still running.")


@app.post("/load")
async def load_dv360_report(payload: DV360LoadRequest) -> dict[str, Any]:
    config = load_yaml_config(CONFIG_PATH)
    request_json = payload.model_dump(exclude_none=True)

    try:
        timezone = get_parameter(
            request_json, "timezone", config.get("timezone", "America/Sao_Paulo")
        )
        start_date = get_parameter(request_json, "start_date")
        end_date = get_parameter(request_json, "end_date")
        reprocess_last_x_days = int(
            get_parameter(request_json, "reprocess_last_x_days", 1)
        )

        advertiser_ids = get_parameter(request_json, "advertiser_ids", required=True)
        metrics = get_parameter(request_json, "metrics", required=True)
        dimensions = get_parameter(request_json, "dimensions", required=True)
        file_name = get_parameter(request_json, "file_name", "dv360_report")
        query_id = get_parameter(request_json, "query_id")

        secret_project_id = get_parameter(
            request_json, "secret_project_id", config.get("secret_project_id"), True
        )
        dv360_secret_id = get_parameter(
            request_json, "dv360_secret_id", config.get("dv360_secret_id"), True
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
        delete_existing = bool(get_parameter(request_json, "delete_existing", False))
        partition_column = get_parameter(request_json, "partition_column")
        min_retry_interval = int(get_parameter(request_json, "min_retry_interval", 30))
        max_retry_interval = int(get_parameter(request_json, "max_retry_interval", 60))
        max_retry_count = int(get_parameter(request_json, "max_retry_count", 10))

        start_dt, end_dt = compute_date_range(
            timezone, start_date, end_date, reprocess_last_x_days
        )

        secret_client = secretmanager.SecretManagerServiceClient()
        dv360_secret_value = access_secret(
            secret_client, secret_project_id, dv360_secret_id
        )
        dv360_payload = parse_secret_payload(dv360_secret_value)
        if not isinstance(dv360_payload, dict):
            raise ValueError("DV360 secret must be a service account JSON payload.")

        bq_secret_value = access_secret(secret_client, secret_project_id, bq_secret_id)
        bq_payload = parse_secret_payload(bq_secret_value)
        if not isinstance(bq_payload, dict):
            raise ValueError("BigQuery secret must be a service account JSON payload.")

        dv360_credentials = service_account.Credentials.from_service_account_info(
            dv360_payload,
            scopes=["https://www.googleapis.com/auth/doubleclickbidmanager"],
        )
        bq_credentials = service_account.Credentials.from_service_account_info(bq_payload)

        service = build("doubleclickbidmanager", "v2", credentials=dv360_credentials, cache_discovery=False)

        report = run_dv360_query(
            service=service,
            advertiser_ids=advertiser_ids,
            metrics=metrics,
            dimensions=dimensions,
            start_date=start_dt.isoformat(),
            end_date=end_dt.isoformat(),
            file_name=file_name,
            query_id=query_id,
            min_retry_interval=min_retry_interval,
            max_retry_interval=max_retry_interval,
            max_retry_count=max_retry_count,
        )

        if report["metadata"]["status"]["state"] == "FAILED":
            raise RuntimeError("Report finished with error.")

        gcs_path = report["metadata"].get("googleCloudStoragePath")
        if not gcs_path:
            raise RuntimeError("Report did not provide a Google Cloud Storage path.")

        report_df = download_report(dv360_credentials, gcs_path)
        report_df["ingestion_time"] = datetime.utcnow().isoformat()

        report_df = normalize_dataframe(report_df, ["ingestion_time"])

        rows_loaded = load_dataframe_to_bigquery(
            df=report_df,
            credentials=bq_credentials,
            project_id=destination_project_id,
            dataset_id=destination_dataset,
            table_id=destination_table,
            start_date=start_dt,
            end_date=end_dt,
            account_ids=advertiser_ids,
            delete_existing=delete_existing,
            partition_column=partition_column,
        )

    except ValueError as error:
        LOGGER.exception("Invalid request")
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        LOGGER.exception("Failed to load DV360 report")
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "success": True,
        "rows_loaded": rows_loaded,
        "date_range": [start_dt.isoformat(), end_dt.isoformat()],
        "destination": f"{destination_project_id}.{destination_dataset}.{destination_table}",
    }
