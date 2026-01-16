from __future__ import annotations

from google.cloud import secretmanager


def access_secret(
    client: secretmanager.SecretManagerServiceClient,
    project_id: str,
    secret_id: str,
    version: str = "latest",
) -> str:
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("utf-8")
