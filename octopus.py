import os
from datetime import date, datetime
from typing import Any, Literal, TypedDict

import requests
from requests.auth import HTTPBasicAuth

API_KEY_ENV = "OCTOPUS_API_KEY"


def get_api_key(api_key: str | None) -> str:
    if api_key is None:
        api_key = os.getenv(API_KEY_ENV)
    if api_key is None:
        raise ValueError(f"{API_KEY_ENV} must be set")
    if not api_key.startswith("sk_"):
        raise ValueError(f"{API_KEY_ENV} must start with 'sk_'")
    return api_key


GSP = Literal[
    "_A",
    "_B",
    "_C",
    "_D",
    "_E",
    "_F",
    "_G",
    "_H",
    "_I",
    "_J",
    "_K",
    "_L",
    "_M",
    "_N",
    "_O",
    "_P",
    "_Q",
    "_R",
    "_S",
    "_T",
    "_U",
    "_V",
    "_W",
    "_X",
    "_Y",
    "_Z",
]


class ElectricityMeterPointV1(TypedDict):
    gsp: GSP
    mpan: str
    profile_class: int


class ConsumptionV1(TypedDict):
    consumption: float
    interval_start: str
    interval_end: str


class LinkV1(TypedDict):
    href: str
    method: str
    rel: str


class ProductV1(TypedDict):
    code: str
    direction: str
    full_name: str
    display_name: str
    description: str
    is_variable: bool
    is_green: bool
    is_tracker: bool
    is_prepay: bool
    is_business: bool
    is_restricted: bool
    term: int
    available_from: str
    available_to: str | None
    links: list[LinkV1]
    brand: str


PaymentMethod = Literal["direct_debit_monthly", "direct_debit_quarterly"]


class BaseElectricityTariffV1(TypedDict):
    code: str
    standing_charge_exc_vat: float
    standing_charge_inc_vat: float
    online_discount_exc_vat: float
    online_discount_inc_vat: float
    dual_fuel_discount_exc_vat: float
    dual_fuel_discount_inc_vat: float
    exit_fees_exc_vat: float
    exit_fees_inc_vat: float
    exit_fees_type: str
    links: list[LinkV1]


class ElectricitySingleRateTariffV1(BaseElectricityTariffV1):
    standard_unit_rate_exc_vat: float
    standard_unit_rate_inc_vat: float


class ElectricityDualRateTariffV1(BaseElectricityTariffV1):
    day_unit_rate_exc_vat: float
    day_unit_rate_inc_vat: float
    night_unit_rate_exc_vat: float
    night_unit_rate_inc_vat: float


class ElectricitySingleRateConsumptionV1(TypedDict):
    electricity_standard: int


class ElectricityDualRateConsumptionV1(TypedDict):
    electricity_day: int
    electricity_night: int


class DualFuelSingleRateConsumptionV1(TypedDict):
    electricity_standard: int
    gas_standard: int


class DualFuelDualRateConsumptionV1(TypedDict):
    electricity_day: int
    electricity_night: int
    gas_standard: int


PlanType = Literal[
    "electricity_single_rate",
    "electricity_dual_rate",
    "dual_fuel_single_rate",
    "dual_fuel_dual_rate",
]


class SampleQuoteV1(TypedDict):
    annual_cost_inc_vat: int
    annual_cost_exc_vat: int


class SampleConsumptionV1(TypedDict):
    electricity_single_rate: ElectricitySingleRateConsumptionV1
    electricity_dual_rate: ElectricityDualRateConsumptionV1
    dual_fuel_single_rate: DualFuelSingleRateConsumptionV1
    dual_fuel_dual_rate: DualFuelDualRateConsumptionV1


class ProductDetailsV1(TypedDict):
    tariffs_active_at: str
    code: str
    full_name: str
    display_name: str
    description: str
    is_variable: bool
    is_green: bool
    is_tracker: bool
    is_prepay: bool
    is_business: bool
    is_restricted: bool
    term: int
    available_from: str
    available_to: str | None
    brand: str
    links: list[LinkV1]
    single_register_electricity_tariffs: dict[GSP, dict[PaymentMethod, ElectricitySingleRateTariffV1]]
    dual_register_electricity_tariffs: dict[GSP, dict[PaymentMethod, ElectricityDualRateTariffV1]]
    single_register_gas_tariffs: dict[GSP, dict[PaymentMethod, dict]]
    sample_quotes: dict[GSP, dict[PaymentMethod, dict[PlanType, SampleQuoteV1]]]
    sample_consumption: SampleConsumptionV1


class UnitRateV1(TypedDict):
    value_exc_vat: float
    value_inc_vat: float
    valid_from: str
    valid_to: str | None
    payment_method: Any


def params_to_str(**kwargs) -> str:
    return "&".join(f"{k}={v}" for k, v in kwargs.items() if v)


class OctopusEnergyAPIClient:
    api_key: str
    base_url: str
    session: requests.Session  # lateinit

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.octopus.energy/"):
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

    def _get(self, path: str, **kwargs):
        return self._request("get", path, **kwargs).json()

    def _get_all(self, path: str, **kwargs) -> list:
        data = []
        while True:
            response = self._get(path, **kwargs)
            data.extend(response["results"])
            next = response.get("next")
            if not next:
                break
            path = next[next.find(self.base_url) + len(self.base_url) :]
        return data

    def get_electricity_meter_point_v1(self, mpan: str) -> ElectricityMeterPointV1:
        return self._get(f"v1/electricity-meter-points/{mpan}")

    def list_electricity_meter_consumption_v1(
        self,
        mpan: str,
        serial: str,
        group_by: Literal["", "hour", "day", "week", "month", "quarter"] = "",
        order_by: Literal["", "period", "-period"] = "",
        period_from: date | None = None,
        period_to: date | None = None,
    ) -> list[ConsumptionV1]:
        params = params_to_str(
            group_by=group_by,
            order_by=order_by,
            period_from=period_from.isoformat() if period_from else None,
            period_to=period_to.isoformat() if period_to else None,
        )
        return self._get_all(f"v1/electricity-meter-points/{mpan}/meters/{serial}/consumption?{params}")

    def list_gas_meter_consumption_v1(
        self,
        mpan: str,
        serial: str,
        group_by: Literal["", "hour", "day", "week", "month", "quarter"] = "",
        order_by: Literal["", "period", "-period"] = "",
        period_from: date | None = None,
        period_to: date | None = None,
    ) -> list[ConsumptionV1]:
        params = params_to_str(
            group_by=group_by,
            order_by=order_by,
            period_from=period_from.isoformat() if period_from else None,
            period_to=period_to.isoformat() if period_to else None,
        )
        return self._get_all(f"v1/gas-meter-points/{mpan}/meters/{serial}/consumption?{params}")

    def list_products_v1(
        self,
        available_at: datetime | None = None,
        brand: str | None = None,
        is_business=False,
        is_green=False,
        is_historical=False,
        is_prepay=False,
        is_tracker=False,
        is_variable=False,
    ) -> list[ProductV1]:
        params = params_to_str(
            available_at=available_at.isoformat() if available_at else None,
            brand=brand,
            is_business=is_business,
            is_green=is_green,
            is_historical=is_historical,
            is_prepay=is_prepay,
            is_tracker=is_tracker,
            is_variable=is_variable,
            page=1,
        )
        return self._get_all(f"v1/products?{params}")

    def retrieve_product_v1(self, product_code: str) -> ProductDetailsV1:
        return self._get(f"v1/products/{product_code}")

    def list_electricity_tariff_day_unit_rates_v1(
        self,
        product_code: str,
        tariff_code: str,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> list[UnitRateV1]:
        params = params_to_str(
            period_from=period_from.isoformat() if period_from else None,
            period_to=period_to.isoformat() if period_to else None,
        )
        return self._get_all(f"v1/products/{product_code}/electricity-tariffs/{tariff_code}/day-unit-rates?{params}")

    def list_electricity_tariff_night_unit_rates_v1(
        self,
        product_code: str,
        tariff_code: str,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> list[UnitRateV1]:
        params = params_to_str(
            period_from=period_from.isoformat() if period_from else None,
            period_to=period_to.isoformat() if period_to else None,
        )
        return self._get_all(f"v1/products/{product_code}/electricity-tariffs/{tariff_code}/night-unit-rates?{params}")

    def list_electricity_tariff_standard_unit_rates_v1(
        self,
        product_code: str,
        tariff_code: str,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> list[UnitRateV1]:
        params = params_to_str(
            period_from=period_from.isoformat() if period_from else None,
            period_to=period_to.isoformat() if period_to else None,
        )
        return self._get_all(f"v1/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates?{params}")

    def list_electricity_tariff_standing_charges_v1(
        self,
        product_code: str,
        tariff_code: str,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> list[UnitRateV1]:
        params = params_to_str(
            period_from=period_from.isoformat() if period_from else None,
            period_to=period_to.isoformat() if period_to else None,
        )
        return self._get_all(f"v1/products/{product_code}/electricity-tariffs/{tariff_code}/standing-charges?{params}")

    def list_gas_tariff_standard_unit_rates_v1(
        self,
        product_code: str,
        tariff_code: str,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> list[UnitRateV1]:
        params = params_to_str(
            period_from=period_from.isoformat() if period_from else None,
            period_to=period_to.isoformat() if period_to else None,
        )
        return self._get_all(f"v1/products/{product_code}/gas-tariffs/{tariff_code}/standard-unit-rates?{params}")

    def list_gas_tariff_standing_charges_v1(
        self,
        product_code: str,
        tariff_code: str,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> list[UnitRateV1]:
        params = params_to_str(
            period_from=period_from.isoformat() if period_from else None,
            period_to=period_to.isoformat() if period_to else None,
        )
        return self._get_all(f"v1/products/{product_code}/gas-tariffs/{tariff_code}/standing-charges?{params}")
