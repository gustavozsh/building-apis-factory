from enum import Enum
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Union
import pandas as pd
from loguru import logger
from proto.marshal.collections import Repeated, RepeatedComposite

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v20.services.types.google_ads_service import (
    GoogleAdsRow,
    SearchGoogleAdsResponse,
)
from google.api_core.exceptions import InternalServerError, ServerError, TooManyRequests
from google.auth import exceptions
from google.protobuf.json_format import MessageToDict
from ..Utils.Utils import Utils


class GoogleAds:

    def __init__(self, credentials: MutableMapping[str, Any]):
        """
        Initializes the GoogleAds client with the provided credentials.

        Args:
            credentials (MutableMapping[str, Any]): A dictionary containing the credentials for Google Ads API authentication.
                Example:
                    credentials = {
                        "developer_token": "YOUR_DEVELOPER_TOKEN",
                        "refresh_token": "YOUR_REFRESH_TOKEN",
                        "client_id": "YOUR_CLIENT_ID",
                        "client_secret": "YOUR_CLIENT_SECRET",
                        "login_customer_id": "YOUR_LOGIN_CUSTOMER_ID",
                    }

        Attributes:
            credentials (MutableMapping[str, Any]): The credentials dictionary.
            client (GoogleAdsClient): The Google Ads client initialized with the provided credentials.
            ga_service (GoogleAdsService): The Google Ads service client.
            customer_service (CustomerService): The Customer service client.
        """
        # `google-ads` library version `14.0.0` and higher requires an additional required parameter `use_proto_plus`.
        # More details can be found here: https://developers.google.com/google-ads/api/docs/client-libs/python/protobuf-messages
        credentials["use_proto_plus"] = "false"
        self.credentials = credentials
        self._API_VERSION = "v20"
        self.client = self.get_google_ads_client(credentials)
        self.ga_service = self.client.get_service(
            "GoogleAdsService", version=self._API_VERSION
        )
        self.customer_service = self.client.get_service(
            "CustomerService", version=self._API_VERSION
        )
        self.utils_client = Utils()

    @staticmethod
    def get_google_ads_client(credentials) -> GoogleAdsClient:
        """
        Creates and returns a GoogleAdsClient instance using the provided credentials.

        Args:
            credentials (MutableMapping[str, Any]): A dictionary containing the credentials required to authenticate with the Google Ads API.

        Raises:
            exceptions.RefreshError: If the authentication to Google Ads has expired and needs to be refreshed.

        Returns:
            GoogleAdsClient: An instance of GoogleAdsClient authenticated with the provided credentials.
        """

        try:
            return GoogleAdsClient.load_from_dict(credentials)
        except exceptions.RefreshError as e:
            message = "The authentication to Google Ads has expired. Re-authenticate to restore access to Google Ads."
            logger.error(message)
            raise e

    def get_accessible_customers(self) -> List[Dict[str, str]]:
        """
        Retrieves a list of accessible customer.

        This method fetches the list of accessible customer from the Google Ads API
        and returns them as a list of dictionaries, each containing a customer ID.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing a customer ID of an accessible account.
        """
        customer_resource_names = (
            self.customer_service.list_accessible_customers().resource_names
        )
        logger.info(
            f"Found {len(customer_resource_names)} accessible customers: {customer_resource_names}"
        )

        accessible_accounts = []
        for customer_resource_name in customer_resource_names:
            customer_id = self.ga_service.parse_customer_path(customer_resource_name)[
                "customer_id"
            ]
            accessible_accounts.append({"customer_id": customer_id})

        return accessible_accounts

    def send_request(
        self, query: str, customer_id: str
    ) -> Iterator[SearchGoogleAdsResponse]:
        """
        Sends a request to the Google Ads API using the provided query and customer ID.

        Args:
            query (str): The query to be executed.
            customer_id (str): The customer ID for which the query will be executed.
            login_customer_id (str, optional): The login customer ID to be used for the request. Defaults to None.

        Returns:
            Iterator[SearchGoogleAdsResponse]: An iterator over the search responses.
        """
        try:
            logger.info(f"Creating a search request for customer ID: {customer_id}")

            search_request = self.client.get_type("SearchGoogleAdsRequest")
            search_request.query = query
            search_request.customer_id = customer_id

            logger.info(f"Sending the search request")
            # Execute the search request
            response = self.ga_service.search(request=search_request)

            return response

        except GoogleAdsException as ex:
            logger.error(
                f"Request failed with GoogleAdsException: {ex.error.code().name}"
            )
            for error in ex.failure.errors:
                logger.error(f"Error with message: {error.message}")
                if error.location:
                    for field_path_element in error.location.field_path_elements:
                        logger.error(f"On field: {field_path_element.field_name}")
            raise ex

        except InternalServerError as ex:
            logger.error(f"Internal server error: {ex.message}")
            raise ex

        except ServerError as ex:
            logger.error(f"Server error: {ex.message}")
            raise ex

        except TooManyRequests as ex:
            logger.error(f"Too many requests error: {ex.message}")
            raise ex

        except Exception as ex:
            logger.error(f"An unexpected error occurred: {ex}")
            raise ex

    def send_request_pandas(self, query: str, customer_id: str) -> pd.DataFrame:
        """
        Sends a request to the Google Ads API using the provided query and customer ID and return a Pandas Dataframe. Optionally makes requests individually by day instead of full range.

        Args:
            query (str): The query to be executed.
            customer_id (str): The customer ID for which the query will be executed.
            start_date (str): Date range start date.
            end_date (str): Date range end date.
            break_into_daily_requests (bool, Optional): True to break a date range into multiple requests by day or False to make to use the full date range in a single request. Defaults to True.

        Returns:
            pd.DataFrame: A Pandas Dataframe with the requested query results.
        """
        try:
            logger.info(f"Creating a search request for customer ID: {customer_id}")
            rows_list = list()

            logger.info(f"Sending search request")
            # Execute the search request
            response_stream = self.ga_service.search_stream(
                customer_id=customer_id, query=query
            )
            for batch in response_stream:
                for row in batch.results:
                    row_json = MessageToDict(row)
                    rows_list.append(row_json)

            df_final = pd.json_normalize(rows_list)

            if df_final is None:
                error_message = f"No data returned from query"
                logger.warning(error_message)
                return None

            df_final = df_final.rename(
                columns=lambda column: self.utils_client.camel_to_snake(
                    column.replace(".", "_")
                )
            )

            return df_final

        except GoogleAdsException as ex:
            logger.error(
                f"Request failed with GoogleAdsException: {ex.error.code().name}"
            )
            for error in ex.failure.errors:
                logger.error(f"Error with message: {error.message}")
                if error.location:
                    for field_path_element in error.location.field_path_elements:
                        logger.error(f"On field: {field_path_element.field_name}")
            raise ex

        except InternalServerError as ex:
            logger.error(f"Internal server error: {ex.message}")
            raise ex

        except ServerError as ex:
            logger.error(f"Server error: {ex.message}")
            raise ex

        except TooManyRequests as ex:
            logger.error(f"Too many requests error: {ex.message}")
            raise ex

        except Exception as ex:
            logger.error(f"An unexpected error occurred: {ex}")
            raise ex

    @staticmethod
    def get_fields_from_schema(schema: Mapping[str, Any]) -> List[str]:
        properties = schema.get("properties")
        return list(properties.keys())

    @staticmethod
    def convert_schema_into_query(
        fields: Iterable[str],
        table_name: str,
        conditions: List[str] = None,
        order_field: str = None,
        limit: int = None,
        start_date: str = None,
        end_date: str = None,
    ) -> str:
        """
        Constructs a Google Ads query based on the provided parameters.

        Args:
        - fields (Iterable[str]): List of fields to be selected in the query.
        - table_name (str): Name of the table from which data will be selected.
        - conditions (List[str], optional): List of conditions to be applied in the WHERE clause. Each condition must be in a format accepted by the Google Ads query language. Defaults to None.
        - order_field (str, optional): Field by which the results should be ordered. Defaults to None.
        - limit (int, optional): Maximum number of results to be returned. Defaults to None.

        Returns:
        - str: Constructed Google Ads query.
        """

        query_template = f"SELECT {', '.join(fields)} FROM {table_name}"

        where_clauses = []

        if conditions:
            where_clauses.extend(conditions)

        if start_date and end_date:
            where_clauses.append(
                f"segments.date >= '{start_date}' AND segments.date <= '{end_date}'"
            )

        if where_clauses:
            query_template += " WHERE " + " AND ".join(where_clauses)

        if order_field:
            query_template += f" ORDER BY {order_field} ASC"

        if limit:
            query_template += f" LIMIT {limit}"

        return query_template

    @staticmethod
    def __get_field_value(
        field_value: GoogleAdsRow, field: str, schema_type: Mapping[str, Any]
    ) -> str:
        field_name = field.split(".")
        for level_attr in field_name:
            """
            We have an object of the GoogleAdsRow class, and in order to get all the attributes we requested,
            we should alternately go through the nestings according to the path that we have in the field_name variable.

            For example 'field_value' looks like:
            customer {
              resource_name: "customers/4186739445"
              ...
            }
            campaign {
              resource_name: "customers/4186739445/campaigns/8765465473658"
              ....
            }
            ad_group {
              resource_name: "customers/4186739445/adGroups/2345266867978"
              ....
            }
            metrics {
              clicks: 0
              ...
            }
            ad_group_ad {
              resource_name: "customers/4186739445/adGroupAds/2345266867978~46437453679869"
              status: ENABLED
              ad {
                type_: RESPONSIVE_SEARCH_AD
                id: 46437453679869
                ....
              }
              policy_summary {
                approval_status: APPROVED
              }
            }
            segments {
              ad_network_type: SEARCH_PARTNERS
              ...
            }
            """

            try:
                field_value = getattr(field_value, level_attr)
            except AttributeError:
                # In GoogleAdsRow there are attributes that add an underscore at the end in their name.
                # For example, 'ad_group_ad.ad.type' is replaced by 'ad_group_ad.ad.type_'.
                field_value = getattr(field_value, level_attr + "_", None)
            if isinstance(field_value, Enum):
                field_value = field_value.name
            elif isinstance(field_value, (Repeated, RepeatedComposite)):
                field_value = [str(value) for value in field_value]

        # Google Ads has a lot of entities inside itself, and we cannot process them all separately, because:
        # 1. It will take a long time
        # 2. We have no way to get data on absolutely all entities to test.
        #
        # To prevent JSON from throwing an error during deserialization, we made such a hack.
        # For example:
        # 1. ad_group_ad.ad.responsive_display_ad.long_headline - type AdTextAsset
        # (https://developers.google.com/google-ads/api/reference/rpc/v6/AdTextAsset?hl=en).
        # 2. ad_group_ad.ad.legacy_app_install_ad - type LegacyAppInstallAdInfo
        # (https://developers.google.com/google-ads/api/reference/rpc/v7/LegacyAppInstallAdInfo?hl=en).
        if (
            not isinstance(field_value, (list, int, float, str, bool, dict))
            and field_value is not None
        ):
            field_value = str(field_value)

        return field_value

    @staticmethod
    def parse_single_result(
        schema: Mapping[str, Any], result: GoogleAdsRow
    ) -> Dict[str, Any]:
        """
        Parses a single result from the Google Ads API response.

        Args:
            schema (Mapping[str, Any]): The schema defining the structure of the result.
            result (GoogleAdsRow): A single row from the Google Ads API response.

        Returns:
            Dict[str, Any]: A dictionary representing the parsed result, with field names as keys and their corresponding values.

        Example:
            schema = {"properties": {field: {} for field in fields}}

            for result in response:
                parsed_result = self.parse_single_result(schema, result)
                results.append(parsed_result)
        """

        props = schema.get("properties")
        fields = GoogleAds.get_fields_from_schema(schema)
        single_record = {
            field: GoogleAds.__get_field_value(result, field, props.get(field))
            for field in fields
        }
        return single_record

    def request_report(
        self,
        fields: List[str],
        table_name: str,
        account_id: str,
        conditions: List[str] = None,
        order_field: str = None,
        limit: int = None,
        start_date: str = None,
        end_date: str = None,
    ) -> pd.DataFrame:
        """
        Requests a report from the Google Ads API and returns the results as a DataFrame.

        Args:
            fields (List[str]): List of fields to be selected in the query.
            table_name (str): Name of the table from which data will be selected.
            account_id (str): The client ID for which the query will be executed.
            conditions (List[str], optional): List of conditions to be applied in the WHERE clause. Defaults to None.
            order_field (str, optional): Field by which the results should be ordered. Defaults to None.
            limit (int, optional): Maximum number of results to be returned. Defaults to None.
            start_date (str, optional): Start date for the query. Defaults to None.
            end_date (str, optional): End date for the query. Defaults to None.

        Returns:
            pd.DataFrame: A DataFrame containing the results of the query.
        """
        # Constructing query
        query = self.convert_schema_into_query(
            fields=fields,
            table_name=table_name,
            conditions=conditions,
            order_field=order_field,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )
        logger.info(f"Constructed Query: {query}")

        # Send request
        response = self.send_request(query, account_id)
        logger.info(f"Received response, processing results")

        results = []
        schema = {"properties": {field: {} for field in fields}}

        for result in response:
            parsed_result = self.parse_single_result(schema, result)
            results.append(parsed_result)

        # Converting results to DataFrame
        df = pd.DataFrame(results)

        logger.success(f"Processed {len(df)} results")

        return df

    def get_accessible_client_ids(
        self, customer_id
    ) -> List[Dict[str, Union[int, str]]]:
        """
        Retrieves client IDs along with their descriptive names and currency codes.

        This method sends a query to the Google Ads API to fetch client IDs, descriptive names,
        and currency codes. The results are parsed and returned
        as a list of dictionaries.

        Args:
            customer_id (str): The customer ID for which the query will be executed.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each dictionary contains:
                - 'customer_client.id': The client ID.
                - 'customer_client.descriptive_name': The descriptive name of the client.
                - 'customer_client.currency_code': The currency code of the client.
        """
        table_name = "customer_client"
        fields = [
            "customer_client.id",
            "customer_client.descriptive_name",
            "customer_client.currency_code",
        ]

        query = self.convert_schema_into_query(
            fields=fields,
            table_name=table_name,
        )

        logger.info(f"Constructed Query: {query}")

        logger.info(f"Requesting client IDs")
        response = self.send_request(query, customer_id)
        results = []
        schema = {"properties": {field: {} for field in fields}}

        for result in response:
            parsed_result = self.parse_single_result(schema, result)
            results.append(parsed_result)

        return results
