from retry.api import retry_call
from loguru import logger
from google.oauth2.service_account import Credentials as SA_Credentials
from google.oauth2.credentials import Credentials as OAuth_Credentials
from ..GoogleDiscoveryAPI import GoogleDiscoveryAPI
from ..Utils.Utils import Utils


class DV360:
    def __init__(
        self,
        credentials: SA_Credentials | OAuth_Credentials,
        min_retry_interval: int = 30,
        max_retry_interval: int = 60,
        max_retry_count: int = 10,
    ):
        """Instantiates a class to interact with the DV360 API.

        Args:
            credentials (SA_Credentials | OAuth_Credentials): Google credentials to use to authenticate API requests.
            min_retry_interval (int, optional): Minimum retry interval, in seconds, when polling for the report status. Defaults to 30 seconds.
            max_retry_interval (int, optional):  Maximum retry interval, in seconds, when polling for the report status. Defaults to 1 minute.
            max_retry_count (int, optional): Maximum number of retries before considering unsuccessful. Defaults to 10.
        """
        self._SERVICE_API_NAME = "doubleclickbidmanager"
        self._SERVICE_API_VERSION = "v2"
        self._SERVICE_API_URL = "https://doubleclickbidmanager.googleapis.com/"
        self._SERVICE_API_SCOPES = [
            "https://www.googleapis.com/auth/doubleclickbidmanager"
        ]
        self.credentials = credentials
        self.service_client = GoogleDiscoveryAPI(
            credentials=credentials,
            api_url=self._SERVICE_API_URL,
            api_version=self._SERVICE_API_VERSION,
            api_name=self._SERVICE_API_NAME,
        ).get_service()
        self.min_retry_interval = min_retry_interval
        self.max_retry_interval = max_retry_interval
        self.max_retry_count = max_retry_count
        self.utils = Utils()

    def request_report(
        self,
        advertiser_ids: list,
        metrics: list,
        dimensions: list,
        start_date: str,
        end_date: str,
        file_name: str,
        directory_path: str,
        query_id: str = "",
    ):
        """Creates and runs a query and downloads the resulting report file.

        Args:
            advertiser_ids (list): The IDs of the advertisers for whom the report is being requested.
            metrics (list): A list of metrics to include in the report.
            dimensions (list): A list of dimensions to include in the report.
            start_date (str): The start date for the report in 'YYYY-MM-DD' format.
            end_date (str): The end date for the report in 'YYYY-MM-DD' format.
            file_name (str): Name that will be used for the downloaded report file.
            directory_path (str): Path that will be used for the downloaded report file.
            query_id (str): Query to use in report generation. If equals to "", a new query will be generated.

        Raises:
            RuntimeError: If report is not done generating after the maximum number
                of polling requests.
            HttpError: If an API request is not made successfully.

        """
        # Convert start and end dates to dictionary format.
        custom_start_date = self.utils.date_from_str_to_dict(start_date)
        custom_end_date = self.utils.date_from_str_to_dict(end_date)

        # Build list of advertiser id filter pairs.
        filters = []
        for advertiser_id in advertiser_ids:
            filters.append({"type": "FILTER_ADVERTISER", "value": advertiser_id})

        # Create a query object with basic dimension and metrics values.
        query_obj = {
            "metadata": {
                "title": file_name,
                "dataRange": {
                    "range": "CUSTOM_DATES",
                    "customStartDate": custom_start_date,
                    "customEndDate": custom_end_date,
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

        query_aux = query_id
        # Create query object.
        if not query_id:
            query_response = (
                self.service_client.queries().create(body=query_obj).execute()
            )
            logger.info(f'Query {query_response["queryId"]} was created.')
            query_aux = query_response["queryId"]

        # Log query creation.

        # Run query asynchronously.
        report_response = (
            self.service_client.queries()
            .run(queryId=query_aux, synchronous=False)
            .execute()
        )

        # Log information on running report.
        logger.info(
            f'Query {report_response["key"]["queryId"]} is running, report '
            f'{report_response["key"]["reportId"]} has been created and is '
            "currently being generated."
        )

        # Configure the queries.reports.get request.
        get_request = (
            self.service_client.queries()
            .reports()
            .get(
                queryId=report_response["key"]["queryId"],
                reportId=report_response["key"]["reportId"],
            )
        )

        # Get current status of operation with exponential backoff retry logic.
        report = retry_call(
            self.poll_report,
            fargs=[get_request],
            exceptions=RuntimeError,
            tries=self.max_retry_count,
            delay=self.min_retry_interval,
            max_delay=self.max_retry_interval,
            backoff=2,
        )

        if report["metadata"]["status"]["state"] == "FAILED":
            raise Exception(f'Report {report["key"]["reportId"]} finished with error.')

        logger.info(
            f'Report {report["key"]["reportId"]} generated successfully. Now '
            "downloading."
        )

        output_file = directory_path / f"{file_name}.csv"
        self.utils.make_dir(directory_path)
        # Download generated report file to the given output file.
        self.utils.download_from_gcs_url(
            report["metadata"]["googleCloudStoragePath"], output_file
        )

        return output_file

    def poll_report(sef, get_request):
        """Polls the given report and returns it if finished.

        Args:
            get_request: the Bid Manager API "queries.reports.get" request object.

        Returns:
            The finished report.

        Raises:
            RuntimeError: If report is not finished.
        """

        logger.info("Polling report...")

        # Get current status of operation.
        report = get_request.execute()

        # Check if report is done.
        if (
            report["metadata"]["status"]["state"] != "DONE"
            and report["metadata"]["status"]["state"] != "FAILED"
        ):
            raise RuntimeError("Report polling unsuccessful. Report is still running.")

        return report
