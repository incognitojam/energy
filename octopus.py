from datetime import date
import os
from typing import Literal, TypedDict

import requests
from requests.auth import HTTPBasicAuth


def get_api_key(api_key: str | None) -> str:
    if api_key is None:
        api_key = os.getenv("OCTOPUS_API_KEY")
    if api_key is None:
        raise ValueError("OCTOPUS_API_KEY must be set")
    if not api_key.startswith("sk_"):
        raise ValueError("OCTOPUS_API_KEY must start with 'sk_'")
    return api_key


class ElectricityMeterPointV1(TypedDict):
    gsp: str
    mpan: str
    profile_class: int


class ConsumptionV1(TypedDict):
    consumption: float
    interval_start: str
    interval_end: str


def params_to_str(**kwargs) -> str:
    return "&".join(f"{k}={v}" for k, v in kwargs.items() if v)


class OctopusEnergyAPIClient:
    api_key: str
    base_url: str
    session: requests.Session  # lateinit

    def __init__(
        self, api_key: str | None = None, base_url: str = "https://api.octopus.energy/"
    ):
        self.api_key = get_api_key(api_key)
        self.base_url = base_url

    def __enter__(self):
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.api_key, "")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def _get(self, path: str, **kwargs) -> requests.Response:
        return self._request("get", path, **kwargs)

    def _get_all(self, path: str, **kwargs) -> list:
        data = []
        while True:
            response = self._request("get", path, **kwargs).json()
            data.extend(response["results"])
            next = response.get("next")
            if not next:
                break
            path = next[next.find(self.base_url) + len(self.base_url) :]
        return data

    def get_electricity_meter_point_v1(self, mpan: str) -> ElectricityMeterPointV1:
        response = self._get(f"v1/electricity-meter-points/{mpan}")
        return response.json()

    def get_electricity_consumption_v1(
        self,
        mpan: str,
        serial: str,
        group_by: Literal["", "hour", "day", "week", "month", "quarter"] = "",
        order_by: Literal["", "period", "-period"] = "",
        period_from: date | None = None,
        period_to: date | None = None,
    ) -> list[ConsumptionV1]:
        # TODO: optimise page_size
        params = params_to_str(
            group_by=group_by,
            order_by=order_by,
            page=1,
            page_size=1000,
            period_from=period_from.isoformat() if period_from else None,
            period_to=period_to.isoformat() if period_to else None,
        )
        return self._get_all(
            f"v1/electricity-meter-points/{mpan}/meters/{serial}/consumption?{params}"
        )
