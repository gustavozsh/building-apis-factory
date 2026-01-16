from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import pytz
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from google.cloud import secretmanager
from google.oauth2 import service_account

from shared.bigquery import load_dataframe_to_bigquery, normalize_dataframe
from shared.config import get_parameter, load_yaml_config, parse_secret_payload
from shared.secrets import access_secret

LOGGER = logging.getLogger("linkedin_service")
logging.basicConfig(level=logging.INFO)

CONFIG_PATH = Path(__file__).with_name("config.yaml")

app = FastAPI(title="LinkedIn API", version="1.0.0")


class LinkedInLoadRequest(BaseModel):
    organization_urn: str
    client_name: str
    posts_count: int | None = Field(default=40)
    timezone: str | None = Field(default="America/Sao_Paulo")
    secret_project_id: str
    linkedin_secret_id: str
    bq_secret_id: str
    destination_project_id: str
    destination_dataset: str
    destination_general_table: str
    destination_posts_table: str
    delete_existing: bool | None = Field(default=False)
    partition_column: str | None = Field(default=None)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def get_organization_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def fetch_company_info(headers: dict[str, str], client_name: str) -> tuple[str, str]:
    company_info_url = (
        "https://api.linkedin.com/v2/organizationalEntityAcls"
        "?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED"
        "&projection=(elements*(organizationalTarget~(localizedName)))"
    )
    response = requests.get(company_info_url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    for element in data.get("elements", []):
        org_name = element.get("organizationalTarget~", {}).get("localizedName")
        if org_name == client_name:
            org_target = element.get("organizationalTarget")
            return org_target, org_name

    raise ValueError("Organization not found for client_name.")


def fetch_followers(headers: dict[str, str], organization_urn: str) -> int:
    followers_url = (
        "https://api.linkedin.com/v2/networkSizes/"
        f"{organization_urn}?edgeType=CompanyFollowedByMember"
    )
    response = requests.get(followers_url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("firstDegreeSize", 0)


def fetch_posts(
    headers: dict[str, str],
    organization_urn: str,
    count: int,
) -> list[dict[str, Any]]:
    organization_urn_encoded = quote(organization_urn, safe="")
    posts_url = (
        "https://api.linkedin.com/v2/ugcPosts"
        f"?q=authors&authors=List({organization_urn_encoded})"
        f"&sortBy=CREATED&count={count}"
    )
    response = requests.get(posts_url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("elements", [])


def fetch_post_analytics(headers: dict[str, str], organization_urn: str, post_id: str) -> dict[str, Any]:
    if "share" in post_id:
        url = (
            "https://api.linkedin.com/v2/organizationalEntityShareStatistics"
            f"?q=organizationalEntity&organizationalEntity={organization_urn}"
            f"&shares[0]={post_id}"
        )
    else:
        url = (
            "https://api.linkedin.com/v2/organizationalEntityShareStatistics"
            f"?q=organizationalEntity&organizationalEntity={organization_urn}"
            f"&ugcPosts[0]={post_id}"
        )

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def build_general_dataframe(date_insertion: str, org_id: str, org_name: str, followers: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date_insertion": date_insertion,
                "id": org_id,
                "client": org_name,
                "followers": followers,
            }
        ]
    )


def build_posts_dataframe(
    date_insertion: str,
    organization_urn: str,
    posts: list[dict[str, Any]],
    headers: dict[str, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for element in posts:
        post_id = element.get("id")
        if not post_id:
            continue

        created_time = element.get("created", {}).get("time")
        created_date = None
        if created_time:
            created_date = datetime.fromtimestamp(created_time / 1000.0).date().isoformat()

        post_type = (
            element.get("specificContent", {})
            .get("com.linkedin.ugc.ShareContent", {})
            .get("shareMediaCategory")
        )
        text = (
            element.get("specificContent", {})
            .get("com.linkedin.ugc.ShareContent", {})
            .get("shareCommentary", {})
            .get("text", "")
        ).replace("\n", " ").replace("\r", " ")

        media_list = (
            element.get("specificContent", {})
            .get("com.linkedin.ugc.ShareContent", {})
            .get("media", [])
        )
        thumbnail_url = media_list[0].get("originalUrl") if media_list else ""

        analytics = fetch_post_analytics(headers, organization_urn, post_id)
        elements = analytics.get("elements", [])
        stats = elements[0].get("totalShareStatistics", {}) if elements else {}

        rows.append(
            {
                "date_insertion": date_insertion,
                "author": element.get("author"),
                "created": created_date,
                "post_id": post_id,
                "post_type": post_type,
                "text": text,
                "thumbnail_url": thumbnail_url,
                "url": f"https://www.linkedin.com/embed/feed/update/{post_id}",
                "uniqueImpressionsCount": stats.get("uniqueImpressionsCount"),
                "sharecount": stats.get("shareCount"),
                "engagement": stats.get("engagement"),
                "clickcount": stats.get("clickCount"),
                "likeCount": stats.get("likeCount"),
                "impressioncount": stats.get("impressionCount"),
                "commentcount": stats.get("commentCount"),
            }
        )

    return pd.DataFrame(rows)


@app.post("/load")
async def load_linkedin_report(payload: LinkedInLoadRequest) -> dict[str, Any]:
    config = load_yaml_config(CONFIG_PATH)
    request_json = payload.model_dump(exclude_none=True)

    try:
        organization_urn = get_parameter(
            request_json, "organization_urn", config.get("organization_urn"), True
        )
        client_name = get_parameter(
            request_json, "client_name", config.get("client_name"), True
        )
        posts_count = int(get_parameter(request_json, "posts_count", 40))
        timezone = get_parameter(
            request_json, "timezone", config.get("timezone", "America/Sao_Paulo")
        )

        secret_project_id = get_parameter(
            request_json, "secret_project_id", config.get("secret_project_id"), True
        )
        linkedin_secret_id = get_parameter(
            request_json, "linkedin_secret_id", config.get("linkedin_secret_id"), True
        )
        bq_secret_id = get_parameter(
            request_json, "bq_secret_id", config.get("bq_secret_id"), True
        )

        destination_project_id = get_parameter(
            request_json,
            "destination_project_id",
            config.get("destination_project_id"),
            True,
        )
        destination_dataset = get_parameter(
            request_json, "destination_dataset", config.get("destination_dataset"), True
        )
        destination_general_table = get_parameter(
            request_json,
            "destination_general_table",
            config.get("destination_general_table"),
            True,
        )
        destination_posts_table = get_parameter(
            request_json,
            "destination_posts_table",
            config.get("destination_posts_table"),
            True,
        )
        delete_existing = bool(get_parameter(request_json, "delete_existing", False))
        partition_column = get_parameter(request_json, "partition_column")

        secret_client = secretmanager.SecretManagerServiceClient()
        linkedin_secret_value = access_secret(
            secret_client, secret_project_id, linkedin_secret_id
        )
        linkedin_payload = parse_secret_payload(linkedin_secret_value)
        access_token = (
            linkedin_payload.get("access_token")
            if isinstance(linkedin_payload, dict)
            else linkedin_payload
        )
        if not access_token:
            raise ValueError("LinkedIn access token was not found in the secret payload.")

        bq_secret_value = access_secret(secret_client, secret_project_id, bq_secret_id)
        bq_payload = parse_secret_payload(bq_secret_value)
        if not isinstance(bq_payload, dict):
            raise ValueError("BigQuery secret must be a service account JSON payload.")

        credentials_bigquery = service_account.Credentials.from_service_account_info(
            bq_payload
        )

        date_insertion = (
            datetime.now(pytz.timezone(timezone)) - timedelta(days=2)
        ).strftime("%d-%m-%Y")

        headers = get_organization_headers(access_token)
        org_id, org_name = fetch_company_info(headers, client_name)
        followers = fetch_followers(headers, organization_urn)
        general_df = build_general_dataframe(date_insertion, org_id, org_name, followers)

        posts = fetch_posts(headers, organization_urn, posts_count)
        posts_df = build_posts_dataframe(date_insertion, organization_urn, posts, headers)

        general_df = normalize_dataframe(general_df, ["date_insertion"])
        posts_df = normalize_dataframe(posts_df, ["created", "date_insertion"])

        general_rows = load_dataframe_to_bigquery(
            df=general_df,
            credentials=credentials_bigquery,
            project_id=destination_project_id,
            dataset_id=destination_dataset,
            table_id=destination_general_table,
            delete_existing=delete_existing,
            partition_column=partition_column,
        )
        posts_rows = load_dataframe_to_bigquery(
            df=posts_df,
            credentials=credentials_bigquery,
            project_id=destination_project_id,
            dataset_id=destination_dataset,
            table_id=destination_posts_table,
            delete_existing=delete_existing,
            partition_column=partition_column,
        )

    except ValueError as error:
        LOGGER.exception("Invalid request")
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        LOGGER.exception("Failed to load LinkedIn report")
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "success": True,
        "rows_loaded": {
            "general": general_rows,
            "posts": posts_rows,
        },
        "destination": {
            "general": f"{destination_project_id}.{destination_dataset}.{destination_general_table}",
            "posts": f"{destination_project_id}.{destination_dataset}.{destination_posts_table}",
        },
    }
