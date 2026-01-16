from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf.json_format import MessageToDict
from google.cloud import secretmanager
from google.oauth2 import service_account

from shared.bigquery import load_dataframe_to_bigquery, normalize_dataframe
from shared.config import get_parameter, load_yaml_config, parse_secret_payload
from shared.dates import compute_date_range
from shared.secrets import access_secret

LOGGER = logging.getLogger("google_ads_service")
logging.basicConfig(level=logging.INFO)

CONFIG_PATH = Path(__file__).with_name("config.yaml")

app = FastAPI(title="Google Ads API", version="1.0.0")


class GoogleAdsLoadRequest(BaseModel):
    timezone: str | None = Field(default=None)
    start_date: str | None = Field(default=None, description="YYYY-MM-DD")
    end_date: str | None = Field(default=None, description="YYYY-MM-DD")
    reprocess_last_x_days: int | None = Field(default=1)
    customer_ids: list[str]
    query: str
    secret_project_id: str
    google_ads_secret_id: str
    bq_secret_id: str
    destination_project_id: str
    destination_dataset: str
    destination_table: str
    delete_existing: bool | None = Field(default=False)
    partition_column: str | None = Field(
        default=None,
        description="Optional partition column for delete_existing (e.g. segments_date)",
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def fetch_google_ads_report(
    client: GoogleAdsClient, customer_id: str, query: str
) -> pd.DataFrame:
    service = client.get_service("GoogleAdsService")
    response = service.search_stream(customer_id=customer_id, query=query)

    rows_list: list[dict[str, Any]] = []
    for batch in response:
        for row in batch.results:
            row_json = MessageToDict(row)
            rows_list.append(row_json)

    if not rows_list:
        return pd.DataFrame()

    df = pd.json_normalize(rows_list)
    df["customer_id"] = customer_id
    df["ingestion_time"] = datetime.utcnow().isoformat()
    return df


@app.post("/load")
async def load_google_ads_report(payload: GoogleAdsLoadRequest) -> dict[str, Any]:
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

        customer_ids = get_parameter(request_json, "customer_ids", required=True)
        query = get_parameter(request_json, "query", required=True)

        secret_project_id = get_parameter(
            request_json, "secret_project_id", config.get("secret_project_id"), True
        )
        google_ads_secret_id = get_parameter(
            request_json,
            "google_ads_secret_id",
            config.get("google_ads_secret_id"),
            True,
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

        start_dt, end_dt = compute_date_range(
            timezone, start_date, end_date, reprocess_last_x_days
        )

        secret_client = secretmanager.SecretManagerServiceClient()
        google_ads_secret_value = access_secret(
            secret_client, secret_project_id, google_ads_secret_id
        )
        google_ads_payload = parse_secret_payload(google_ads_secret_value)
        if not isinstance(google_ads_payload, dict):
            raise ValueError("Google Ads secret must be a JSON payload.")

        google_ads_payload["use_proto_plus"] = "false"
        google_ads_client = GoogleAdsClient.load_from_dict(google_ads_payload)

        bq_secret_value = access_secret(secret_client, secret_project_id, bq_secret_id)
        bq_payload = parse_secret_payload(bq_secret_value)
        if not isinstance(bq_payload, dict):
            raise ValueError("BigQuery secret must be a service account JSON payload.")

        credentials_bigquery = service_account.Credentials.from_service_account_info(
            bq_payload
        )

        dataframes: list[pd.DataFrame] = []
        for customer_id in customer_ids:
            df = fetch_google_ads_report(google_ads_client, customer_id, query)
            if not df.empty:
                dataframes.append(df)

        report_df = pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()
        report_df = normalize_dataframe(report_df, ["segments.date", "ingestion_time"])

        rows_loaded = load_dataframe_to_bigquery(
            df=report_df,
            credentials=credentials_bigquery,
            project_id=destination_project_id,
            dataset_id=destination_dataset,
            table_id=destination_table,
            start_date=start_dt,
            end_date=end_dt,
            account_ids=customer_ids,
            delete_existing=delete_existing,
            partition_column=partition_column,
        )

    except ValueError as error:
        LOGGER.exception("Invalid request")
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        LOGGER.exception("Failed to load Google Ads report")
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "success": True,
        "rows_loaded": rows_loaded,
        "date_range": [start_dt.isoformat(), end_dt.isoformat()],
        "destination": f"{destination_project_id}.{destination_dataset}.{destination_table}",
    }
