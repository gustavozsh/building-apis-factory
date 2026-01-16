import json
import uuid
import time
import traceback
import pandas as pd
from datetime import datetime
from loguru import logger
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as SA_Credentials
from pathlib import Path
from cadastra_core import SecretManager
from cadastra_core import TikTok
from cadastra_core import BigQuery
from cadastra_core import Utils


UUID = uuid.uuid4()


def format_columns(df):
    if "date_loading" in df.columns:
        df = df.drop(columns=["date_loading"])

    if "media_source" in df.columns:
        df = df.drop(columns=["media_source"])

    return df


def main(request):
    logger.info(f"{UUID} - Starting the process TikTok")
    request_json = request.get_json()
    start_time = time.time()
    utils = Utils()
    notification_webhook_url: str = utils.get_parameter(
        json=request_json, parameter="notification_webhook_url"
    )

    notification_summary = {
        "function_name": utils.get_function_name() or "TikTok",
    }

    try:
        secret_id: str = utils.get_parameter(json=request_json, parameter="secret_id")
        secret_project_id: str = utils.get_parameter(
            json=request_json, parameter="secret_project_id"
        )
        bq_secret_id: str = utils.get_parameter(
            json=request_json, parameter="bq_secret_id"
        )
        bq_secret_project: str = utils.get_parameter(
            json=request_json, parameter="bq_secret_project"
        )
        reprocess_last_x_days: int = (
            utils.get_parameter(json=request_json, parameter="reprocess_last_x_days")
            or 0
        )
        start_date: str = utils.get_parameter(json=request_json, parameter="start_date")
        end_date: str = utils.get_parameter(json=request_json, parameter="end_date")
        destination_table: str = utils.get_parameter(
            json=request_json, parameter="destination_table"
        )
        destination_project_id: str = utils.get_parameter(
            json=request_json, parameter="destination_project_id"
        )

        account_ids = utils.get_parameter(request_json, "account_ids")
        dimensions = utils.get_parameter(request_json, "dimensions")
        level = utils.get_parameter(request_json, "level")
        report_type = utils.get_parameter(request_json, "report_type")
        metrics = utils.get_parameter(request_json, "metrics")

        if (start_date or end_date) and reprocess_last_x_days:
            raise Exception(
                "If using start_date/end_date, you should set 'reprocess_last_x_days' to 0"
            )

        if reprocess_last_x_days > 0:
            start_date = utils.get_last_x_days(reprocess_last_x_days)
            end_date = utils.get_yesterday()

        notification_summary["date_range"] = [start_date, end_date]
        notification_summary["destination_table"] = (
            f"{destination_project_id}.{destination_table}"
        )
        notification_summary["account_id"] = ", ".join(account_ids)

        # Get the credentials
        secret_manager = SecretManager()
        credentials_tiktok = json.loads(
            secret_manager.access_secret_version(secret_id, secret_project_id)
        )["access_token"]

        credentials_big_query = SA_Credentials.from_service_account_info(
            json.loads(
                secret_manager.access_secret_version(bq_secret_id, bq_secret_project)
            )
        )

        # Authenticate in TikTok
        tiktok_service = TikTok(credentials_tiktok)
        logger.info(f"{UUID} - Requesting the report")

        utils = Utils()
        date_array = utils.get_date_array(start_date, end_date)
        lista_dfs = []

        for advertiser_id in account_ids:
            for date in date_array:
                df = tiktok_service.request_report(
                    advertiser_id=advertiser_id,
                    start_date=date,
                    end_date=date,
                    dimensions=dimensions,
                    metrics=metrics,
                    level=level,
                    report_type=report_type,
                )
                df = df.astype(str)
                df["account_id"] = advertiser_id
                df["created_time"] = date
                df["created_time"] = pd.to_datetime(df["created_time"])
                lista_dfs.append(df)

        final_df = pd.concat(lista_dfs, ignore_index=True)
        final_df = format_columns(final_df)

        logger.success(f"{UUID} - Report created successfully")

        # # Authenticate in BigQuery
        bq = BigQuery(credentials_big_query, destination_project_id)
        list_of_account_in = "'" + "', '".join(account_ids) + "'"

        logger.info(
            f"Writing {final_df.shape[0]} rows to BigQuery on {destination_project_id}.{destination_table}"
        )

        # Export the data to BigQuery
        bq.export_with_date_range_and_filter(
            final_df,
            start_date=start_date,
            end_date=end_date,
            date_column="created_time",
            destination_table=destination_table,
            project_id=destination_project_id,
            filter_statement=f"account_id in ({list_of_account_in})",
        )

        logger.success("Successfully written to BigQuery")

        run_time = time.time() - start_time
        notification_summary["exec_time"] = round(run_time, 2)
        notification_summary["rows"] = final_df.shape[0]

        utils.send_message_to_chat(
            "success",
            webhook_url=notification_webhook_url,
            notification_summary=notification_summary,
        )
        return json.dumps({"success": True}), 200, {"Content-Type": "application/json"}

    except Exception as e:
        traceback.print_exc()
        notification_summary["custom_message"] = traceback.format_exc()
        utils.send_message_to_chat(
            "error",
            webhook_url=notification_webhook_url,
            notification_summary=notification_summary,
        )
        return json.dumps({"success": False}), 500, {"Content-Type": "application/json"}


# To test locally, use "functions-framework --target=main" instead of "python main"
class How_To_Request:
    def __init__(self):
        print("")

    def get_json(self):
        parameters = {
            "destination_project_id": "yduqs-estacio-prd",
            "destination_table": "raw.tb_tiktok_device",
            "secret_id": "",
            "secret_project_id": "76816773014",
            "bq_secret_id": "",
            "bq_secret_project": "76816773014",
            "account_ids": ["7010742212912791553"],
            "dimensions": ["device_brand_id", "campaign_id"],
            "level": "AUCTION_CAMPAIGN",
            "report_type": "AUDIENCE",
            "metrics": [
                "spend",
                "impressions",
                "clicks",
                "campaign_name",
                "device_brand_name",
            ],
            "start_date": "",
            "end_date": "",
            "reprocess_last_x_days": 14,
            "notification_webhook_url": "",
        }
        return parameters


if __name__ == "__main__":
    main(How_To_Request())
