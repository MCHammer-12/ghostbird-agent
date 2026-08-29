import httpx


class IntegrationError(Exception):
    def __init__(self, service: str, message: str, status_code: int | None = None) -> None:
        self.service = service
        self.message = message
        self.status_code = status_code
        super().__init__(f"{service}: {message}")


async def request_json(
    method: str,
    url: str,
    *,
    service: str,
    headers: dict[str, str] | None = None,
    json: dict | list | None = None,
    timeout: float = 30.0,
) -> dict | list:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, url, headers=headers, json=json)

    if response.status_code >= 400:
        raise IntegrationError(
            service,
            response.text or f"HTTP {response.status_code}",
            response.status_code,
        )

    if not response.content:
        return {}
    return response.json()
