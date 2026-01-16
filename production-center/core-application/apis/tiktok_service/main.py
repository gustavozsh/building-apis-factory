from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from google.cloud import secretmanager
from google.oauth2 import service_account

from TikTok import TikTok

from shared.bigquery import load_dataframe_to_bigquery, normalize_dataframe
from shared.config import get_parameter, load_yaml_config, parse_secret_payload
from shared.dates import build_date_list, compute_date_range
from shared.secrets import access_secret

LOGGER = logging.getLogger("tiktok_service")
logging.basicConfig(level=logging.INFO)

CONFIG_PATH = Path(__file__).with_name("config.yaml")

app = FastAPI(title="TikTok Ads API", version="1.0.0")


class TikTokLoadRequest(BaseModel):
    timezone: str | None = Field(default=None)
    start_date: str | None = Field(default=None, description="YYYY-MM-DD")
    end_date: str | None = Field(default=None, description="YYYY-MM-DD")
    reprocess_last_x_days: int | None = Field(default=1)
    account_ids: list[str]
    dimensions: list[str]
    metrics: list[str]
    level: str | None = Field(default="AUCTION_AD")
    report_type: str | None = Field(default="BASIC")
    secret_project_id: str
    tiktok_secret_id: str
    bq_secret_id: str
    destination_project_id: str
    destination_dataset: str
    destination_table: str
    delete_existing: bool | None = Field(default=True)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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


@app.post("/load")
async def load_tiktok_report(payload: TikTokLoadRequest) -> dict[str, Any]:
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

        report_df = normalize_dataframe(report_df, ["created_time", "ingestion_time"])

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
            partition_column="created_time",
        )

    except ValueError as error:
        LOGGER.exception("Invalid request")
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        LOGGER.exception("Failed to load TikTok report")
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "success": True,
        "rows_loaded": rows_loaded,
        "date_range": [start_dt.isoformat(), end_dt.isoformat()],
        "destination": f"{destination_project_id}.{destination_dataset}.{destination_table}",
    }
