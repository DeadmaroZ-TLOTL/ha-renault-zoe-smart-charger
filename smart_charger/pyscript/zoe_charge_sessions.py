# ruff: noqa: F821 - Pyscript injects state, service, time_trigger, and log.

import asyncio
import math
import time
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from functools import partial
from zoneinfo import ZoneInfo

from custom_components.pyscript.function import Function
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.zoe_new_extended.charging_accounts_data import (
    apply_provider_transactions,
    combine_charge_fragments,
    parse_nordpool_day_ahead_prices,
)


MODEL_CODE = "X102VE"
DEFAULT_BATTERY_CAPACITY_KWH = 52.0
DEFAULT_CHARGING_EFFICIENCY = 0.9
DEFAULT_CHARGING_POWER_KW = 11.0
DEFAULT_DELIVERY_PRICE_EXCL_VAT_EUR_PER_KWH = 0.03962
DEFAULT_ENERGY_VAT_PERCENT = 21.0
DEFAULT_FALLBACK_CONSUMPTION_KWH_PER_100KM = 17.5
VISIBLE_HISTORY_DAYS = 31
LEARNING_HISTORY_DAYS = 180
MAX_EXPOSED_HISTORY_SESSIONS = 200
UPDATE_INTERVAL_MINUTES = 15
EFFECTIVE_PRICE_ENTITY = "sensor.renault_zoe_new_effective_charging_price"
DYNAMIC_PRICE_ENTITY = "sensor.renault_zoe_new_nord_pool_price"
LEGACY_PRICE_ENTITY = "sensor.nordpool_kwh_lv_eur_3_10_021"
COST_SETTINGS_ENTITY = "sensor.renault_zoe_new_cost_settings"
CHARGING_ACCOUNTS_ENTITY = "sensor.renault_zoe_new_charging_accounts"
NORDPOOL_ARCHIVE_API_URL = (
    "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
)
NORDPOOL_ARCHIVE_AREA = "LV"
EXACT_PROVIDER_PRICE_SOURCES = {
    "elektrum_drive_app",
    "mobilly",
    "ignitis_on_app",
    "ikrautas_app",
}
PYSCRIPT_REVISION = "operator_transactions_v5"

_refresh_in_progress = False
_nordpool_archive_cache = {}


def _attributes(result):
    raw = getattr(result, "raw_data", None) or {}
    if not isinstance(raw, dict):
        return {}
    data = raw.get("data", raw)
    if not isinstance(data, dict):
        return {}
    attrs = data.get("attributes", data)
    return attrs if isinstance(attrs, dict) else {}


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _cost_settings():
    """Read the integration options through its stable settings sensor."""
    state_value = Function.hass.states.get(COST_SETTINGS_ENTITY)
    attrs = state_value.attributes if state_value is not None else {}
    capacity = max(
        1.0,
        _number(
            attrs.get("battery_capacity_kwh"),
            DEFAULT_BATTERY_CAPACITY_KWH,
        ),
    )
    efficiency = _number(
        attrs.get("charging_efficiency"),
        _number(
            attrs.get("charging_efficiency_percent"),
            DEFAULT_CHARGING_EFFICIENCY * 100,
        )
        / 100.0,
    )
    efficiency = min(1.0, max(0.01, efficiency))
    delivery_excl_vat = max(
        0.0,
        _number(
            attrs.get("delivery_price_excl_vat_eur_per_kwh"),
            DEFAULT_DELIVERY_PRICE_EXCL_VAT_EUR_PER_KWH,
        ),
    )
    vat_percent = max(
        0.0,
        _number(
            attrs.get("vat_percent"),
            DEFAULT_ENERGY_VAT_PERCENT,
        ),
    )
    delivery_incl_vat = _number(
        attrs.get("delivery_price_incl_vat_eur_per_kwh"),
        delivery_excl_vat * (1 + vat_percent / 100.0),
    )
    return {
        "battery_capacity_kwh": capacity,
        "charging_efficiency": efficiency,
        "default_charging_power_kw": max(
            0.1,
            _number(
                attrs.get("default_charging_power_kw"),
                DEFAULT_CHARGING_POWER_KW,
            ),
        ),
        "delivery_price_excl_vat_eur_per_kwh": delivery_excl_vat,
        "vat_percent": vat_percent,
        "delivery_price_incl_vat_eur_per_kwh": max(0.0, delivery_incl_vat),
        "fallback_consumption_kwh_per_100km": max(
            0.1,
            _number(
                attrs.get("fallback_consumption_kwh_per_100km"),
                DEFAULT_FALLBACK_CONSUMPTION_KWH_PER_100KM,
            ),
        ),
    }


def _normalise_session(raw, settings):
    start_soc = _number(raw.get("chargeStartBatteryLevel"))
    end_soc = _number(raw.get("chargeEndBatteryLevel"))
    soc_gained = max(0.0, end_soc - start_soc)
    duration = max(0, round(_number(raw.get("chargeDuration"))))
    energy_recovered = raw.get("chargeEnergyRecovered")
    if energy_recovered is not None:
        energy_recovered = round(_number(energy_recovered), 2)
    return {
        "start": raw.get("chargeStartDate"),
        "end": raw.get("chargeEndDate"),
        "duration_min": duration,
        "start_soc": round(start_soc, 1),
        "end_soc": round(end_soc, 1),
        "soc_gained": round(soc_gained, 1),
        "energy_recovered_kwh": energy_recovered,
        "estimated_battery_energy_kwh": round(
            settings["battery_capacity_kwh"] * soc_gained / 100.0, 2
        ),
        "charge_type": raw.get("chargePower"),
        "status": raw.get("chargeEndStatus"),
    }


def _parse_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _history_state_value(item):
    if isinstance(item, dict):
        return item.get("state")
    return getattr(item, "state", None)


def _history_state_time(item):
    if isinstance(item, dict):
        value = item.get("last_updated") or item.get("last_changed")
    else:
        value = getattr(item, "last_updated", None) or getattr(
            item, "last_changed", None
        )
    return _parse_datetime(value)


def _history_state_attributes(item):
    if isinstance(item, dict):
        attributes = item.get("attributes", {})
    else:
        attributes = getattr(item, "attributes", {})
    return attributes if isinstance(attributes, dict) else {}


def _resolve_nordpool_price_entity():
    """Prefer the selected area's original sensor to retain old price history."""
    hass = Function.hass
    dynamic = hass.states.get(DYNAMIC_PRICE_ENTITY)
    if dynamic is not None:
        source_entity = dynamic.attributes.get("source_entity")
        if source_entity and hass.states.get(source_entity) is not None:
            return source_entity
        return DYNAMIC_PRICE_ENTITY
    if hass.states.get(LEGACY_PRICE_ENTITY) is not None:
        return LEGACY_PRICE_ENTITY
    return DYNAMIC_PRICE_ENTITY


def _current_effective_price():
    current = Function.hass.states.get(EFFECTIVE_PRICE_ENTITY)
    if current is None:
        return None
    value = _number(current.state, float("nan"))
    if not math.isfinite(value):
        return None
    return {"cents_per_kwh": value, "attributes": dict(current.attributes)}


def _provider_transactions():
    """Read normalized, de-duplicated transactions from account coordinators."""
    current = Function.hass.states.get(CHARGING_ACCOUNTS_ENTITY)
    if current is None:
        return []
    transactions = current.attributes.get("transactions") or []
    return [dict(item) for item in transactions if isinstance(item, dict)]


async def _get_price_history(
    start,
    end,
    price_entity,
    *,
    include_attributes=False,
):
    hass = Function.hass
    query = partial(
        get_significant_states,
        hass,
        start,
        end,
        [price_entity],
        include_start_time_state=True,
        significant_changes_only=False,
        no_attributes=not include_attributes,
    )
    result = await get_instance(hass).async_add_executor_job(query)
    prices = []
    for item in result.get(price_entity, []):
        item_time = _history_state_time(item)
        item_value = _number(_history_state_value(item), float("nan"))
        if item_time is not None and math.isfinite(item_value):
            price = {"time": item_time, "cents_per_kwh": item_value}
            if include_attributes:
                price["attributes"] = _history_state_attributes(item)
            prices.append(price)
    return sorted(prices, key=lambda item: item["time"])


def _weighted_price(start, end, prices, price_times):
    covered_seconds = 0.0
    weighted_price = 0.0
    source_seconds = {}
    source_attributes = {}
    first_index = max(0, bisect_right(price_times, start) - 1)
    for index in range(first_index, len(prices)):
        price = prices[index]
        slot_start = price["time"]
        if slot_start >= end:
            break
        slot_end = prices[index + 1]["time"] if index + 1 < len(prices) else end
        overlap_start = max(start, slot_start)
        overlap_end = min(end, slot_end)
        overlap_seconds = (overlap_end - overlap_start).total_seconds()
        if overlap_seconds <= 0:
            continue
        covered_seconds += overlap_seconds
        weighted_price += overlap_seconds * price["cents_per_kwh"]
        attributes = price.get("attributes", {})
        source_key = (
            attributes.get("price_source"),
            attributes.get("station_id"),
            attributes.get("connector_code"),
        )
        source_seconds[source_key] = source_seconds.get(source_key, 0) + overlap_seconds
        source_attributes[source_key] = attributes
    if covered_seconds <= 0:
        return None, 0.0, {}
    dominant_key = max(source_seconds, key=source_seconds.get) if source_seconds else None
    return (
        weighted_price / covered_seconds,
        covered_seconds,
        source_attributes.get(dominant_key, {}),
    )


def _archive_query_dates(
    sessions,
    effective_prices,
    effective_price_times,
    legacy_prices,
    legacy_price_times,
):
    """Return Nord Pool delivery dates needed for sessions missing history."""
    local_zone = ZoneInfo(Function.hass.config.time_zone or "Europe/Riga")
    local_dates = set()
    for session in sessions:
        start = _parse_datetime(session.get("start"))
        end = _parse_datetime(session.get("end"))
        if start is None or end is None or end <= start:
            continue
        duration_seconds = (end - start).total_seconds()
        effective_rate, effective_covered, _ = _weighted_price(
            start,
            end,
            effective_prices,
            effective_price_times,
        )
        legacy_rate, legacy_covered, _ = _weighted_price(
            start,
            end,
            legacy_prices,
            legacy_price_times,
        )
        if (
            effective_rate is not None
            and effective_covered >= duration_seconds * 0.8
        ) or (
            legacy_rate is not None
            and legacy_covered >= duration_seconds * 0.8
        ):
            continue

        first_date = start.astimezone(local_zone).date()
        last_date = (end - timedelta(microseconds=1)).astimezone(local_zone).date()
        cursor = first_date
        while cursor <= last_date:
            local_dates.add(cursor)
            cursor += timedelta(days=1)

    query_dates = set()
    for local_date in local_dates:
        # The API's delivery date follows CET/CEST. Latvia's first local hour
        # is therefore contained in the preceding API delivery date.
        query_dates.add(local_date - timedelta(days=1))
        query_dates.add(local_date)
    return sorted(query_dates)


async def _get_nordpool_archive_prices(
    sessions,
    effective_prices,
    effective_price_times,
    legacy_prices,
    legacy_price_times,
    settings,
):
    """Fetch only missing historical slots from the official Nord Pool API."""
    dates = _archive_query_dates(
        sessions,
        effective_prices,
        effective_price_times,
        legacy_prices,
        legacy_price_times,
    )
    if not dates:
        return []

    client = async_get_clientsession(Function.hass)
    vat_percent = settings["vat_percent"]

    async def fetch_date(delivery_date):
        cache_key = (
            delivery_date.isoformat()
            + "|"
            + str(round(vat_percent, 4))
        )
        cached = _nordpool_archive_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            async with client.get(
                NORDPOOL_ARCHIVE_API_URL,
                params={
                    "currency": "EUR",
                    "market": "DayAhead",
                    "deliveryArea": NORDPOOL_ARCHIVE_AREA,
                    "date": delivery_date.isoformat(),
                },
                timeout=20,
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
            parsed = parse_nordpool_day_ahead_prices(
                payload,
                vat_percent=vat_percent,
                area=NORDPOOL_ARCHIVE_AREA,
            )
            _nordpool_archive_cache[cache_key] = parsed
            return parsed
        except Exception as exc:
            log.warning(
                "Nord Pool archive update failed for "
                + delivery_date.isoformat()
                + ": "
                + str(exc)[:180]
            )
            return []

    result = []
    for delivery_date in dates:
        day_prices = await fetch_date(delivery_date)
        result.extend(day_prices)

    unique = {}
    for item in result:
        unique[item["time"]] = item
    return sorted(unique.values(), key=lambda item: item["time"])


def _add_session_cost(
    session,
    effective_prices,
    effective_price_times,
    legacy_prices,
    legacy_price_times,
    settings,
    current_effective=None,
):
    start = _parse_datetime(session.get("start"))
    end = _parse_datetime(session.get("end"))
    result = dict(session)
    result.update(
        {
            "grid_energy_kwh": None,
            "spot_rate_c_per_kwh": None,
            "total_rate_c_per_kwh": None,
            "spot_cost_eur": None,
            "delivery_cost_eur": None,
            "total_cost_eur": None,
            "price_coverage_percent": 0.0,
            "price_source": None,
            "price_entity": None,
            "station_name": None,
            "station_id": None,
            "connector_code": None,
        }
    )
    if start is None or end is None or end <= start:
        return result

    duration_seconds = (end - start).total_seconds()
    if duration_seconds <= 0:
        return result

    recovered = session.get("energy_recovered_kwh")
    if recovered is None:
        battery_energy = _number(session.get("estimated_battery_energy_kwh"))
        energy_source = "soc_estimate"
    else:
        battery_energy = _number(recovered)
        energy_source = "renault_recovered_energy"
    if battery_energy <= 0:
        return result

    grid_energy = battery_energy / settings["charging_efficiency"]
    effective_rate, effective_covered, effective_attrs = _weighted_price(
        start,
        end,
        effective_prices,
        effective_price_times,
    )
    price_inferred_from_current_station = False
    if (
        effective_rate is None
        and current_effective
        and current_effective.get("attributes", {}).get("price_source")
        == "elektrum_drive"
        and timedelta(0)
        <= datetime.now(timezone.utc) - end
        <= timedelta(hours=6)
    ):
        effective_rate = current_effective["cents_per_kwh"]
        effective_covered = duration_seconds
        effective_attrs = current_effective["attributes"]
        price_inferred_from_current_station = True
    effective_source = effective_attrs.get("price_source")
    if effective_rate is not None and (
        effective_source == "elektrum_drive"
        or effective_covered >= duration_seconds * 0.8
    ):
        price_source = effective_source or "effective"
        delivery_rate = (
            _number(effective_attrs.get("delivery_price_c_per_kwh")) / 100.0
            if price_source == "home_nord_pool"
            else 0.0
        )
        spot_rate = (
            effective_rate - delivery_rate * 100.0
            if price_source == "home_nord_pool"
            else None
        )
        delivery_cost = grid_energy * delivery_rate
        spot_cost = (
            grid_energy * spot_rate / 100.0
            if spot_rate is not None
            else grid_energy * effective_rate / 100.0
        )
        total_cost = grid_energy * effective_rate / 100.0
        result.update(
            {
                "grid_energy_kwh": round(grid_energy, 2),
                "spot_rate_c_per_kwh": (
                    round(spot_rate, 3) if spot_rate is not None else None
                ),
                "total_rate_c_per_kwh": round(effective_rate, 3),
                "spot_cost_eur": round(spot_cost, 4),
                "delivery_cost_eur": round(delivery_cost, 4),
                "total_cost_eur": round(total_cost, 4),
                "price_coverage_percent": round(
                    min(1.0, effective_covered / duration_seconds) * 100.0,
                    1,
                ),
                "energy_source": energy_source,
                "price_source": price_source,
                "price_entity": EFFECTIVE_PRICE_ENTITY,
                "station_name": effective_attrs.get("station_name"),
                "station_id": effective_attrs.get("station_id"),
                "station_address": effective_attrs.get("station_address"),
                "station_city": effective_attrs.get("station_city"),
                "connector_code": effective_attrs.get("connector_code"),
                "station_partner": effective_attrs.get("station_partner"),
                "postpaid_discount_percent": effective_attrs.get(
                    "postpaid_discount_percent"
                ),
                "price_inferred_from_current_station": (
                    price_inferred_from_current_station
                ),
            }
        )
        return result

    legacy_rate, legacy_covered, legacy_attrs = _weighted_price(
        start,
        end,
        legacy_prices,
        legacy_price_times,
    )
    if legacy_rate is None:
        return result
    spot_rate = legacy_rate
    spot_cost = grid_energy * spot_rate / 100.0
    delivery_rate = settings["delivery_price_incl_vat_eur_per_kwh"]
    delivery_cost = grid_energy * delivery_rate
    total_cost = spot_cost + delivery_cost
    legacy_source = legacy_attrs.get("price_source") or "legacy_nord_pool"
    result.update(
        {
            "grid_energy_kwh": round(grid_energy, 2),
            "spot_rate_c_per_kwh": round(spot_rate, 3),
            "total_rate_c_per_kwh": round(
                spot_rate + delivery_rate * 100.0, 3
            ),
            "spot_cost_eur": round(spot_cost, 4),
            "delivery_cost_eur": round(delivery_cost, 4),
            "total_cost_eur": round(total_cost, 4),
            "price_coverage_percent": round(
                min(1.0, legacy_covered / duration_seconds) * 100.0, 1
            ),
            "energy_source": energy_source,
            "price_source": legacy_source,
            "price_entity": (
                NORDPOOL_ARCHIVE_API_URL
                if legacy_source == "home_nord_pool_archive"
                else _resolve_nordpool_price_entity()
            ),
            "price_from_official_archive": (
                legacy_source == "home_nord_pool_archive"
            ),
        }
    )
    return result


def _sessions_are_contiguous(earlier, later):
    """Return whether two API sessions belong to one uninterrupted stop."""
    earlier_end = _parse_datetime(earlier.get("end"))
    later_start = _parse_datetime(later.get("start"))
    if earlier_end is None or later_start is None:
        return False
    gap = (later_start - earlier_end).total_seconds()
    if gap < 0 or gap > 30 * 60:
        return False
    earlier_soc = _number(earlier.get("end_soc"), float("nan"))
    later_soc = _number(later.get("start_soc"), float("nan"))
    return (
        math.isfinite(earlier_soc)
        and math.isfinite(later_soc)
        and abs(earlier_soc - later_soc) <= 1.0
    )


def _inherit_elektrum_cost(session, reference, settings):
    """Apply a neighboring session's Elektrum station and all-in tariff."""
    result = dict(session)
    rate = _number(reference.get("total_rate_c_per_kwh"), float("nan"))
    recovered = session.get("energy_recovered_kwh")
    if recovered is None or _number(recovered) <= 0:
        battery_energy = _number(session.get("estimated_battery_energy_kwh"))
    else:
        battery_energy = _number(recovered)
    if not math.isfinite(rate) or rate <= 0 or battery_energy <= 0:
        return result

    grid_energy = battery_energy / settings["charging_efficiency"]
    total_cost = grid_energy * rate / 100.0
    result.update(
        {
            "grid_energy_kwh": round(grid_energy, 2),
            "spot_rate_c_per_kwh": None,
            "total_rate_c_per_kwh": round(rate, 3),
            "spot_cost_eur": round(total_cost, 4),
            "delivery_cost_eur": 0.0,
            "total_cost_eur": round(total_cost, 4),
            "price_coverage_percent": reference.get(
                "price_coverage_percent", 0.0
            ),
            "price_source": "elektrum_drive",
            "price_entity": EFFECTIVE_PRICE_ENTITY,
            "station_name": reference.get("station_name"),
            "station_id": reference.get("station_id"),
            "station_address": reference.get("station_address"),
            "station_city": reference.get("station_city"),
            "connector_code": reference.get("connector_code"),
            "station_partner": reference.get("station_partner"),
            "postpaid_discount_percent": reference.get(
                "postpaid_discount_percent"
            ),
            "price_inferred_from_adjacent_session": True,
            "price_inference_reference_start": reference.get("start"),
        }
    )
    return result


def _inherit_adjacent_elektrum_sessions(sessions, settings):
    """Fill short split sessions from a contiguous Elektrum session.

    ``_deduplicate_sessions`` supplies newest-first input. Avoid a key callback
    here because Pyscript evaluates script functions as awaitables when a
    Python builtin invokes them.
    """
    updated = [dict(session) for session in sessions]
    chronological = list(range(len(updated) - 1, -1, -1))
    for _pass in range(2):
        changed = False
        for position, index in enumerate(chronological):
            if updated[index].get("price_source") == "elektrum_drive":
                continue
            candidates = []
            if position > 0:
                previous = chronological[position - 1]
                if (
                    updated[previous].get("price_source") == "elektrum_drive"
                    and _sessions_are_contiguous(updated[previous], updated[index])
                ):
                    candidates.append(previous)
            if position + 1 < len(chronological):
                following = chronological[position + 1]
                if (
                    updated[following].get("price_source") == "elektrum_drive"
                    and _sessions_are_contiguous(updated[index], updated[following])
                ):
                    candidates.append(following)
            if not candidates:
                continue
            updated[index] = _inherit_elektrum_cost(
                updated[index], updated[candidates[0]], settings
            )
            changed = True
        if not changed:
            break
    return updated


def _stored_elektrum_sessions():
    """Keep confirmed public and exact provider prices across API refreshes."""
    stored = {}
    for entity_id in (
        "sensor.zoe_charge_sessions_history_raw",
        "sensor.zoe_charge_sessions_31d_raw",
    ):
        current = Function.hass.states.get(entity_id)
        if current is None:
            continue
        for session in current.attributes.get("sessions") or []:
            key = (session.get("start"), session.get("end"))
            if (
                key != (None, None)
                and session.get("price_source")
                in ({"elektrum_drive"} | EXACT_PROVIDER_PRICE_SOURCES)
            ):
                stored[key] = dict(session)
    return stored


def _inherit_stored_elektrum_sessions(sessions, stored, settings):
    """Reapply a recorded provider classification for the same API session."""
    updated = []
    for session in sessions:
        key = (session.get("start"), session.get("end"))
        reference = stored.get(key)
        if (
            session.get("price_source")
            in ({"elektrum_drive"} | EXACT_PROVIDER_PRICE_SOURCES)
            or reference is None
        ):
            updated.append(dict(session))
            continue
        if reference.get("price_source") in EXACT_PROVIDER_PRICE_SOURCES:
            inherited = dict(session)
            for field in (
                "grid_energy_kwh",
                "spot_rate_c_per_kwh",
                "total_rate_c_per_kwh",
                "spot_cost_eur",
                "delivery_cost_eur",
                "total_cost_eur",
                "price_coverage_percent",
                "energy_source",
                "price_source",
                "price_entity",
                "station_name",
                "station_address",
                "provider",
                "provider_transaction_id",
                "provider_account_id",
                "provider_account_name",
                "provider_reported_cost",
                "provider_reported_energy",
                "provider_total_grid_energy_kwh",
                "provider_total_cost_eur",
                "provider_allocation_fraction",
                "provider_split_session_count",
                "transaction_status",
                "alternate_sources",
            ):
                inherited[field] = reference.get(field)
            inherited["price_preserved_from_previous_update"] = True
            updated.append(inherited)
            continue
        inherited = _inherit_elektrum_cost(session, reference, settings)
        if inherited.get("price_source") == "elektrum_drive":
            inherited["price_preserved_from_previous_update"] = True
        updated.append(inherited)
    return updated


def _deduplicate_sessions(sessions):
    unique = {}
    for session in sessions:
        key = (session.get("start"), session.get("end"))
        if key == (None, None):
            continue
        unique[key] = session
    return sorted(
        unique.values(),
        key=lambda item: item.get("end") or item.get("start") or "",
        reverse=True,
    )


def _is_meaningful_session(session):
    return (
        _number(session.get("soc_gained")) > 0
        and _number(session.get("duration_min")) >= 1
    )


def _build_history_model(sessions, settings):
    observations = []
    ignored_taper_sessions = 0
    ignored_invalid_sessions = 0

    for session in sessions:
        start_soc = _number(session.get("start_soc"))
        end_soc = _number(session.get("end_soc"))
        soc_gained = _number(session.get("soc_gained"))
        duration_min = _number(session.get("duration_min"))

        if start_soc >= 90:
            ignored_taper_sessions += 1
            continue
        if soc_gained < 2 or duration_min < 10 or duration_min > 720:
            ignored_invalid_sessions += 1
            continue

        duration_hours = duration_min / 60.0
        rate_percent_per_hour = soc_gained / duration_hours
        observed_power_kw = (
            soc_gained
            * settings["battery_capacity_kwh"]
            / 100.0
            / settings["charging_efficiency"]
            / duration_hours
        )
        if not (1 <= rate_percent_per_hour <= 35 and 2 <= observed_power_kw <= 22):
            ignored_invalid_sessions += 1
            continue

        taper_fraction = 1.0
        if end_soc > 90:
            taper_fraction = max(0.35, min(1.0, (90 - start_soc) / soc_gained))
        weight = min(soc_gained, 25.0) * taper_fraction
        observations.append(
            {
                "start": session.get("start"),
                "end": session.get("end"),
                "start_soc": round(start_soc, 1),
                "end_soc": round(end_soc, 1),
                "soc_gained": round(soc_gained, 1),
                "duration_min": round(duration_min),
                "power_kw": round(observed_power_kw, 2),
                "rate_percent_per_hour": round(rate_percent_per_hour, 2),
                "weight": round(weight, 2),
            }
        )

    if not observations:
        adaptive_power_kw = settings["default_charging_power_kw"]
        observed_power_kw = settings["default_charging_power_kw"]
        confidence = 0.0
        standard_deviation_kw = 0.0
        total_weight = 0.0
    else:
        total_weight = 0.0
        weighted_power = 0.0
        for item in observations:
            total_weight += item["weight"]
            weighted_power += item["power_kw"] * item["weight"]
        observed_power_kw = weighted_power / total_weight

        weighted_variance = 0.0
        for item in observations:
            weighted_variance += (
                item["weight"] * (item["power_kw"] - observed_power_kw) ** 2
            )
        variance = weighted_variance / total_weight
        standard_deviation_kw = math.sqrt(max(variance, 0.0))

        count_confidence = min(len(observations) / 5.0, 1.0)
        volume_confidence = min(total_weight / 60.0, 1.0)
        consistency = max(
            0.5,
            1.0 - min(standard_deviation_kw / max(observed_power_kw, 1.0), 0.5),
        )
        confidence = min(
            0.95,
            (0.25 * count_confidence + 0.75 * volume_confidence) * consistency,
        )
        adaptive_power_kw = (
            settings["default_charging_power_kw"] * (1.0 - confidence)
            + observed_power_kw * confidence
        )

    adaptive_rate = (
        adaptive_power_kw
        * settings["charging_efficiency"]
        / settings["battery_capacity_kwh"]
        * 100.0
    )
    return {
        "adaptive_power_kw": round(adaptive_power_kw, 2),
        "observed_power_kw": round(observed_power_kw, 2),
        "rate_percent_per_hour": round(adaptive_rate, 2),
        "minutes_per_percent": round(60.0 / adaptive_rate, 2),
        "confidence_percent": round(confidence * 100.0, 1),
        "standard_deviation_kw": round(standard_deviation_kw, 2),
        "eligible_session_count": len(observations),
        "ignored_taper_session_count": ignored_taper_sessions,
        "ignored_invalid_session_count": ignored_invalid_sessions,
        "weighted_soc_points": round(total_weight, 1),
        "observations": observations[:MAX_EXPOSED_HISTORY_SESSIONS],
    }


def _set_sensor(entity_id, value, name, icon, extra=None):
    attrs = {
        "friendly_name": name,
        "icon": icon,
        "attribution": "Data from the Renault My Renault cloud API",
    }
    if extra:
        attrs.update(extra)
    state.set(entity_id, value, attrs)


def _find_active_zoe():
    hass = Function.hass
    entries = hass.config_entries.async_entries("renault")
    if not entries or entries[0].runtime_data is None:
        raise RuntimeError("Renault integration is not loaded")
    for proxy in entries[0].runtime_data.vehicles.values():
        if proxy.details.get_model_code() == MODEL_CODE:
            return proxy
    raise RuntimeError("Active Zoe was not found")


async def _get_charges_with_auth_retry(proxy, start, end):
    try:
        return await proxy._vehicle.get_charges(start, end)
    except Exception as exc:
        if "unauthorized" not in str(exc).lower():
            raise

        log.warning("Renault charge session token was rejected; refreshing it once")
        proxy._vehicle.session._credentials.clear_keys(["gigya_jwt"])
        return await proxy._vehicle.get_charges(start, end)


async def _get_charging_settings_with_auth_retry(proxy):
    try:
        return await proxy._vehicle.get_charging_settings()
    except Exception as exc:
        if "unauthorized" not in str(exc).lower():
            raise

        log.warning("Renault charging settings token was rejected; refreshing it once")
        proxy._vehicle.session._credentials.clear_keys(["gigya_jwt"])
        return await proxy._vehicle.get_charging_settings()


@service(supports_response="optional")
@time_trigger("startup", "period(now, 15min)")
async def zoe_charge_sessions_update():
    """yaml
    name: Update Zoe charge sessions
    description: Reads completed charging sessions from the Renault cloud API.
    """
    global _refresh_in_progress
    if _refresh_in_progress:
        return {"ok": False, "error": "Update already in progress"}

    _refresh_in_progress = True
    update_started = time.monotonic()
    phase_started = update_started
    phase_durations = {}
    try:
        stored_elektrum = _stored_elektrum_sessions()
        proxy = None
        last_error = None
        for attempt in range(7):
            try:
                proxy = _find_active_zoe()
                break
            except RuntimeError as exc:
                last_error = exc
                if attempt < 6:
                    await asyncio.sleep(10)
        if proxy is None:
            raise last_error or RuntimeError("Active Zoe was not found")
        phase_durations["find_vehicle"] = round(time.monotonic() - phase_started, 3)

        now = datetime.now(timezone.utc)
        settings = _cost_settings()
        phase_started = time.monotonic()
        result = await _get_charges_with_auth_retry(
            proxy, now - timedelta(days=LEARNING_HISTORY_DAYS), now
        )
        phase_durations["renault_charges_api"] = round(
            time.monotonic() - phase_started, 3
        )
        charging_settings = None
        phase_started = time.monotonic()
        try:
            charging_settings = _attributes(
                await _get_charging_settings_with_auth_retry(proxy)
            )
        except Exception as exc:
            log.warning("Zoe charging settings update failed: " + str(exc)[:240])
        phase_durations["renault_settings_api"] = round(
            time.monotonic() - phase_started, 3
        )
        phase_started = time.monotonic()
        raw_sessions = _attributes(result).get("charges") or []
        history_sessions = _deduplicate_sessions(
            [
                _normalise_session(item, settings)
                for item in raw_sessions
                if isinstance(item, dict)
            ]
        )
        meaningful_sessions = [
            item for item in history_sessions if _is_meaningful_session(item)
        ]
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        visible_cutoff = max(now - timedelta(days=VISIBLE_HISTORY_DAYS), month_start)
        price_entity = _resolve_nordpool_price_entity()
        phase_durations["normalise_sessions"] = round(
            time.monotonic() - phase_started, 3
        )
        effective_price_history = []
        legacy_price_history = []
        current_effective_price = _current_effective_price()
        phase_started = time.monotonic()
        try:
            effective_price_history = await _get_price_history(
                visible_cutoff - timedelta(hours=1),
                now,
                EFFECTIVE_PRICE_ENTITY,
                include_attributes=True,
            )
        except Exception as exc:
            log.warning(
                "Zoe effective price history update failed: " + str(exc)[:240]
            )
        try:
            legacy_price_history = await _get_price_history(
                visible_cutoff - timedelta(hours=1), now, price_entity
            )
        except Exception as exc:
            log.warning("Zoe Nord Pool price history update failed: " + str(exc)[:240])
        archive_price_history = await _get_nordpool_archive_prices(
            meaningful_sessions,
            effective_price_history,
            [item["time"] for item in effective_price_history],
            legacy_price_history,
            [item["time"] for item in legacy_price_history],
            settings,
        )
        if archive_price_history:
            # Recorder values win on overlap; the archive only fills gaps.
            merged_legacy_prices = {
                item["time"]: item for item in archive_price_history
            }
            for item in legacy_price_history:
                merged_legacy_prices[item["time"]] = item
            legacy_price_history = sorted(
                merged_legacy_prices.values(),
                key=lambda item: item["time"],
            )
        phase_durations["price_history"] = round(
            time.monotonic() - phase_started, 3
        )
        phase_started = time.monotonic()
        effective_price_times = [item["time"] for item in effective_price_history]
        legacy_price_times = [item["time"] for item in legacy_price_history]
        meaningful_sessions = [
            _add_session_cost(
                item,
                effective_price_history,
                effective_price_times,
                legacy_price_history,
                legacy_price_times,
                settings,
                current_effective_price,
            )
            for item in meaningful_sessions
        ]
        meaningful_sessions = _inherit_stored_elektrum_sessions(
            meaningful_sessions,
            stored_elektrum,
            settings,
        )
        meaningful_sessions = _inherit_adjacent_elektrum_sessions(
            meaningful_sessions,
            settings,
        )
        provider_transactions = _provider_transactions()
        meaningful_sessions = apply_provider_transactions(
            meaningful_sessions,
            provider_transactions,
        )
        meaningful_sessions = combine_charge_fragments(meaningful_sessions)
        visible_sessions = [
            item
            for item in meaningful_sessions
            if (_parse_datetime(item.get("end") or item.get("start")) or now)
            >= visible_cutoff
        ]
        model = _build_history_model(history_sessions, settings)
        phase_durations["cost_and_model"] = round(
            time.monotonic() - phase_started, 3
        )
        updated = now.isoformat()
        common = {
            "source": "Renault API charges endpoint",
            "pyscript_revision": PYSCRIPT_REVISION,
            "stored_elektrum_session_count": len(stored_elektrum),
            "provider_transaction_count": len(provider_transactions),
            "nordpool_archive_slot_count": len(archive_price_history),
            "charging_accounts_entity": CHARGING_ACCOUNTS_ENTITY,
            "last_api_update": updated,
            "period_days": VISIBLE_HISTORY_DAYS,
            "period_start": visible_cutoff.isoformat(),
            "battery_capacity_kwh": settings["battery_capacity_kwh"],
            "charging_efficiency": settings["charging_efficiency"],
            "grid_kwh_per_soc_percent": round(
                settings["battery_capacity_kwh"]
                / 100.0
                / settings["charging_efficiency"],
                4,
            ),
            "energy_note": "Renault recovered energy is battery energy, not metered grid input energy",
            "price_entity": EFFECTIVE_PRICE_ENTITY,
            "legacy_price_entity": price_entity,
            "delivery_excl_vat_eur_per_kwh": round(
                settings["delivery_price_excl_vat_eur_per_kwh"],
                7,
            ),
            "energy_vat_percent": settings["vat_percent"],
            "delivery_with_vat_eur_per_kwh": round(
                settings["delivery_price_incl_vat_eur_per_kwh"],
                7,
            ),
            "fallback_consumption_kwh_per_100km": settings[
                "fallback_consumption_kwh_per_100km"
            ],
            "cost_note": "Grid energy divides Renault battery-side energy by charging efficiency, then applies an exact operator transaction, recorded home price, or official Nord Pool archive price",
            "profile_phase_durations_s": dict(phase_durations),
        }

        publish_started = time.monotonic()
        if charging_settings and charging_settings.get("dateTime"):
            _set_sensor(
                "sensor.zoe_charging_settings_updated_raw",
                charging_settings["dateTime"],
                "Zoe charging settings updated",
                "mdi:calendar-clock",
                {
                    **common,
                    "source": "Renault API charging-settings endpoint",
                    "device_class": "timestamp",
                    "api_field": "dateTime",
                },
            )

        _set_sensor(
            "sensor.zoe_charge_sessions_31d_raw",
            len(visible_sessions),
            "Zoe charge sessions (current month)",
            "mdi:ev-station",
            {**common, "sessions": visible_sessions},
        )
        _set_sensor(
            "sensor.zoe_charge_sessions_history_raw",
            len(meaningful_sessions),
            "Zoe charge sessions history",
            "mdi:history",
            {
                **common,
                "period_days": LEARNING_HISTORY_DAYS,
                "sessions": meaningful_sessions[:MAX_EXPOSED_HISTORY_SESSIONS],
                "raw_session_count": len(history_sessions),
                "discarded_zero_session_count": len(history_sessions)
                - len(meaningful_sessions),
            },
        )
        _set_sensor(
            "sensor.zoe_charge_history_power_raw",
            model["adaptive_power_kw"],
            "Zoe learned charging power",
            "mdi:chart-timeline-variant-shimmer",
            {
                **common,
                **model,
                "period_days": LEARNING_HISTORY_DAYS,
                "default_power_kw": settings["default_charging_power_kw"],
                "unit_of_measurement": "kW",
                "device_class": "power",
                "state_class": "measurement",
            },
        )
        _set_sensor(
            "sensor.zoe_charge_history_rate_raw",
            model["rate_percent_per_hour"],
            "Zoe learned charging rate",
            "mdi:battery-sync-outline",
            {
                **common,
                "period_days": LEARNING_HISTORY_DAYS,
                "unit_of_measurement": "%/h",
                "state_class": "measurement",
                "minutes_per_percent": model["minutes_per_percent"],
                "eligible_session_count": model["eligible_session_count"],
            },
        )
        _set_sensor(
            "sensor.zoe_charge_model_confidence_raw",
            model["confidence_percent"],
            "Zoe charging model confidence",
            "mdi:chart-bell-curve-cumulative",
            {
                **common,
                "period_days": LEARNING_HISTORY_DAYS,
                "unit_of_measurement": "%",
                "state_class": "measurement",
                "eligible_session_count": model["eligible_session_count"],
                "ignored_taper_session_count": model["ignored_taper_session_count"],
                "ignored_invalid_session_count": model["ignored_invalid_session_count"],
            },
        )
        _set_sensor(
            "sensor.zoe_charge_sessions_status_raw",
            "ok",
            "Zoe charge sessions status",
            "mdi:cloud-check",
            common,
        )

        if meaningful_sessions:
            latest = meaningful_sessions[0]
            direct_common = {
                **common,
                "source": "Renault API charges endpoint",
            }
            _set_sensor(
                "sensor.zoe_last_charge_start_battery_level_raw",
                latest["start_soc"],
                "Zoe last charge start battery level",
                "mdi:battery-arrow-down-outline",
                {
                    **direct_common,
                    "api_field": "chargeStartBatteryLevel",
                    "device_class": "battery",
                    "state_class": "measurement",
                    "unit_of_measurement": "%",
                },
            )
            _set_sensor(
                "sensor.zoe_last_charge_end_battery_level_raw",
                latest["end_soc"],
                "Zoe last charge end battery level",
                "mdi:battery-arrow-up-outline",
                {
                    **direct_common,
                    "api_field": "chargeEndBatteryLevel",
                    "device_class": "battery",
                    "state_class": "measurement",
                    "unit_of_measurement": "%",
                },
            )
            if latest["energy_recovered_kwh"] is not None:
                _set_sensor(
                    "sensor.zoe_last_charge_energy_recovered_raw",
                    latest["energy_recovered_kwh"],
                    "Zoe last charge energy recovered",
                    "mdi:battery-charging-high",
                    {
                        **direct_common,
                        "api_field": "chargeEnergyRecovered",
                        "device_class": "energy",
                        "state_class": "measurement",
                        "unit_of_measurement": "kWh",
                    },
                )
            _set_sensor(
                "sensor.zoe_last_charge_energy_estimate_raw",
                latest["estimated_battery_energy_kwh"],
                "Zoe last charge energy estimate",
                "mdi:battery-charging",
                {
                    **common,
                    "device_class": "energy",
                    "state_class": "measurement",
                    "unit_of_measurement": "kWh",
                },
            )
            _set_sensor(
                "sensor.zoe_last_charge_duration_raw",
                latest["duration_min"],
                "Zoe last charge duration",
                "mdi:timer-outline",
                {
                    **direct_common,
                    "api_field": "chargeDuration",
                    "device_class": "duration",
                    "state_class": "measurement",
                    "unit_of_measurement": "min",
                },
            )
            _set_sensor(
                "sensor.zoe_last_charge_soc_gained_raw",
                latest["soc_gained"],
                "Zoe last charge SOC gained",
                "mdi:battery-plus",
                {
                    **common,
                    "state_class": "measurement",
                    "unit_of_measurement": "%",
                    "start_soc": latest["start_soc"],
                    "end_soc": latest["end_soc"],
                },
            )
            _set_sensor(
                "sensor.zoe_last_charge_start_raw",
                latest["start"],
                "Zoe last charge start",
                "mdi:clock-start",
                {
                    **direct_common,
                    "api_field": "chargeStartDate",
                    "device_class": "timestamp",
                },
            )
            _set_sensor(
                "sensor.zoe_last_charge_end_raw",
                latest["end"],
                "Zoe last charge end",
                "mdi:clock-end",
                {
                    **direct_common,
                    "api_field": "chargeEndDate",
                    "device_class": "timestamp",
                },
            )
            _set_sensor(
                "sensor.zoe_last_charge_status_raw",
                latest["status"] or "unknown",
                "Zoe last charge status",
                "mdi:check-circle-outline",
                {**direct_common, "api_field": "chargeEndStatus"},
            )

        phase_durations["publish_states"] = round(
            time.monotonic() - publish_started, 3
        )
        total_duration = round(time.monotonic() - update_started, 3)
        log.debug(
            "Zoe charge session update profile: "
            + str({"total": total_duration, **phase_durations})
        )
        return {
            "ok": True,
            "count_31d": len(visible_sessions),
            "count_history": len(meaningful_sessions),
            "raw_count_history": len(history_sessions),
            "model": model,
            "latest": meaningful_sessions[0] if meaningful_sessions else None,
            "profile_phase_durations_s": phase_durations,
            "profile_total_duration_s": total_duration,
        }
    except Exception as exc:
        message = str(exc)[:240]
        log.warning("Zoe charge session update failed: " + message)
        _set_sensor(
            "sensor.zoe_charge_sessions_status_raw",
            "error",
            "Zoe charge sessions status",
            "mdi:cloud-alert",
            {
                "error": message,
                "last_api_update": datetime.now(timezone.utc).isoformat(),
            },
        )
        return {"ok": False, "error": message}
    finally:
        _refresh_in_progress = False
