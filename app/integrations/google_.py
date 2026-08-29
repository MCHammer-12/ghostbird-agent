import base64
import json
from typing import Any

from app.config import Settings
from app.integrations.base import IntegrationError


class GoogleClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _credentials(self):
        try:
            from google.oauth2 import service_account
        except ImportError as exc:
            raise IntegrationError("google", "Install with: uv sync --extra google") from exc

        raw = self.settings.google_service_account_json.strip()
        if raw.startswith("{"):
            info = json.loads(raw)
        else:
            info = json.loads(base64.b64decode(raw).decode())

        return service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )

    async def append_sheet_row(self, spreadsheet_id: str, range_name: str, values: list[Any]) -> dict[str, Any]:
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise IntegrationError("google", "Install with: uv sync --extra google") from exc

        service = build("sheets", "v4", credentials=self._credentials(), cache_discovery=False)
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": [values]},
            )
            .execute()
        )
        return {
            "updated_range": result.get("updates", {}).get("updatedRange"),
            "updated_rows": result.get("updates", {}).get("updatedRows"),
        }
