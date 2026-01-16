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
from cadastra_core import DV360
from cadastra_core import BigQuery
from cadastra_core import Utils

SECRET_MANAGER_PROJECT_ID = 76816773014

UUID = uuid.uuid4()


def transform_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Do some transformations to the DF.

    - Lowercases the column names.
    - Converts the 'Date' column to the correct format.
    - Transforms the ID columns to strings.

    Returns:
        DataFrame: The DataFrame containing the report data.
    """
    for column in df.columns:
        if "id" in column.lower():
            df[column] = df[column].astype(str).str.replace(".0", "")

    # Remove special characters from the column names and lowercase them
    df.columns = df.columns.str.replace("[ :;'\"()]", "_", regex=True)
    df.columns = df.columns.str.lower()

    df["date"] = pd.to_datetime(df["date"], format="%Y/%m/%d").dt.strftime("%Y-%m-%d")

    return df


def result_file_name(advertiser_ids: list):
    """
    Returns the name of the file that will contain the report data.
    """
    # Timestamp to be used in the report file name
    timestamp = int(datetime.now().timestamp())
    result_file_name = f"report_{timestamp}_{advertiser_ids[0]}"
    return result_file_name


def main(request):
    logger.info(f"{UUID} - Starting the process Display & Video 360")
    request_json = request.get_json()
    start_time = time.time()
    utils = Utils()
    notification_webhook_url: str = utils.get_parameter(
        json=request_json, parameter="notification_webhook_url"
    )

    notification_summary = {
        "function_name": utils.get_function_name() or "DV360",
    }

    try:
        secret_id: str = utils.get_parameter(json=request_json, parameter="secret_id")
        query_id: str = utils.get_parameter(json=request_json, parameter="query_id")
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
        advertiser_ids = utils.get_parameter(request_json, "advertiser_ids")
        dimensions = utils.get_parameter(request_json, "dimensions")
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
        notification_summary["account_id"] = ", ".join(advertiser_ids)

        # Get the credentials
        secret_manager = SecretManager()
        credentials_display_video = Credentials.from_authorized_user_info(
            json.loads(
                secret_manager.access_secret_version(secret_id, secret_project_id)
            )
        )
        credentials_big_query = SA_Credentials.from_service_account_info(
            json.loads(
                secret_manager.access_secret_version(bq_secret_id, bq_secret_project)
            )
        )

        # Authenticate in Display & Video 360
        dv360_service = DV360(credentials_display_video, max_retry_count=20)

        # Define the file name and directory path
        file_name = result_file_name(advertiser_ids)
        directory_path = Path.cwd() / "tmp"

        logger.info(f"{UUID} - Requesting the report")

        # Request the report
        report_file = dv360_service.request_report(
            advertiser_ids,
            metrics,
            dimensions,
            start_date,
            end_date,
            file_name,
            directory_path,
            query_id=query_id,
        )

        logger.success(f"{UUID} - Report downloaded successfully")

        df_to_transform = pd.read_csv(report_file, skipfooter=17, engine="python")

        # Transform the report into a DataFrame
        df_transformed = transform_df(df_to_transform)

        # Authenticate in BigQuery
        bq = BigQuery(credentials_big_query, destination_project_id)
        list_of_advertisers_in = "'" + "', '".join(advertiser_ids) + "'"

        logger.info(
            f"Writing {df_transformed.shape[0]} rows to BigQuery on {destination_project_id}.{destination_table}"
        )

        # Export the data to BigQuery
        bq.export_with_date_range_and_filter(
            df_transformed,
            start_date=start_date,
            end_date=end_date,
            date_column="date",
            destination_table=destination_table,
            project_id=destination_project_id,
            filter_statement=f"advertiser_id in ({list_of_advertisers_in})",
        )

        logger.success("Successfully written to BigQuery")

        run_time = time.time() - start_time
        notification_summary["exec_time"] = round(run_time, 2)
        notification_summary["rows"] = df_transformed.shape[0]

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
            "destination_table": "raw.tb_dv360_region",
            "secret_id": "",
            "secret_project_id": "76816773014",
            "bq_secret_id": "",
            "bq_secret_project": "76816773014",
            "advertiser_ids": ["1070390302"],
            "query_id": "",
            "dimensions": [
                "FILTER_DATE",
                "FILTER_ADVERTISER",
                "FILTER_MEDIA_PLAN",
                "FILTER_MEDIA_PLAN_NAME",
                "FILTER_CITY_NAME",
                "FILTER_REGION_NAME",
                "FILTER_INSERTION_ORDER_NAME",
                "FILTER_INSERTION_ORDER",
                "FILTER_ADVERTISER_CURRENCY",
                "FILTER_LINE_ITEM_NAME",
            ],
            "metrics": [
                "METRIC_IMPRESSIONS",
                "METRIC_CLICKS",
                "METRIC_REVENUE_ADVERTISER",
                "METRIC_MEDIA_COST_ADVERTISER",
            ],
            "start_date": "2023-11-12",
            "end_date": "2024-01-01",
            "reprocess_last_x_days": 0,
            "notification_webhook_url": "",
        }
        return parameters


if __name__ == "__main__":
    main(How_To_Request())
