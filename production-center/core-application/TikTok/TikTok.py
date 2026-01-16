import requests
import pandas as pd
from datetime import datetime
from datetime import timedelta
from loguru import logger
import sys


class TikTok:
    def __init__(
        self, access_token: str, api_version: str = "v1.2", debug_messages: bool = False
    ):
        self.access_token = access_token
        self.debug_messages = debug_messages
        self.api_version = api_version
        if self.api_version == "v1.2":
            self.base_url = (
                f"https://business-api.tiktok.com/open_api/v1.2/reports/integrated/get/"
            )
        elif self.api_version == "v1.3":
            self.base_url = (
                f"https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"
            )
        else:
            logger.error("This version of api does not exist, please use v1.2 or v1.3")

        logger.remove()
        log_level = "DEBUG" if self.debug_messages else "INFO"
        logger.add(sys.stdout, level=log_level)

    def check_auth(self) -> bool:
        """This functions checks if an access token is valid

        Returns:
            bool: True if authentication was successful, False otherwise
        """
        headers = {
            "access_token": self.access_token,
        }
        response = requests.post(
            "https://business-api.tiktok.com/open_api/v1.2/oauth2/access_token/",
            headers=headers,
        )

        if response.status_code == 200:
            logger.success("Authentication successful!")
            return True

        logger.error("Authentication failed")
        return False

    def __params(
        self,
        dimensions: list[str],
        metrics: list[str],
        advertiser_id: str,
        start_date: str,
        end_date: str,
        data_level: str,
        report_type: str,
    ) -> dict:
        params = {
            "advertiser_id": advertiser_id,
            "page_size": 1000,
            "report_type": report_type,
            "lifetime": "false",
            "query_lifetime": "false",
            "data_level": data_level,
            "dimensions": dimensions,
            "metrics": metrics,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "page": 1,
        }
        return params

    def request_report(
        self,
        advertiser_id: str,
        start_date: str,
        end_date: str,
        dimensions: list[str],
        metrics: list[str],
        level: str = "AUCTION_AD",
        report_type: str = "BASIC",
    ) -> pd.DataFrame:
        """Method to extract a data report from TikTok and return a Pandas Dataframe with the requested data.

        Args:
            advertiser_id (str): The tiktok advertiser ID to extract data from
            start_date (str): Start date in format 'YYYY-MM-DD'
            end_date (str): End date in format 'YYYY-MM-DD'
            dimensions (list[str]): List with dimensions to retrive, like ["ad_id", "stat_time_day"]
            metrics (list[str]): List with metrics to retrive, like ["ad_name", "spend", "impressions"]
            level (str, optional): Level of granularity of the data returned in the API response. Options for data_level: AUCTION_CAMPAIGN, AUCTION_ADGROUP, AUCTION_AD or AUCTION_ADVERTISER
            report_type (str, optional): The type of report. Examples: BASIC, AUDIENCE.

        Raises:
            Exception: if the API request returns a code different from 200

        Returns:
            pd.DataFrame: the Pandas Dataframe with the data
        """

        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

        response_list = []
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        while start <= end:
            current_end = start + timedelta(days=29)

            if current_end > end:
                current_end = end

            params = self.__params(
                dimensions,
                metrics,
                advertiser_id,
                start,
                current_end,
                level,
                report_type,
            )

            response = requests.get(self.base_url, headers=headers, json=params)
            if response.status_code == 200:
                response_json = response.json()

                if not response_json.get("data"):
                    logger.info(f"No data for advertiser_id: {advertiser_id}")
                    logger.info(response_json.get("message"))
                    return pd.DataFrame([])

                response_list.append(response_json)
                logger.debug(
                    f"Reading page {response_json.get('data',{}).get('page_info')}"
                )

                while response_json.get("data", {}).get("page_info", {}).get(
                    "page"
                ) < response_json.get("data", {}).get("page_info", {}).get(
                    "total_page"
                ):
                    params["page"] += 1
                    response = requests.get(self.base_url, headers=headers, json=params)
                    response_json = response.json()
                    if not response_json.get("data"):
                        logger.error("Error inside paging!!")
                    response_list.append(response_json)
                    logger.debug(
                        f"Reading page {response_json.get('data',{}).get('page_info')}"
                    )

            else:
                logger.error(f"Error!! Message: {response.json()}")
                raise Exception(
                    f"Error in searching data for advertiser_id: {advertiser_id}"
                )

            start = current_end + timedelta(days=1)

        # Extracting data from responses
        logger.debug("Extracting data from responses")
        df_data = []
        for response in response_list:
            list_data = response.get("data", {}).get("list")
            for item in list_data:
                row = {}
                dimensions_data = item.get("dimensions", {})
                row.update(dimensions_data)
                metrics_data = item.get("metrics", {})
                row.update(metrics_data)
                df_data.append(row)

        self.df = pd.DataFrame(df_data)
        self.df = self.df.astype(str)

        # Add Datetime
        self.df["date_loading"] = datetime.now()

        logger.success("Success in creating the dataframe")

        return self.df
