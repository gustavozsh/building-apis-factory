from loguru import logger
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as SA_Credentials
from cadastra_core import GoogleAds
from cadastra_core import SecretManager
from cadastra_core import BigQuery
from cadastra_core import Utils
import traceback
import json
import re
import functions_framework
import time


@functions_framework.http
def main(request):
    logger.info("Initializing Google Ads Extraction")
    request_json: dict = request.get_json()
    start_time = time.time()
    utils = Utils()

    notification_webhook_url: str = utils.get_parameter(
        json=request_json, parameter="notification_webhook_url"
    )

    notification_summary = {
        "function_name": utils.get_function_name() or "Google Ads",
    }

    try:
        # Request params
        logger.info("Reading parameters")
        customer_id: int = utils.get_parameter(
            json=request_json, parameter="customer_id"
        )
        login_customer_id: int = utils.get_parameter(
            json=request_json, parameter="login_customer_id"
        )
        query: str = utils.get_parameter(json=request_json, parameter="query")
        secret_id: str = utils.get_parameter(json=request_json, parameter="secret_id")
        secret_project_id: str = utils.get_parameter(
            json=request_json, parameter="secret_project_id"
        )
        bq_secret_id: str = utils.get_parameter(
            json=request_json, parameter="bq_secret_id"
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

        if (start_date or end_date) and reprocess_last_x_days:
            raise Exception(
                "If using start_date/end_date, you should set 'reprocess_last_x_days' to 0"
            )

        if reprocess_last_x_days > 0:
            end_date = utils.get_yesterday()
            start_date = utils.get_last_x_days(reprocess_last_x_days)

        # Credentials
        secret_manager = SecretManager()

        credentials_dict: dict = json.loads(
            secret_manager.access_secret_version(secret_id, secret_project_id)
        )
        google_ads_credentials = {
            "developer_token": credentials_dict.get("developer_token"),
            "refresh_token": credentials_dict.get("refresh_token"),
            "client_id": credentials_dict.get("client_id"),
            "client_secret": credentials_dict.get("client_secret"),
            "login_customer_id": login_customer_id,
        }

        bigquery_dict: dict = json.loads(
            secret_manager.access_secret_version(bq_secret_id, secret_project_id)
        )

        bigquery_credentials: Credentials = SA_Credentials.from_service_account_info(
            bigquery_dict
        )

        destination_gcp_project = (
            utils.get_current_gcp_project()
            if destination_project_id is None
            else destination_project_id
        )

        notification_summary["date_range"] = [start_date, end_date]
        notification_summary["destination_table"] = (
            f"{destination_gcp_project}.{destination_table}"
        )
        notification_summary["account_id"] = customer_id

        logger.info(f"Getting data from {start_date} to {end_date}")

        google_ads_client = GoogleAds(google_ads_credentials)

        where_or_and_clause = "AND" if re.match("WHERE", query) else "WHERE"
        query_with_date = (
            query
            + f"\n{where_or_and_clause} segments.date BETWEEN '{start_date}' AND '{end_date}'"
        )

        df_query = google_ads_client.send_request_pandas(query_with_date, customer_id)
        if df_query is None or df_query.shape[0] == 0:
            run_time = time.time() - start_time
            notification_summary["exec_time"] = round(run_time, 2)
            notification_summary["custom_message"] = (
                "Execution successful but query returned no results"
            )
            logger.warning(notification_summary["custom_message"])
            utils.send_message_to_chat(
                "warning",
                webhook_url=notification_webhook_url,
                notification_summary=notification_summary,
            )
            return (
                json.dumps({"success": False}),
                500,
                {"Content-Type": "application/json"},
            )

        logger.success("Query ran successfully")

        logger.info(
            f"Writing {df_query.shape[0]} rows to BigQuery on {destination_gcp_project}.{destination_table}"
        )
        bigquery = BigQuery(bigquery_credentials, destination_gcp_project)

        df_query.columns = df_query.columns.str.replace(".", "_")
        bigquery.export_with_date_range_and_filter(
            df_query,
            start_date=start_date,
            end_date=end_date,
            date_column="segments_date",
            destination_table=destination_table,
            project_id=destination_gcp_project,
            filter_statement=f"customer_id = '{customer_id}'",
        )

        run_time = time.time() - start_time

        notification_summary["exec_time"] = round(run_time, 2)
        notification_summary["rows"] = df_query.shape[0]

        utils.send_message_to_chat(
            "success",
            webhook_url=notification_webhook_url,
            notification_summary=notification_summary,
        )
        return json.dumps({"success": True}), 200, {"Content-Type": "application/json"}
    except Exception:  # pylint: disable=broad-except
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
    def __init__(self, table, customer_id):
        self.table = table
        self.customer_id = customer_id
        self.query_dict = {
            "impression_share": """
                SELECT
                    segments.date
                    , campaign.name
                    , campaign.id
                    , segments.device
                    , metrics.clicks
                    , metrics.cost_micros
                    , metrics.impressions
                    , metrics.absolute_top_impression_percentage
                    , customer.id
                FROM campaign
            """,
            "device": """
                SELECT
                    segments.date
                    , campaign.name
                    , campaign.id
                    , segments.device
                    , metrics.clicks
                    , metrics.cost_micros
                    , metrics.impressions
                    , customer.id
                FROM campaign
            """,
            "region": """
                SELECT
                    segments.date
                    , campaign.name
                    , campaign.id
                    , segments.geo_target_region
                    , segments.geo_target_city
                    , metrics.clicks
                    , metrics.cost_micros
                    , metrics.impressions
                    , customer.id
                FROM geographic_view
            """,
        }

        self.destination_table_dict = {
            "impression_share": "raw.tb_google_ads_impression_share",
            "device": "raw.tb_google_ads_device",
            "region": "raw.tb_google_ads_region",
        }

    def get_json(self):
        parameters = {
            "query": self.query_dict[self.table],
            "customer_id": self.customer_id,
            "login_customer_id": "4693364974",
            "secret_id": "",
            "secret_project_id": "76816773014",
            "bq_secret_id": "",
            "start_date": "2024-08-01",
            "end_date": "2024-08-31",
            "destination_table": self.destination_table_dict[self.table],
            "destination_project_id": "yduqs-estacio-prd",
            "notification_webhook_url": "",
        }
        return parameters


if __name__ == "__main__":
    """
    '3284036835'
    '1490507278'
    '1780338927'
    """
    table_to_extract = "region"
    customer_ids = ["3284036835", "1490507278", "1780338927"]

    for customer_id in customer_ids:
        main(How_To_Request(table_to_extract, customer_id))
