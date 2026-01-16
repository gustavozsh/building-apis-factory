# Changelog

Guidelines based on https://github.com/vweevers/common-changelog

## [0.0.51] - 2025-06-12
### Changed
- [[Meta](./cadastra_core/GoogleAds/)] Update GoogleAds Api Version [Vinicius Gomes <vinicius.gomes@cadastra.com>]

## [0.0.50] - 2025-05-02
### Changed
- [[Meta](./cadastra_core/Meta/)] Hot Fix Meta Api Version [Bryan Bora <bryan.bora@cadastra.com>]

## [0.0.49] - 2025-02-11
### Test CICD

## [0.0.48] - 2024-12-16
### Added
- [[Criteo](./cadastra_core/Criteo/)] New connector [Fernando Zanutto <fernando.zanutto@cadastra.com>]
- [[Mercado Livre](./cadastra_core/MercadoLivre/)] Campaign status filter [Fernando Zanutto <fernando.zanutto@cadastra.com>]
- [[Mercado Livre](./cadastra_core/MercadoLivre/)] Aggregation type parameter [Fernando Zanutto <fernando.zanutto@cadastra.com>]

## [0.0.47] - 2024-11-18
### Changed
- [[Meta](./cadastra_core/Meta/)] Added attribution window parameter [Fernando Zanutto <fernando.zanutto@cadastra.com>]

## [0.0.46] - 2024-11-07
### Fixed
- [[Mercado Livre](./cadastra_core/MercadoLivre/)] Checks if dates are within a campaign start and end date [Fernando Zanutto <fernando.zanutto@cadastra.com>]

## [0.0.45] - 2024-11-07
### Added
- [[Mercado Livre](./cadastra_core/MercadoLivre/)] New connector [Fernando Zanutto <fernando.zanutto@cadastra.com>]

### Changed
- [[Google Analytics 4](./cadastra_core/GoogleAnalytics4/)] Now supports filtering requests [Bryan Bora <bryan.bora@cadastra.com>]
- [[Meta](./cadastra_core/Meta/)] Added request limit parameter to optimize memory usage [Fernando Zanutto <fernando.zanutto@cadastra.com>]
- [[DV360](./cadastra_core/DV360/)] Added "query_id" parameter support to download specific reports instead of always generating a new one [Fernando Zanutto <fernando.zanutto@cadastra.com>]
- [[TikTok](./cadastra_core/TikTok/)] Upgraded API version to 1.3 [Fernando Zanutto <fernando.zanutto@cadastra.com>]
- [[Bing](./cadastra_core/Bing/)] Added new "ad_performance" report type [Bryan Bora <bryan.bora@cadastra.com>]

## [0.0.44] - 2024-10-16
### Added
- [[Amazon Ads](./cadastra_core/AmazonAds/)] New connector [Fernando Zanutto <fernando.zanutto@cadastra.com>]

### Changed
- [[Utils](./cadastra_core/Utils/)] Method "send_message_to_chat" now requires a "force_send" parameter when sending success notifications in order to avoid spamming Google Chat.

## [0.0.43] - 2024-10-09
### Changed
- [[Utils](./cadastra_core/Utils/)] No longer uses class, now you can just import the method you want directly. Still has "Utils" class for retro compatibility but you should't use it.
  
## [0.0.42] - 2024-10-09
### Changed
- [[Utils](./cadastra_core/Utils/)] Method "send_message_to_chat" now supports threaded messages. Just add a "threadKey=xxxx" parameter in the URL
  
## [0.0.41] - 2024-10-02
### Changed
- [[Meta](./cadastra_core/Meta/)] Method "request_report" new boolean parameter "return_json" to determine if it will return a list of dicts or a ready to use Pandas Dataframe [Fernando Zanutto <fernando.zanutto@cadastra.com>]

### Fixed
- [[Meta](./cadastra_core/Meta/)] Optimized request_report by using "limit=1000" on the request params sent to the API to increse data returned on each page [Fernando Zanutto <fernando.zanutto@cadastra.com>]

## [0.0.40] - 2024-10-01
### Added
- [[TikTok](./cadastra_core/TikTok/)] New connector [Fernando Zanutto <fernando.zanutto@cadastra.com>]

## [0.0.39] - 2024-09-30
### Added
- [[Bing Ads](./cadastra_core/Bing/)] New connector [Bryan Bora <bryan.bora@cadastra.com>]

## [0.0.38] - 2024-09-26
### Added
- [[GoogleAds](./cadastra_core/GoogleAds/)] New method "send_request_pandas" [Daniel Mendel <dmendel@cadastra.com>]

### Fixed
- [[Search Ads 360](./cadastra_core/SearchAds360/)] Optimized the "run_query" method: query now runs via Search Stream method and the final Dataframe is only generated after all response is processed. [Daniel Mendel <dmendel@cadastra.com>]

## [0.0.37] - 2024-09-26
### Added
- [[Utils](./cadastra_core/Utils/)] New method "get_date_array" [Fernando Zanutto <fernando.zanutto@cadastra.com>]
- [[Meta](./cadastra_core/Meta/)] New method "request_report_by_day" [Fernando Zanutto <fernando.zanutto@cadastra.com>]

## [0.0.35] - 2024-09-26
### Added
- [[GoogleAds](./cadastra_core/GoogleAds/)] New connector [Bryan Bora <bryan.bora@cadastra.com> and Daniel Mendel <dmendel@cadastra.com>]

## [0.0.34] - 2024-09-25
### Added
- [[DV360](./cadastra_core/DV360/)] New connector [Bryan Bora <bryan.bora@cadastra.com> and Daniel Mendel <dmendel@cadastra.com>]
- [[Utils](./cadastra_core/Utils/)] New methods

## [0.0.33] - 2024-09-25
### Added
- [[Utils](./cadastra_core/Utils/)] New methods "send_error_message_to_chat" and "send_warning_message_to_chat"

### Changed
- [[Search Ads 360](./cadastra_core/SearchAds360/)] "run_query" now returns None if query returns no result

## [0.0.31] - 2024-09-25
### Added
- [[Utils](./cadastra_core/Utils/)] New method "get_environment" [Daniel Mendel <dmendel@cadastra.com>]

### Fixed
- [[Search Ads 360](./cadastra_core/SearchAds360/)] Really fixed renaming column names for final dataframe

## [0.0.25] - 2024-09-25
### Added
- [Utils](./cadastra_core/Utils/) New utilities module [Daniel Mendel <dmendel@cadastra.com>]

### Fixed
- [[Search Ads 360](./cadastra_core/SearchAds360/)] Fix renaming column names for final dataframe

## [0.0.20] - 2024-09-24
### Added
- [Search Ads 360](./cadastra_core/SearchAds360/) connector [Fernando Zanutto <fernando.zanutto@cadastra.com> and Daniel Mendel <dmendel@cadastra.com>]
- [[BigQuery](./cadastra_core/BigQuery/)] Method "list_tables" [Daniel Mendel <dmendel@cadastra.com>]
- [[Secret Manager](./cadastra_core/SecretManager/)] List of available secrets

### Fixed
- [[BigQuery](./cadastra_core/BigQuery/)] Class initialization now returns None instead of bool [Daniel Mendel <dmendel@cadastra.com>]

## [0.0.16] - 2024-09-17
### Added
- [[Meta](./cadastra_core/Meta/)] New method "get_campaign_ids" [Daniel Mendel <dmendel@cadastra.com>]
- New [RTB House](./cadastra_core/Rtbhouse/) connector [Fernando Zanutto <fernando.zanutto@cadastra.com>]

### Changed
- [[Meta](./cadastra_core/Meta/)] Method "request_report" now reads any entity and aggregation level you need by using the "entity_name" and "level" parameters

## [0.0.15] - 2024-09-16
### Added
- [[Google Analytics 4](./cadastra_core/GoogleAnalytics4/)] New method "get_metadata" [Fernando Zanutto <fernando.zanutto@cadastra.com>]

## [0.0.14] - 2024-09-10
### Added
- New [Meta](./cadastra_core/Meta/) controller created [Fernando Zanutto <fernando.zanutto@cadastra.com>]