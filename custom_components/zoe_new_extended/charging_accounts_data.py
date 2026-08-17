"""Pure helpers for charging-account transaction data."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
import math
import re
import unicodedata
from typing import Any


ELEKTRUM_SOURCE = "elektrum_drive"
MOBILLY_SOURCE = "mobilly"
IGNITIS_SOURCE = "ignitis_on"
IKRAUTAS_SOURCE = "ikrautas"
DIRECT_OPERATOR_SOURCES = frozenset(
    {ELEKTRUM_SOURCE, IGNITIS_SOURCE, IKRAUTAS_SOURCE}
)
_ELEKTRUM_MATCH_SECONDS = 20 * 60
_CHARGE_FRAGMENT_GAP_SECONDS = 30 * 60


def parse_nordpool_day_ahead_prices(
    payload: Mapping[str, Any],
    *,
    vat_percent: float,
    area: str = "LV",
) -> list[dict[str, Any]]:
    """Normalize official Nord Pool archive prices to VAT-inclusive c/kWh."""
    if str(payload.get("currency") or "EUR").upper() != "EUR":
        raise ValueError("Nord Pool archive currency is not EUR")

    multiplier = (1.0 + max(0.0, float(vat_percent)) / 100.0) / 10.0
    result: list[dict[str, Any]] = []
    entries = payload.get("multiAreaEntries")
    if not isinstance(entries, list):
        return result

    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        area_values = entry.get("entryPerArea")
        if not isinstance(area_values, Mapping):
            continue
        raw_price = _as_float(area_values.get(area))
        start = _parse_datetime(entry.get("deliveryStart"))
        end = _parse_datetime(entry.get("deliveryEnd"))
        if (
            raw_price is None
            or not math.isfinite(raw_price)
            or start is None
            or end is None
            or end <= start
        ):
            continue
        result.append(
            {
                "time": start,
                "end": end,
                "cents_per_kwh": round(raw_price * multiplier, 6),
                "attributes": {
                    "price_source": "home_nord_pool_archive",
                    "archive_source": "Nord Pool DayAheadPrices",
                    "spot_price_includes_vat": True,
                },
            }
        )
    return sorted(result, key=lambda item: item["time"])


def charging_account_identity(account: Mapping[str, Any]) -> tuple[str, ...]:
    """Return a stable identity for one configured charging account."""
    account_type = str(account.get("type") or "").strip().casefold()
    identity_fields = {
        "ignitis_on": ("email",),
        "ikrautas": ("email",),
        "mobilly": ("mobile_phone", "username"),
        "elektrum_drive": ("agreement_id", "phone"),
    }.get(
        account_type,
        ("email", "mobile_phone", "phone", "username"),
    )
    for field in identity_fields:
        value = str(account.get(field) or "").strip().casefold()
        if value:
            return account_type, field, value
    account_id = str(account.get("id") or "").strip()
    return account_type, "id", account_id


def deduplicate_account_records(
    records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Merge duplicate account records while preserving the original ID.

    Repeated authorization attempts previously appended another record for the
    same operator identity. Later non-empty values are preferred so a renewed
    token replaces an expired one without creating a second coordinator task.
    """
    result: list[dict[str, Any]] = []
    indexes: dict[tuple[str, ...], int] = {}
    for raw in records:
        account = dict(raw)
        identity = charging_account_identity(account)
        existing_index = indexes.get(identity)
        if existing_index is None:
            indexes[identity] = len(result)
            result.append(account)
            continue

        existing = result[existing_index]
        original_id = existing.get("id")
        for key, value in account.items():
            if value is not None and value != "" and value != [] and value != {}:
                existing[key] = value
        if original_id:
            existing["id"] = original_id
    return result


def elektrum_profile_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a sanitized Elektrum profile/authentication state."""
    data = payload.get("data")
    if not isinstance(data, Mapping):
        return {
            "auth_state": "unknown",
            "profile_type": None,
            "agreement_linked": False,
        }
    profile_type = _as_int(data.get("type"))
    agreements = data.get("agreements")
    agreement_items = agreements if isinstance(agreements, list) else []
    agreement_linked = profile_type == 3 or any(
        isinstance(item, Mapping) and bool(item.get("selected"))
        for item in agreement_items
    )
    return {
        "auth_state": (
            "agreement_linked"
            if agreement_linked
            else "agreement_required"
            if profile_type == 0
            else "authenticated"
        ),
        "profile_type": profile_type,
        "agreement_linked": agreement_linked,
        "agreement_count": len(agreement_items),
    }


def elektrum_token_can_replace(
    current_payload: Mapping[str, Any] | None,
    candidate_payload: Mapping[str, Any],
    *,
    saved_agreement: bool = False,
) -> bool:
    """Prevent an anonymous app profile from replacing a linked session."""
    candidate = elektrum_profile_state(candidate_payload)
    if candidate["auth_state"] == "unknown":
        return False
    current = elektrum_profile_state(current_payload or {})
    must_remain_linked = saved_agreement or current["agreement_linked"]
    return not must_remain_linked or candidate["agreement_linked"]


def elektrum_month_keys(
    reference: datetime,
    *,
    history_days: int,
) -> list[str]:
    """Return newest-first calendar months covering a history window."""
    reference_utc = (
        reference.replace(tzinfo=UTC)
        if reference.tzinfo is None
        else reference.astimezone(UTC)
    )
    oldest = reference_utc - timedelta(days=max(0, history_days))
    year = reference_utc.year
    month = reference_utc.month
    result: list[str] = []
    while (year, month) >= (oldest.year, oldest.month):
        result.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return result


def parse_elektrum_transactions(
    payload: Mapping[str, Any],
    *,
    account_id: str,
    account_name: str,
) -> list[dict[str, Any]]:
    """Normalize completed Elektrum Drive charging transactions."""
    raw_data = payload.get("data", [])
    if isinstance(raw_data, Mapping):
        raw_data = raw_data.get("transactions", raw_data.get("items", []))
    if not isinstance(raw_data, list):
        return []

    result: list[dict[str, Any]] = []
    for raw in raw_data:
        if not isinstance(raw, Mapping):
            continue
        item = raw.get("item")
        if not isinstance(item, Mapping):
            continue
        if _as_int(raw.get("status")) != 2:
            continue
        start = _timestamp_iso(item.get("startedAt"))
        end = _timestamp_iso(item.get("endedAt"))
        if start is None or end is None:
            continue

        energy_wh = _as_float(item.get("energyUsed"))
        energy_kwh = (
            round(energy_wh / 1000.0, 3)
            if energy_wh is not None and energy_wh >= 0
            else None
        )
        amount_cents = _as_float(raw.get("amount"))
        cost_eur = (
            round(amount_cents / 100.0, 4)
            if amount_cents is not None
            else None
        )
        transaction_id = str(raw.get("id") or "") or None
        rate = (
            round(cost_eur / energy_kwh * 100.0, 3)
            if cost_eur is not None and energy_kwh and energy_kwh > 0
            else None
        )
        result.append(
            {
                "transaction_id": transaction_id,
                "source_page": "elektrum_drive_app",
                "source_account_type": ELEKTRUM_SOURCE,
                "account_id": account_id,
                "account_name": account_name,
                "provider": "Elektrum Drive",
                "operator": "Elektrum Drive",
                "station_name": item.get("stationName"),
                "station_address": item.get("stationAddress"),
                "start": start,
                "end": end,
                "duration_minutes": _duration_minutes(item, start, end),
                "energy_kwh": energy_kwh,
                "cost_eur": cost_eur,
                "total_cost_eur": cost_eur,
                "total_rate_c_per_kwh": rate,
                "tariff_charging_price_c_per_kwh": _as_float(
                    item.get("tariffChargingPriceFull")
                ),
                "tariff_charging_unit": item.get("tariffChargingUnit"),
                "tariff_connection_price_cents": _as_float(
                    item.get("tariffConnectionPriceFull")
                ),
                "tariff_connection_unit": item.get("tariffConnectionUnit"),
                "transaction_status": _transaction_status(raw.get("status")),
                "transaction_type": raw.get("type"),
                "invoice_available": raw.get("invoiceAvailable"),
                "price_source": "elektrum_drive_app",
                "elektrum_transaction": True,
                "provider_reported_cost": cost_eur is not None,
                "provider_reported_energy": energy_kwh is not None,
            }
        )
    return sorted(result, key=lambda record: record["end"], reverse=True)


def tag_account_transactions(
    records: Iterable[Mapping[str, Any]],
    *,
    account_id: str,
    account_name: str,
    account_type: str,
) -> list[dict[str, Any]]:
    """Attach a non-secret account reference to normalized transactions."""
    result = []
    for raw in records:
        record = dict(raw)
        record["account_id"] = account_id
        record["account_name"] = account_name
        record["source_account_type"] = account_type
        result.append(record)
    return result


def merge_account_transactions(
    *record_groups: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Merge accounts and prefer an operator app over an overlapping reseller."""
    records = [dict(item) for group in record_groups for item in group]
    records = _deduplicate_same_source(records)

    direct_operator_records = [
        record
        for record in records
        if record.get("source_account_type") in DIRECT_OPERATOR_SOURCES
    ]
    consumed_mobilly: set[int] = set()
    for primary in direct_operator_records:
        candidates = [
            (index, candidate)
            for index, candidate in enumerate(records)
            if index not in consumed_mobilly
            and candidate.get("source_account_type") == MOBILLY_SOURCE
            and _operator_transaction_matches(primary, candidate)
            and _same_charge(primary, candidate)
        ]
        if not candidates:
            continue
        index, alternate = min(
            candidates,
            key=lambda pair: _interval_distance(primary, pair[1]),
        )
        consumed_mobilly.add(index)
        _attach_alternate(primary, alternate)

    merged = [
        record
        for index, record in enumerate(records)
        if index not in consumed_mobilly
    ]
    return sorted(merged, key=lambda record: record.get("end") or "", reverse=True)


def _operator_transaction_matches(
    primary: Mapping[str, Any],
    alternate: Mapping[str, Any],
) -> bool:
    source = primary.get("source_account_type")
    if source == ELEKTRUM_SOURCE:
        return bool(alternate.get("elektrum_transaction"))

    primary_names = {
        _normalize(primary.get("provider")),
        _normalize(primary.get("operator")),
    }
    alternate_text = " ".join(
        filter(
            None,
            (
                _normalize(alternate.get("provider")),
                _normalize(alternate.get("operator")),
                _normalize(alternate.get("station_name")),
                _normalize(alternate.get("note")),
                _normalize(alternate.get("description")),
            ),
        )
    )
    aliases = {
        IGNITIS_SOURCE: ("ignitis",),
        IKRAUTAS_SOURCE: ("ikrautas",),
    }
    needles = {value for value in primary_names if value}
    needles.update(aliases.get(str(source), ()))
    return any(needle in alternate_text for needle in needles)


def apply_provider_transactions(
    sessions: Iterable[Mapping[str, Any]],
    transactions: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply exact provider energy and cost to matching Renault sessions.

    Renault can split one physical charge into several API rows. When that
    happens, expose one combined session with the provider's exact totals.
    Keeping one row prevents a single paid charge from looking like multiple
    sessions and avoids rounding the provider total across fragments.
    """
    provider_records = sorted(
        (dict(item) for item in transactions),
        key=lambda item: item.get("end") or "",
    )
    result = _expand_multi_transaction_sessions(sessions, provider_records)
    for transaction in provider_records:
        candidates = [
            index
            for index, session in enumerate(result)
            if _interval_matches(session, transaction)
        ]
        if not candidates:
            continue

        fragments = [result[index] for index in candidates]
        combined = _combine_provider_sessions(fragments, transaction)
        result = [
            session for index, session in enumerate(result) if index not in candidates
        ]
        result.append(combined)

    return sorted(
        result,
        key=lambda item: item.get("end") or item.get("start") or "",
        reverse=True,
    )


def _expand_multi_transaction_sessions(
    sessions: Iterable[Mapping[str, Any]],
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Restore Renault fragments when one combined row spans several payments."""
    result: list[dict[str, Any]] = []
    for raw_session in sessions:
        session = dict(raw_session)
        fragments = session.get("renault_session_fragments")
        matching_transactions = sum(
            1 for transaction in transactions if _interval_matches(session, transaction)
        )
        if (
            matching_transactions <= 1
            or not isinstance(fragments, list)
            or len(fragments) <= 1
        ):
            result.append(session)
            continue

        normalized_fragments = [
            dict(fragment) for fragment in fragments if isinstance(fragment, Mapping)
        ]
        if len(normalized_fragments) <= 1:
            result.append(session)
            continue

        weights = [_fragment_weight(fragment) for fragment in normalized_fragments]
        total_weight = sum(weights) or float(len(normalized_fragments))
        for fragment, weight in zip(normalized_fragments, weights, strict=True):
            expanded = dict(session)
            expanded.update(fragment)
            start = _parse_datetime(fragment.get("start"))
            end = _parse_datetime(fragment.get("end"))
            if start is not None and end is not None:
                expanded["duration_min"] = max(
                    0, round((end - start).total_seconds() / 60.0)
                )
            start_soc = _as_float(fragment.get("start_soc"))
            end_soc = _as_float(fragment.get("end_soc"))
            if start_soc is not None and end_soc is not None:
                expanded["soc_gained"] = round(max(0.0, end_soc - start_soc), 1)
            fraction = weight / total_weight
            for field in (
                "estimated_battery_energy_kwh",
                "energy_recovered_kwh",
                "grid_energy_kwh",
                "spot_cost_eur",
                "delivery_cost_eur",
                "total_cost_eur",
            ):
                value = _as_float(session.get(field))
                if value is not None:
                    expanded[field] = round(value * fraction, 4)
            expanded["combined_charge"] = False
            expanded["combined_fragment_count"] = 1
            expanded["renault_session_fragments"] = [fragment]
            result.append(expanded)
    return result


def _fragment_weight(fragment: Mapping[str, Any]) -> float:
    """Prefer SOC gain, then elapsed time, when allocating combined estimates."""
    start_soc = _as_float(fragment.get("start_soc"))
    end_soc = _as_float(fragment.get("end_soc"))
    if start_soc is not None and end_soc is not None and end_soc > start_soc:
        return end_soc - start_soc
    start = _parse_datetime(fragment.get("start"))
    end = _parse_datetime(fragment.get("end"))
    if start is not None and end is not None and end > start:
        return (end - start).total_seconds()
    return 1.0


def combine_charge_fragments(
    sessions: Iterable[Mapping[str, Any]],
    *,
    max_gap_seconds: int = _CHARGE_FRAGMENT_GAP_SECONDS,
) -> list[dict[str, Any]]:
    """Combine stop/restart fragments belonging to one physical charge.

    Renault creates a new API row after a remote stop and subsequent restart.
    Adjacent rows are combined only when SOC is continuous and their known
    station/provider identity agrees, which keeps unrelated charges separate.
    """
    chronological = sorted(
        (dict(item) for item in sessions),
        key=lambda item: item.get("start") or item.get("end") or "",
    )
    groups: list[list[dict[str, Any]]] = []
    for session in chronological:
        if groups and _fragments_match(
            groups[-1][-1], session, max_gap_seconds=max_gap_seconds
        ):
            groups[-1].append(session)
        else:
            groups.append([session])

    result = [
        _combine_charge_fragment_group(group) if len(group) > 1 else group[0]
        for group in groups
    ]
    return sorted(
        result,
        key=lambda item: item.get("end") or item.get("start") or "",
        reverse=True,
    )


def _fragments_match(
    earlier: Mapping[str, Any],
    later: Mapping[str, Any],
    *,
    max_gap_seconds: int,
) -> bool:
    earlier_transaction = earlier.get("provider_transaction_id")
    later_transaction = later.get("provider_transaction_id")
    if earlier_transaction or later_transaction:
        return bool(
            earlier_transaction
            and later_transaction
            and earlier_transaction == later_transaction
        )

    earlier_end = _parse_datetime(earlier.get("end"))
    later_start = _parse_datetime(later.get("start"))
    if earlier_end is None or later_start is None:
        return False
    gap_seconds = (later_start - earlier_end).total_seconds()
    if gap_seconds < 0 or gap_seconds > max_gap_seconds:
        return False

    earlier_soc = _as_float(earlier.get("end_soc"))
    later_soc = _as_float(later.get("start_soc"))
    if (
        earlier_soc is None
        or later_soc is None
        or abs(earlier_soc - later_soc) > 1.0
    ):
        return False

    earlier_identity = _charge_location_identity(earlier)
    later_identity = _charge_location_identity(later)
    return not (
        earlier_identity
        and later_identity
        and earlier_identity != later_identity
    )


def _charge_location_identity(session: Mapping[str, Any]) -> str:
    for key in ("station_id", "station_name", "station_address", "provider"):
        value = _normalize(session.get(key))
        if value:
            return value
    source = str(session.get("price_source") or "")
    if source in {"elektrum_drive", "elektrum_drive_app", "mobilly"}:
        return source
    return ""


def _combine_charge_fragment_group(
    fragments: list[dict[str, Any]],
) -> dict[str, Any]:
    first = fragments[0]
    last = fragments[-1]
    combined = dict(first)
    start = first.get("start")
    end = last.get("end")
    start_time = _parse_datetime(start)
    end_time = _parse_datetime(end)
    active_duration = sum(
        _as_float(item.get("duration_min")) or 0.0 for item in fragments
    )
    elapsed_duration = (
        max(0.0, (end_time - start_time).total_seconds() / 60.0)
        if start_time is not None and end_time is not None
        else active_duration
    )
    start_soc = _as_float(first.get("start_soc"))
    end_soc = _as_float(last.get("end_soc"))
    battery_energy = sum(
        _as_float(item.get("estimated_battery_energy_kwh")) or 0.0
        for item in fragments
    )
    grid_values = [_as_float(item.get("grid_energy_kwh")) for item in fragments]
    cost_values = [_as_float(item.get("total_cost_eur")) for item in fragments]
    grid_energy = (
        sum(value for value in grid_values if value is not None)
        if all(value is not None for value in grid_values)
        else None
    )
    total_cost = (
        sum(value for value in cost_values if value is not None)
        if all(value is not None for value in cost_values)
        else None
    )
    rate = (
        total_cost / grid_energy * 100.0
        if total_cost is not None and grid_energy and grid_energy > 0
        else None
    )
    field_source = next(
        (item for item in fragments if _charge_location_identity(item)), first
    )
    combined.update(
        {
            "start": start,
            "end": end,
            "duration_min": round(elapsed_duration),
            "active_duration_min": round(active_duration),
            "pause_duration_min": round(max(0.0, elapsed_duration - active_duration)),
            "start_soc": start_soc,
            "end_soc": end_soc,
            "soc_gained": (
                round(max(0.0, end_soc - start_soc), 1)
                if start_soc is not None and end_soc is not None
                else round(
                    sum(_as_float(item.get("soc_gained")) or 0.0 for item in fragments),
                    1,
                )
            ),
            "estimated_battery_energy_kwh": round(battery_energy, 2),
            "grid_energy_kwh": round(grid_energy, 2) if grid_energy is not None else None,
            "total_cost_eur": round(total_cost, 4) if total_cost is not None else None,
            "total_rate_c_per_kwh": round(rate, 3) if rate is not None else None,
            "status": last.get("status"),
            "combined_charge": True,
            "combined_fragment_count": len(fragments),
            "renault_session_fragments": [
                {
                    "start": item.get("start"),
                    "end": item.get("end"),
                    "start_soc": item.get("start_soc"),
                    "end_soc": item.get("end_soc"),
                }
                for item in fragments
            ],
        }
    )
    for key in (
        "station_id",
        "station_name",
        "station_address",
        "station_city",
        "provider",
        "connector_code",
        "price_source",
        "price_entity",
    ):
        if field_source.get(key) is not None:
            combined[key] = field_source[key]
    return combined


def _combine_provider_sessions(
    sessions: list[dict[str, Any]], transaction: Mapping[str, Any]
) -> dict[str, Any]:
    """Combine Renault fragments and attach one exact provider transaction."""
    chronological = sorted(sessions, key=lambda item: item.get("start") or "")
    first = chronological[0]
    last = chronological[-1]
    combined = dict(first)
    source_fragments = []
    for item in chronological:
        nested = item.get("renault_session_fragments")
        if isinstance(nested, list) and nested:
            source_fragments.extend(dict(fragment) for fragment in nested)
        else:
            source_fragments.append(
                {
                    "start": item.get("start"),
                    "end": item.get("end"),
                    "start_soc": item.get("start_soc"),
                    "end_soc": item.get("end_soc"),
                }
            )

    start = transaction.get("start") or first.get("start")
    end = (
        last.get("end")
        if transaction.get("end_inferred")
        else transaction.get("end") or last.get("end")
    )
    start_time = _parse_datetime(start)
    end_time = _parse_datetime(end)
    duration = _as_float(transaction.get("duration_minutes"))
    if duration is None and start_time is not None and end_time is not None:
        duration = max(0.0, (end_time - start_time).total_seconds() / 60.0)

    start_soc = _as_float(first.get("start_soc"))
    end_soc = _as_float(last.get("end_soc"))
    soc_gained = (
        max(0.0, end_soc - start_soc)
        if start_soc is not None and end_soc is not None
        else sum(_as_float(item.get("soc_gained")) or 0.0 for item in chronological)
    )
    estimated_battery = sum(
        _as_float(item.get("estimated_battery_energy_kwh")) or 0.0
        for item in chronological
    )
    recovered_values = [
        _as_float(item.get("energy_recovered_kwh")) for item in chronological
    ]
    recovered_energy = (
        sum(value for value in recovered_values if value is not None)
        if any(value is not None for value in recovered_values)
        else None
    )

    exact_energy = _as_float(transaction.get("energy_kwh"))
    exact_cost = _as_float(
        transaction.get("total_cost_eur", transaction.get("cost_eur"))
    )
    exact_rate = (
        exact_cost / exact_energy * 100.0
        if exact_cost is not None and exact_energy and exact_energy > 0
        else _as_float(transaction.get("total_rate_c_per_kwh"))
    )

    combined.update(
        {
            "start": start,
            "end": end,
            "duration_min": round(duration) if duration is not None else None,
            "start_soc": round(start_soc, 1) if start_soc is not None else None,
            "end_soc": round(end_soc, 1) if end_soc is not None else None,
            "soc_gained": round(soc_gained, 1),
            "estimated_battery_energy_kwh": round(estimated_battery, 2),
            "energy_recovered_kwh": (
                round(recovered_energy, 2) if recovered_energy is not None else None
            ),
            "status": last.get("status"),
            "grid_energy_kwh": exact_energy,
            "energy_source": "provider_meter" if exact_energy is not None else None,
            "spot_cost_eur": None,
            "delivery_cost_eur": None,
            "total_cost_eur": exact_cost,
            "total_rate_c_per_kwh": (
                round(exact_rate, 3) if exact_rate is not None else None
            ),
            "price_source": transaction.get("price_source"),
            "price_entity": "sensor.renault_zoe_new_charging_accounts",
            "price_coverage_percent": 100.0,
            "source_page": transaction.get("source_page"),
            "station_id": transaction.get("station_id"),
            "station_name": transaction.get("station_name")
            or transaction.get("provider"),
            "station_address": transaction.get("station_address"),
            "connector_code": transaction.get("connector_code"),
            "provider": transaction.get("provider"),
            "operator": transaction.get("operator"),
            "receipt_url": transaction.get("receipt_url"),
            "provider_transaction_id": transaction.get("transaction_id"),
            "provider_account_id": transaction.get("account_id"),
            "provider_account_name": transaction.get("account_name"),
            "provider_reported_cost": transaction.get(
                "provider_reported_cost", exact_cost is not None
            ),
            "provider_reported_energy": transaction.get(
                "provider_reported_energy", exact_energy is not None
            ),
            "provider_total_grid_energy_kwh": exact_energy,
            "provider_total_cost_eur": exact_cost,
            "provider_allocation_fraction": 1.0,
            "provider_split_session_count": len(source_fragments),
            "provider_combined_session": len(source_fragments) > 1,
            "renault_session_fragments": source_fragments,
            "transaction_status": transaction.get("transaction_status"),
            "alternate_sources": transaction.get("alternate_sources", []),
        }
    )
    return combined


def _deduplicate_same_source(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    keys: dict[tuple[Any, ...], int] = {}
    for record in records:
        source = record.get("source_account_type") or record.get("price_source")
        transaction_id = record.get("transaction_id")
        if transaction_id:
            # Mobilly IDs are account-local. The interval distinguishes equal
            # numeric IDs while still collapsing a genuinely shared charge.
            key = (
                source,
                "id",
                str(transaction_id),
                record.get("start"),
                record.get("end"),
            )
        else:
            key = (
                source,
                _normalize(record.get("provider")),
                record.get("start"),
                record.get("end"),
                _as_float(record.get("energy_kwh")),
                _as_float(record.get("total_cost_eur")),
            )
        existing_index = keys.get(key)
        if existing_index is None:
            keys[key] = len(result)
            result.append(record)
            continue
        _attach_alternate(result[existing_index], record)
    return result


def _same_charge(primary: Mapping[str, Any], alternate: Mapping[str, Any]) -> bool:
    primary_start = _parse_datetime(primary.get("start"))
    primary_end = _parse_datetime(primary.get("end"))
    alternate_start = _parse_datetime(alternate.get("start"))
    alternate_end = _parse_datetime(alternate.get("end"))
    if None in {primary_start, primary_end, alternate_start, alternate_end}:
        return False
    if abs((primary_start - alternate_start).total_seconds()) > _ELEKTRUM_MATCH_SECONDS:
        return False
    if abs((primary_end - alternate_end).total_seconds()) > _ELEKTRUM_MATCH_SECONDS:
        return False

    primary_energy = _as_float(primary.get("energy_kwh"))
    alternate_energy = _as_float(alternate.get("energy_kwh"))
    if primary_energy is None or alternate_energy is None:
        return True
    tolerance = max(2.0, primary_energy * 0.2)
    return abs(primary_energy - alternate_energy) <= tolerance


def _interval_matches(
    session: Mapping[str, Any], transaction: Mapping[str, Any]
) -> bool:
    session_start = _parse_datetime(session.get("start"))
    session_end = _parse_datetime(session.get("end"))
    transaction_start = _parse_datetime(transaction.get("start"))
    transaction_end = _parse_datetime(transaction.get("end"))
    if None in {session_start, session_end, transaction_start, transaction_end}:
        return False
    margin = timedelta(seconds=_ELEKTRUM_MATCH_SECONDS)
    return (
        session_start <= transaction_end + margin
        and session_end >= transaction_start - margin
    )


def _session_weight(session: Mapping[str, Any]) -> float:
    for key in (
        "grid_energy_kwh",
        "energy_recovered_kwh",
        "estimated_battery_energy_kwh",
    ):
        value = _as_float(session.get(key))
        if value is not None and value > 0:
            return value
    start = _parse_datetime(session.get("start"))
    end = _parse_datetime(session.get("end"))
    if start is not None and end is not None:
        return max(1.0, (end - start).total_seconds())
    return 1.0


def _interval_distance(
    primary: Mapping[str, Any], alternate: Mapping[str, Any]
) -> float:
    distance = 0.0
    for key in ("start", "end"):
        primary_time = _parse_datetime(primary.get(key))
        alternate_time = _parse_datetime(alternate.get(key))
        if primary_time is None or alternate_time is None:
            return float("inf")
        distance += abs((primary_time - alternate_time).total_seconds())
    return distance


def _attach_alternate(
    primary: dict[str, Any], alternate: Mapping[str, Any]
) -> None:
    references = list(primary.get("alternate_sources") or [])
    reference = {
        "price_source": alternate.get("price_source"),
        "account_id": alternate.get("account_id"),
        "account_name": alternate.get("account_name"),
        "transaction_id": alternate.get("transaction_id"),
    }
    if reference not in references:
        references.append(reference)
    primary["alternate_sources"] = references

    if primary.get("energy_kwh") is None and alternate.get("energy_kwh") is not None:
        primary["energy_kwh"] = alternate.get("energy_kwh")
        primary["provider_reported_energy"] = alternate.get(
            "provider_reported_energy", True
        )
    if (
        primary.get("total_cost_eur") is None
        and alternate.get("total_cost_eur") is not None
    ):
        primary["cost_eur"] = alternate.get("cost_eur")
        primary["total_cost_eur"] = alternate.get("total_cost_eur")
        primary["provider_reported_cost"] = alternate.get(
            "provider_reported_cost", True
        )


def _timestamp_iso(value: Any) -> str | None:
    timestamp = _as_float(value)
    if timestamp is None or timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _duration_minutes(
    item: Mapping[str, Any], start: str, end: str
) -> int:
    duration = _as_float(item.get("duration"))
    if duration is not None and duration >= 0:
        return round(duration)
    start_time = _parse_datetime(start)
    end_time = _parse_datetime(end)
    if start_time is None or end_time is None:
        return 0
    return max(0, round((end_time - start_time).total_seconds() / 60))


def _transaction_status(value: Any) -> str:
    try:
        return {1: "pending", 2: "success", 3: "failed"}.get(int(value), "unknown")
    except (TypeError, ValueError):
        return "unknown"


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode(
        "ascii", "ignore"
    ).decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
