# ruff: noqa: F821 - Pyscript injects state, service, time_trigger, and log.

import asyncio
import math
from datetime import datetime, timedelta, timezone
from functools import partial

from custom_components.pyscript.function import Function
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states


MODEL_CODE = "X102VE"
BATTERY_CAPACITY_KWH = 52.0
CHARGING_EFFICIENCY = 0.9
DEFAULT_CHARGING_POWER_KW = 11.0
VISIBLE_HISTORY_DAYS = 31
LEARNING_HISTORY_DAYS = 180
MAX_EXPOSED_HISTORY_SESSIONS = 50
UPDATE_INTERVAL_MINUTES = 15
DYNAMIC_PRICE_ENTITY = "sensor.renault_zoe_new_nord_pool_price"
LEGACY_PRICE_ENTITY = "sensor.nordpool_kwh_lv_eur_3_10_021"
DELIVERY_WITH_VAT_EUR_PER_KWH = 0.03962 * 1.21

_refresh_in_progress = False


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


def _normalise_session(raw):
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
            BATTERY_CAPACITY_KWH * soc_gained / 100.0, 2
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


def _resolve_price_entity():
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


async def _get_price_history(start, end, price_entity):
    hass = Function.hass
    query = partial(
        get_significant_states,
        hass,
        start,
        end,
        [price_entity],
        include_start_time_state=True,
        significant_changes_only=False,
        no_attributes=True,
    )
    result = await get_instance(hass).async_add_executor_job(query)
    prices = []
    for item in result.get(price_entity, []):
        item_time = _history_state_time(item)
        item_value = _number(_history_state_value(item), float("nan"))
        if item_time is not None and math.isfinite(item_value):
            prices.append({"time": item_time, "cents_per_kwh": item_value})
    return sorted(prices, key=lambda item: item["time"])


def _add_session_cost(session, prices):
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
        }
    )
    if start is None or end is None or end <= start or not prices:
        return result

    covered_seconds = 0.0
    weighted_price = 0.0
    for index, price in enumerate(prices):
        slot_start = price["time"]
        slot_end = prices[index + 1]["time"] if index + 1 < len(prices) else end
        overlap_start = max(start, slot_start)
        overlap_end = min(end, slot_end)
        overlap_seconds = (overlap_end - overlap_start).total_seconds()
        if overlap_seconds > 0:
            covered_seconds += overlap_seconds
            weighted_price += overlap_seconds * price["cents_per_kwh"]

    duration_seconds = (end - start).total_seconds()
    if covered_seconds <= 0 or duration_seconds <= 0:
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

    grid_energy = battery_energy / CHARGING_EFFICIENCY
    spot_rate = weighted_price / covered_seconds
    spot_cost = grid_energy * spot_rate / 100.0
    delivery_cost = grid_energy * DELIVERY_WITH_VAT_EUR_PER_KWH
    total_cost = spot_cost + delivery_cost
    result.update(
        {
            "grid_energy_kwh": round(grid_energy, 2),
            "spot_rate_c_per_kwh": round(spot_rate, 3),
            "total_rate_c_per_kwh": round(
                spot_rate + DELIVERY_WITH_VAT_EUR_PER_KWH * 100.0, 3
            ),
            "spot_cost_eur": round(spot_cost, 4),
            "delivery_cost_eur": round(delivery_cost, 4),
            "total_cost_eur": round(total_cost, 4),
            "price_coverage_percent": round(
                min(1.0, covered_seconds / duration_seconds) * 100.0, 1
            ),
            "energy_source": energy_source,
        }
    )
    return result


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


def _build_history_model(sessions):
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
            * BATTERY_CAPACITY_KWH
            / 100.0
            / CHARGING_EFFICIENCY
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
        adaptive_power_kw = DEFAULT_CHARGING_POWER_KW
        observed_power_kw = DEFAULT_CHARGING_POWER_KW
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
            DEFAULT_CHARGING_POWER_KW * (1.0 - confidence)
            + observed_power_kw * confidence
        )

    adaptive_rate = (
        adaptive_power_kw * CHARGING_EFFICIENCY / BATTERY_CAPACITY_KWH * 100.0
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
    try:
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

        now = datetime.now(timezone.utc)
        result = await _get_charges_with_auth_retry(
            proxy, now - timedelta(days=LEARNING_HISTORY_DAYS), now
        )
        charging_settings = None
        try:
            charging_settings = _attributes(
                await _get_charging_settings_with_auth_retry(proxy)
            )
        except Exception as exc:
            log.warning("Zoe charging settings update failed: " + str(exc)[:240])
        raw_sessions = _attributes(result).get("charges") or []
        history_sessions = _deduplicate_sessions(
            [
                _normalise_session(item)
                for item in raw_sessions
                if isinstance(item, dict)
            ]
        )
        meaningful_sessions = [
            item for item in history_sessions if _is_meaningful_session(item)
        ]
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        visible_cutoff = max(now - timedelta(days=VISIBLE_HISTORY_DAYS), month_start)
        price_entity = _resolve_price_entity()
        price_history = []
        try:
            price_history = await _get_price_history(
                visible_cutoff - timedelta(hours=1), now, price_entity
            )
        except Exception as exc:
            log.warning("Zoe Nord Pool price history update failed: " + str(exc)[:240])
        meaningful_sessions = [
            _add_session_cost(item, price_history) for item in meaningful_sessions
        ]
        visible_sessions = [
            item
            for item in meaningful_sessions
            if (_parse_datetime(item.get("end") or item.get("start")) or now)
            >= visible_cutoff
        ]
        model = _build_history_model(history_sessions)
        updated = now.isoformat()
        common = {
            "source": "Renault API charges endpoint",
            "last_api_update": updated,
            "period_days": VISIBLE_HISTORY_DAYS,
            "period_start": visible_cutoff.isoformat(),
            "battery_capacity_kwh": BATTERY_CAPACITY_KWH,
            "charging_efficiency": CHARGING_EFFICIENCY,
            "grid_kwh_per_soc_percent": round(
                BATTERY_CAPACITY_KWH / 100.0 / CHARGING_EFFICIENCY, 4
            ),
            "energy_note": "Renault recovered energy is battery energy, not metered grid input energy",
            "price_entity": price_entity,
            "delivery_with_vat_eur_per_kwh": round(DELIVERY_WITH_VAT_EUR_PER_KWH, 7),
            "cost_note": "Grid energy divides Renault battery-side energy by charging efficiency before applying Nord Pool and delivery prices",
        }

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
                "default_power_kw": DEFAULT_CHARGING_POWER_KW,
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

        return {
            "ok": True,
            "count_31d": len(visible_sessions),
            "count_history": len(meaningful_sessions),
            "raw_count_history": len(history_sessions),
            "model": model,
            "latest": meaningful_sessions[0] if meaningful_sessions else None,
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
