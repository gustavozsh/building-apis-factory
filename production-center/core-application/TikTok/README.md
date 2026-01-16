<!-- omit from toc -->
# TikTok Module

This Python module allows you to extract data from TikTok. The data is returned as a Pandas DataFrame, making it easy to work with in a variety of data processing and analysis workflows.

<!-- omit from toc -->
## Table of contents
- [Usage \& Examples](#usage--examples)
  - [Initialization](#initialization)
  - [Examples](#examples)
- [Methods](#methods)
  - [request\_report -\> pd.DataFrame](#request_report---pddataframe)


## Usage & Examples
### Initialization
To use the TikTok class, you need to provide an access_token. You can retrieve this credential using Secret Manager.

Here's an example using Secret Manager:
```

from cadastra_core import SecretManager
from cadastra_core import TikTok

secret_manager = SecretManager()
secret_id = "your-secret-id"
project_id = "your-project-id"
version_id = "latest"  # Optional, defaults to "latest"

secret_value = secret_manager.access_secret_version(
    secret_id=secret_id,
    project_id=project_id,
    version_id=version_id
)

secret_value = json.loads(secret_value) # In case it's a JSON token


# Initialize credential
access_token = secret_value["access_token"]

# Instantiate the TikTok class
tiktok = TikTok(access_token)

```
### Examples

#### Checking authorization
You can check if the authorization is correct and if the API request returns data properly by using the 'check_auth' function. 

```
# If authenticated is False, the AssertionError will be raised with the message 'Authorization Failed'
assert tiktok.check_auth(), "Authorization Failed"

```


#### Requesting a Report
You can request a report by calling the `request_report` method. This method retrieves the desired data from TikTok and returns it as a Pandas DataFrame. 

```
# Define parameters
advertiser_id = "YOUR_TIKTOK_AD_ID"
start_date = '2024-05-01'
end_date = '2024-05-31'
dimensions = ["ad_id", "stat_time_day"]
level = "AUCTION_AD"
metrics = ["ad_name", "spend", "impressions"]

# Request the report
df = tiktok.request_report(
  advertiser_id=advertiser_id, 
  start_date=start_date, 
  end_date=end_date,
  dimensions=dimensions,
  metrics=metrics,
  level=level
  )

# View the resulting DataFrame
print(df)
```
## Methods
### request_report -> pd.DataFrame
| Parameter Name | Type | Required | Description | Default Value |
|---|---|---|---|---|
| advertiser_id | str | :white_check_mark: | The TikTok advertiser ID to extract data from | - |
| start_date | str | :white_check_mark: | Start date in format 'YYYY-MM-DD' | - |
| end_date | str | :white_check_mark: | End date in format 'YYYY-MM-DD' | - |
| dimensions | list[str] | :white_check_mark: | List of dimensions to retrieve, like ["ad_id", "campaign_name"]  | - |
| metrics | list[str] | :white_check_mark: | List of metrics to retrieve, like ["impressions", "clicks", "spend"] | - |
| level (optional) | str | | Level of granularity for data. Options: `AUCTION_CAMPAIGN`, `AUCTION_ADGROUP`, `AUCTION_AD` (default), `AUCTION_ADVERTISER` | `AUCTION_AD` |
| report_type (optional) | str | | Type of the report. Options: `BASIC`, `AUDIENCE` | `BASIC` |

**Returns:** A Pandas Dataframe with the requested data
