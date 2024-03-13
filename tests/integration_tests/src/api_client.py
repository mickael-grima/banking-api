import asyncio
import dataclasses
from typing import Any

import aiohttp


@dataclasses.dataclass
class APIResponse:
    json_body: Any
    status_code: int = 200

    def remove_fields(self, *fields: str):
        if isinstance(self.json_body, dict):
            for field in fields:
                if field in self.json_body:
                    del self.json_body[field]
        elif isinstance(self.json_body, list):
            for field in fields:
                for i, _ in enumerate(self.json_body):
                    if isinstance(self.json_body[i], dict):
                        if field in self.json_body[i]:
                            del self.json_body[i][field]


class APIClient:
    """
    This class handles calls to the Banking API
    """

    def __init__(self, host: str):
        self._host = host
        self._session = aiohttp.ClientSession()

    def __del__(self):
        # we can't call self._session.close() directly since it is async
        # Closing the connector is sufficient, even igf it means
        # accessing protected methods
        self._session._connector._close()

    async def get(self, path: str, params: dict = None) -> APIResponse:
        """GET call to `self._host/path?params"""
        async with self._session.get(
                f"{self._host}{path}", params=params) as res:
            return APIResponse(
                status_code=res.status,
                json_body=await res.json(),
            )

    async def post(self, path: str, params: dict = None) -> APIResponse:
        """POST call to `self._host/path?params"""
        # sleep 1sec for transfer creations to ensure each transfer
        # has a different utc_timestamp
        if path.startswith("/transfer"):
            await asyncio.sleep(1)
        async with self._session.post(
                f"{self._host}{path}", params=params) as res:
            return APIResponse(
                status_code=res.status,
                json_body=await res.json(),
            )
