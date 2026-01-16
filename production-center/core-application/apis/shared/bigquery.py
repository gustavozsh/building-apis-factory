from __future__ import annotations

import logging
from datetime import date
from typing import Iterable

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

LOGGER = logging.getLogger("bigquery_loader")


def normalize_dataframe(df: pd.DataFrame, timestamp_columns: Iterable[str]) -> pd.DataFrame:
    if df.empty:
        return df

    for column in timestamp_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    for column in df.columns:
        if column not in set(timestamp_columns):
            df[column] = df[column].astype("string")

    return df


def delete_existing_rows(
    client: bigquery.Client,
    table_id: str,
    start_date: date,
    end_date: date,
    account_ids: list[str] | None,
    partition_column: str,
) -> None:
    if not partition_column:
        return

    account_ids = account_ids or []

    filter_clause = f"DATE({partition_column}) BETWEEN @start_date AND @end_date"
    if account_ids:
        filter_clause += " AND account_id IN UNNEST(@account_ids)"

    query = f"""
        DELETE FROM `{table_id}`
        WHERE {filter_clause}
    """

    parameters = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]

    if account_ids:
        parameters.append(
            bigquery.ArrayQueryParameter("account_ids", "STRING", account_ids)
        )

    job_config = bigquery.QueryJobConfig(query_parameters=parameters)
    client.query(query, job_config=job_config).result()
    LOGGER.info("Removed existing rows for date range %s - %s", start_date, end_date)


def load_dataframe_to_bigquery(
    df: pd.DataFrame,
    credentials: service_account.Credentials,
    project_id: str,
    dataset_id: str,
    table_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    account_ids: list[str] | None = None,
    delete_existing: bool = False,
    partition_column: str | None = None,
) -> int:
    client = bigquery.Client(credentials=credentials, project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    if delete_existing and start_date and end_date and partition_column:
        delete_existing_rows(
            client=client,
            table_id=table_ref,
            start_date=start_date,
            end_date=end_date,
            account_ids=account_ids,
            partition_column=partition_column,
        )

    if df.empty:
        LOGGER.info("No rows to load for %s", table_ref)
        return 0

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
    )
    load_job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    result = load_job.result()
    LOGGER.info("Loaded %s rows into %s", result.output_rows, table_ref)
    return result.output_rows
