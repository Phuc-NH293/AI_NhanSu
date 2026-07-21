"""Config-driven connectors for enterprise HRM and SharePoint integrations."""

from __future__ import annotations

import os
from typing import Any

import requests


class HRMConnector:
    def __init__(self) -> None:
        self.base_url = os.getenv("HRM_API_BASE", "").rstrip("/")
        self.token = os.getenv("HRM_API_TOKEN", "")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def get_employee_profile(self, employee_id: str) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("HRM connector is not configured")
        response = requests.get(
            f"{self.base_url}/employees/{employee_id}",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()


class SharePointConnector:
    def __init__(self) -> None:
        self.tenant_id = os.getenv("SHAREPOINT_TENANT_ID", "")
        self.client_id = os.getenv("SHAREPOINT_CLIENT_ID", "")
        self.client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET", "")
        self.site_id = os.getenv("SHAREPOINT_SITE_ID", "")
        self.drive_id = os.getenv("SHAREPOINT_DRIVE_ID", "")

    @property
    def configured(self) -> bool:
        return all((self.tenant_id, self.client_id, self.client_secret, self.site_id, self.drive_id))

    def _access_token(self) -> str:
        response = requests.post(
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def list_documents(self) -> list[dict[str, Any]]:
        if not self.configured:
            raise RuntimeError("SharePoint connector is not configured")
        response = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/root/children",
            headers={"Authorization": f"Bearer {self._access_token()}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("value", [])
