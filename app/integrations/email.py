from app.config import Settings
from app.integrations.base import IntegrationError, request_json


class EmailClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, to: str, subject: str, html: str, text: str | None = None) -> dict:
        if self.settings.resend_api_key:
            return await self._send_resend(to, subject, html, text)
        if self.settings.sendgrid_api_key:
            return await self._send_sendgrid(to, subject, html, text)
        raise IntegrationError("email", "Configure RESEND_API_KEY or SENDGRID_API_KEY")

    async def _send_resend(self, to: str, subject: str, html: str, text: str | None) -> dict:
        payload: dict = {
            "from": self.settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text

        data = await request_json(
            "POST",
            "https://api.resend.com/emails",
            service="resend",
            headers={
                "Authorization": f"Bearer {self.settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        return {"provider": "resend", "id": data.get("id")}

    async def _send_sendgrid(self, to: str, subject: str, html: str, text: str | None) -> dict:
        content = [{"type": "text/html", "value": html}]
        if text:
            content.append({"type": "text/plain", "value": text})

        data = await request_json(
            "POST",
            "https://api.sendgrid.com/v3/mail/send",
            service="sendgrid",
            headers={
                "Authorization": f"Bearer {self.settings.sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": self.settings.email_from},
                "subject": subject,
                "content": content,
            },
        )
        return {"provider": "sendgrid", "status": "accepted", "response": data}
