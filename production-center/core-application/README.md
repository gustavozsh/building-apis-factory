<!-- omit from toc -->
# Google Ads Module

This Python module allows you to extract data using predefined methods, run custom queries, retrieve accessible customers and client IDs, and request reports with specified fields and parameters from Google Ads.

<!-- omit from toc -->
## Table of Contents
- [Usage \& Examples](#usage--examples)
  - [Initialization](#initialization)
  - [Requesting a Report](#requesting-a-report)
  - [Retrieve Accessible Client\_ids](#retrieve-accessible-client_ids)
- [Methods](#methods)
  - [request\_report -\> pd.DataFrame](#request_report---pddataframe)
  - [send\_request -\> Iterator\[SearchGoogleAdsResponse\]](#send_request---iteratorsearchgoogleadsresponse)
  - [send\_request\_pandas -\> pd.DataFrame](#send_request_pandas---pddataframe)
  - [get\_accessible\_customers -\> list\[dict\[str, str\]\]](#get_accessible_customers---listdictstr-str)
  - [get\_accessible\_client\_ids -\> list\[dict\[str, Union\[int, str\]\]\]](#get_accessible_client_ids---listdictstr-unionint-str)
  - [convert\_schema\_into\_query -\> str](#convert_schema_into_query---str)
  - [parse\_single\_result -\> dict\[str, Any\]](#parse_single_result---dictstr-any)
- [Metrics and Dimensions](#metrics-and-dimensions)
- [Building Your Own Queries](#building-your-own-queries)


## Usage & Examples
### Initialization
Here's an example using Secret Manager:
```python

from cadastra_core import SecretManager
from cadastra_core import GoogleAds

secret_manager = SecretManager()
secret_id = "your-secret-id"
project_id = "your-project-id"
version_id = "latest"  # Optional, defaults to "latest"

secret_value = secret_manager.access_secret_version(
    secret_id=secret_id,
    project_id=project_id,
    version_id=version_id
)

credentials_dict: dict = json.loads(
    secret_value
)
google_ads_credentials = {
    "developer_token": credentials_dict.get("developer_token"),
    "refresh_token": credentials_dict.get("refresh_token"),
    "client_id": credentials_dict.get("client_id"),
    "client_secret": credentials_dict.get("client_secret"),
    "login_customer_id": login_customer_id,
}

# Instantiate Google Ads Class
google_ads = GoogleAds(google_ads_credentials)
```

### Requesting a Report
You can request data by using the `request_report` method or `send_request`/`send_request_pandas`
```python

# Define the fields and parameters for the report
fields = [
    "campaign.id",
    "campaign.name",
    "metrics.impressions",
    "metrics.clicks",
    "metrics.conversions",
    "metrics.cost_micros",
    "segments.date",
    "campaign_group.resource_name",
    "customer.id",
]
table_name = "campaign"
account_id = "your_client_id"
start_date = "2024-01-01"
end_date = "2024-12-31"

# Request the report and store the results in a DataFrame
df = google_ads.request_report(
    fields=fields,
    table_name=table_name,
    account_id=account_id,
    start_date=start_date,
    end_date=end_date,
)

# View the resulting DataFrame
print(df)

# Define the query
query = """
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
"""
account_id = "your_client_id"

# Request the report and store the results in a DataFrame
df = google_ads.send_request_pandas(query, customer_id)

# View the resulting DataFrame
print(df)
```
### Retrieve Accessible Client_ids

```python

# Get the IDs of accessible customers
client_ids = google_ads.get_accessible_client_ids("your_customer_id")
print(accessible_customers)

```

## Methods
### request_report -> pd.DataFrame

| Parameter name | Type | Required | Description | Default value |
|---|---|---|---|---|
| `fields` | list[str] | :white_check_mark: | List of fields to be selected in the query |  |
| `table_name` | str | :white_check_mark: | Name of the table from which data will be selected |  |
| `conditions` | list[str] | | List of conditions to be applied in the WHERE clause | `None` |
| `order_field` | str | | Field by which the results should be ordered | `None` |
| `limit` | int | | Maximum number of results to be returned | `None` |
| `account_id` | str | :white_check_mark: | The customer ID for which the query will be executed |  |
| `start_date` | str | | Start date for the query in format 'YYYY-MM-DD' | `None` |
| `end_date` | str | | End date for the query in format 'YYYY-MM-DD' | `None` |

### send_request -> Iterator[SearchGoogleAdsResponse]

| Parameter name | Type | Required | Description | Default value |
|---|---|---|---|---|
| `query` | str | :white_check_mark: | The query to be executed |  |
| `customer_id` | str | :white_check_mark: | The customer ID for which the query will be executed |  |

### send_request_pandas -> pd.DataFrame

| Parameter name | Type | Required | Description | Default value |
|---|---|---|---|---|
| `query` | str | :white_check_mark: | The query to be executed |  |
| `customer_id` | str | :white_check_mark: | The customer ID for which the query will be executed |  |

### get_accessible_customers -> list[dict[str, str]]

| Parameter name | Type | Required | Description | Default value |
|---|---|---|---|---|
| None | - | - | This method does not take any parameters | - |

### get_accessible_client_ids -> list[dict[str, Union[int, str]]]

| Parameter name | Type | Required | Description | Default value |
|---|---|---|---|---|
| `customer_id` | str | :white_check_mark: | The customer ID for which the query will be executed |  |

### convert_schema_into_query -> str

| Parameter name | Type | Required | Description | Default value |
|---|---|---|---|---|
| `fields` | list[str] | :white_check_mark: | List of fields to be selected in the query |  |
| `table_name` | str | :white_check_mark: | Name of the table from which data will be selected |  |
| `conditions` | list[str] | | List of conditions to be applied in the WHERE clause | `None` |
| `order_field` | str | | Field by which the results should be ordered | `None` |
| `limit` | int | | Maximum number of results to be returned | `None` |
| `start_date` | str | | Start date for the query in format 'YYYY-MM-DD' | `None` |
| `end_date` | str | | End date for the query in format 'YYYY-MM-DD' | `None` |

### parse_single_result -> dict[str, Any]

| Parameter name | Type | Required | Description | Default value |
|---|---|---|---|---|
| `schema` | dict[str, Any] | :white_check_mark: | The schema defining the structure of the result |  |
| `result` | GoogleAdsRow | :white_check_mark: | A single row from the Google Ads API response |  |


## Metrics and Dimensions

For a complete list of available metrics, dimensions, and their respective tables/resources, refer to the [Google Ads API Fields](https://developers.google.com/google-ads/api/fields).


## Building Your Own Queries

If you prefer to build your own queries and use the `send_request` method directly instead of `request_report`, you can refer to the following documentation for detailed information on constructing and validating queries:

- [Google Ads Query Language (GAQL) documentation](https://developers.google.com/google-ads/api/docs/query/overview)
- [Google Ads Query Builder](https://developers.google.com/google-ads/api/fields/v17/overview_query_builder)
- [Google Ads Query Validator](https://developers.google.com/google-ads/api/fields/v17/query_validator)