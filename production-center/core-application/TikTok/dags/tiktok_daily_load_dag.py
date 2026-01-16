from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import requests
from airflow.decorators import dag, task
from airflow.models import Variable
from google.auth.transport.requests import Request
from google.oauth2 import id_token


DEFAULT_ARGS = {
    "owner": "data-platform",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def get_variable(name: str, default: Any | None = None) -> Any:
    if default is None:
        return Variable.get(name)
    return Variable.get(name, default_var=default)


@dag(
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["tiktok", "cloud-run", "daily-load"],
)
def tiktok_daily_load():
    @task
    def build_payload() -> dict[str, Any]:
        config = Variable.get("tiktok_api_config", deserialize_json=True)
        payload = {
            "account_ids": config["account_ids"],
            "dimensions": config["dimensions"],
            "metrics": config["metrics"],
            "level": config.get("level", "AUCTION_AD"),
            "report_type": config.get("report_type", "BASIC"),
            "reprocess_last_x_days": config.get("reprocess_last_x_days", 1),
            "secret_project_id": config["secret_project_id"],
            "tiktok_secret_id": config["tiktok_secret_id"],
            "bq_secret_id": config["bq_secret_id"],
            "destination_project_id": config["destination_project_id"],
            "destination_dataset": config["destination_dataset"],
            "destination_table": config["destination_table"],
            "delete_existing": config.get("delete_existing", True),
        }
        timezone = config.get("timezone")
        if timezone:
            payload["timezone"] = timezone
        return payload

    @task
    def call_cloud_run(payload: dict[str, Any]) -> dict[str, Any]:
        cloud_run_url = get_variable("tiktok_cloud_run_url")
        audience = cloud_run_url

        token = id_token.fetch_id_token(Request(), audience)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            cloud_run_url,
            headers=headers,
            json=payload,
            timeout=180,
        )
        response.raise_for_status()
        return response.json()

    call_cloud_run(build_payload())


tiktok_daily_load()
