"""Attribute account transactions using contemporaneous vehicle GPS evidence."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
import math

from .charging_accounts_data import apply_provider_transactions, _interval_matches


def _time(value):
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (TypeError, ValueError):
        return None


def _coordinates(item):
    try:
        lat, lon = float(item['latitude']), float(item['longitude'])
        if math.isfinite(lat) and math.isfinite(lon) and abs(lat) <= 90 and abs(lon) <= 180:
            return lat, lon
    except (KeyError, TypeError, ValueError):
        pass
    return None


def _distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 12742000 * math.asin(math.sqrt(min(1, max(0, h))))


def transaction_key(item):
    return str(item.get('account_id') or ''), str(item.get('transaction_id') or '')


def check_transaction_locations(transactions, points, stations):
    """Use only in-session samples, never the vehicle's current position.

    Two separated observations are required. Conflicting or missing evidence
    stays unknown, and catalogs are keyed by provider as station IDs overlap.
    """
    catalog = {}
    for station in stations:
        coordinate = _coordinates(station)
        if coordinate:
            key = str(station.get('provider') or ''), str(station.get('id') or '')
            catalog.setdefault(key, set()).add(coordinate)
    samples = []
    for point in points:
        stamp, coordinate = _time(point.get('time')), _coordinates(point)
        try:
            accuracy = float(point.get('gps_accuracy', 0) or 0)
        except (TypeError, ValueError):
            continue
        if stamp and coordinate and math.isfinite(accuracy) and 0 <= accuracy <= 150:
            samples.append((stamp, coordinate))
    samples.sort(key=lambda x: x[0])
    times = [x[0] for x in samples]
    result = []
    for raw in transactions:
        item = dict(raw)
        item['vehicle_location_match'] = None
        item['vehicle_location_reason'] = 'insufficient_historical_gps'
        start, end = _time(item.get('start')), _time(item.get('end'))
        places = catalog.get((str(item.get('source_account_type') or ''), str(item.get('station_id') or '')), set())
        if start and end and end > start and len(places) == 1:
            place = next(iter(places))
            relevant = samples[bisect_left(times, start):bisect_right(times, end)]
            if len(relevant) >= 2 and (relevant[-1][0]-relevant[0][0]).total_seconds() >= min(60, (end-start).total_seconds()/2):
                distances = [_distance(p[1], place) for p in relevant]
                item['vehicle_location_min_distance_m'] = round(min(distances))
                item['vehicle_location_sample_count'] = len(relevant)
                if max(distances) <= 500:
                    item['vehicle_location_match'] = True
                    item['vehicle_location_reason'] = 'historical_gps_at_station'
                elif min(distances) > 2000:
                    item['vehicle_location_match'] = False
                    item['vehicle_location_reason'] = 'historical_gps_elsewhere'
                else:
                    item['vehicle_location_reason'] = 'ambiguous_historical_gps'
        result.append(item)
    return result


def apply_location_verified_transactions(sessions, transactions):
    """Keep unrelated/unsupported account charges out of the vehicle ledger."""
    sessions = list(sessions)
    accepted = [t for t in transactions if t.get('vehicle_location_match') is not False
                and (t.get('vehicle_location_match') is True
                     or any(_interval_matches(s, t) for s in sessions if not s.get('operator_only_session')))]
    verified = {transaction_key(t): t for t in accepted if t.get('vehicle_location_match') is True}
    result = []
    for row in apply_provider_transactions(sessions, accepted):
        key = (str(row.get('provider_account_id') or ''), str(row.get('provider_transaction_id') or ''))
        if row.get('operator_only_session') and key not in verified:
            continue
        if key in verified:
            row.update({k:v for k,v in verified[key].items() if k.startswith('vehicle_location_')})
        result.append(row)
    return result
