(function () {
  "use strict";

  const HOUR_MS = 60 * 60 * 1000;
  const DEFAULT_RAW_GAP_MS = 45 * 60 * 1000;
  const DEFAULT_VALUE_KEYS = ["state", "mean", "max", "min"];

  function toTime(value) {
    if (typeof value === "number") return value;
    const parsed = new Date(value).getTime();
    return Number.isFinite(parsed) ? parsed : null;
  }

  function stateTime(state) {
    return toTime(
      state?.last_updated || state?.last_changed || state?.last_reported,
    );
  }

  function statisticValue(row, valueKeys) {
    for (const key of valueKeys) {
      const value = Number(row?.[key]);
      if (Number.isFinite(value)) return { key, value };
    }
    return null;
  }

  function statisticTime(row, valueKey) {
    const start = toTime(row?.start);
    const end = toTime(row?.end);
    if (valueKey === "state") return end ?? start;
    if (start != null && end != null) return start + (end - start) / 2;
    return start ?? end;
  }

  function normalizeHistory(history, entityIds) {
    const byEntity = new Map(entityIds.map((entityId) => [entityId, []]));
    for (const group of Array.isArray(history) ? history : []) {
      for (const state of Array.isArray(group) ? group : []) {
        if (!state?.entity_id) continue;
        if (!byEntity.has(state.entity_id)) byEntity.set(state.entity_id, []);
        byEntity.get(state.entity_id).push(state);
      }
    }
    for (const states of byEntity.values()) {
      states.sort((left, right) => stateTime(left) - stateTime(right));
    }
    return byEntity;
  }

  function hasRawStateNear(rawTimes, time, maximumDistance) {
    let low = 0;
    let high = rawTimes.length;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (rawTimes[middle] < time) low = middle + 1;
      else high = middle;
    }
    return [rawTimes[low - 1], rawTimes[low]].some(
      (candidate) => (
        Number.isFinite(candidate)
        && Math.abs(candidate - time) <= maximumDistance
      ),
    );
  }

  function mergeStatistics(history, statistics, options) {
    const entityIds = options.entityIds || Object.keys(statistics || {});
    const start = Number(options.start);
    const end = Number(options.end);
    const byEntity = normalizeHistory(history, entityIds);

    for (const entityId of entityIds) {
      const rawStates = byEntity.get(entityId) || [];
      const firstRawInRange = rawStates.find((state) => {
        const time = stateTime(state);
        return time != null && time >= start;
      });
      const rawCutoff = stateTime(firstRawInRange) ?? Number.POSITIVE_INFINITY;
      const rawTimes = rawStates.map(stateTime).filter(Number.isFinite);
      const valueKeys = options.valueKeys?.[entityId] || DEFAULT_VALUE_KEYS;
      const mergeMode = options.mergeModes?.[entityId] || "before_raw";
      const maximumRawGap = Number.isFinite(options.maximumRawGapMs)
        ? options.maximumRawGapMs
        : DEFAULT_RAW_GAP_MS;
      const synthetic = [];

      for (const row of statistics?.[entityId] || []) {
        const selected = statisticValue(row, valueKeys);
        if (!selected) continue;
        const time = statisticTime(row, selected.key);
        const afterRawCutoff = time != null && time >= rawCutoff;
        const allowedAfterRaw = mergeMode === "all"
          || (
            mergeMode === "gaps"
            && !hasRawStateNear(rawTimes, time, maximumRawGap)
          );
        if (
          time == null
          || time < start - HOUR_MS
          || (afterRawCutoff && !allowedAfterRaw)
          || time > end
        ) {
          continue;
        }
        const timestamp = new Date(time).toISOString();
        synthetic.push({
          entity_id: entityId,
          state: String(selected.value),
          last_changed: timestamp,
          last_updated: timestamp,
          attributes: {
            history_source: "long_term_statistics",
            statistic_period: "hour",
            statistic_value: selected.key,
          },
        });
      }

      const merged = [...synthetic, ...rawStates]
        .filter((state) => stateTime(state) != null)
        .sort((left, right) => stateTime(left) - stateTime(right));
      const deduplicated = [];
      for (const state of merged) {
        const previous = deduplicated.at(-1);
        if (previous && stateTime(previous) === stateTime(state)) {
          if (state.attributes?.history_source !== "long_term_statistics") {
            deduplicated[deduplicated.length - 1] = state;
          }
        } else {
          deduplicated.push(state);
        }
      }
      byEntity.set(entityId, deduplicated);
    }

    return [...byEntity.values()].filter((states) => states.length);
  }

  async function augment(history, options) {
    const hass = options.hass;
    const start = Number(options.start);
    const end = Number(options.end);
    if (
      !hass?.callWS
      || !Number.isFinite(start)
      || !Number.isFinite(end)
      || end <= start
      || !options.entityIds?.length
    ) {
      return history;
    }

    try {
      const statistics = await hass.callWS({
        type: "recorder/statistics_during_period",
        start_time: new Date(Math.max(0, start - HOUR_MS)).toISOString(),
        end_time: new Date(end).toISOString(),
        statistic_ids: options.entityIds,
        period: "hour",
        types: ["mean", "state", "min", "max"],
      });
      return mergeStatistics(history, statistics, options);
    } catch (error) {
      console.debug(
        "Long-term Renault statistics are unavailable; using raw history",
        error,
      );
      return history;
    }
  }

  window.RenaultHistoryFallback = {
    augment,
    mergeStatistics,
  };
})();
