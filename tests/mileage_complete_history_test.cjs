"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync(
  "renault_trips/www/renault_trips/mileage.html",
  "utf8",
);
const start = source.indexOf("    function tripHistoryId");
const end = source.indexOf("    function routeWaypoints", start);
assert.ok(start >= 0 && end > start, "Complete trip-history helpers were not found");

const at = (iso) => new Date(iso).getTime();
const context = {
  toNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  },
  normalizeSurfaceDistance(total, hard, loose) {
    const distance = Math.max(0, Number(total) || 0);
    const known = Math.max(0, Number(hard) || 0) + Math.max(0, Number(loose) || 0);
    const scale = known > distance && known > 0 ? distance / known : 1;
    const normalizedHard = Math.max(0, Number(hard) || 0) * scale;
    const normalizedLoose = Math.max(0, Number(loose) || 0) * scale;
    return {
      total: distance,
      hard: normalizedHard,
      loose: normalizedLoose,
      unknown: Math.max(0, distance - normalizedHard - normalizedLoose),
    };
  },
  tripDayKey(trip) {
    if (trip.day) return trip.day;
    return new Date(trip.start).toISOString().slice(0, 10);
  },
  dayInRange(day, rangeStart, rangeEnd) {
    const value = new Date(`${day}T12:00:00Z`).getTime();
    return value >= rangeStart && value < rangeEnd;
  },
  async haFetch() {},
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)}\nthis.helpers = {
  tripHistoryId,
  mergePersistedTripHistory,
  addArchivedTripGaps,
  tripHistoryRecord,
};`, context);

const detected = {
  start: at("2026-08-20T08:00:00Z"),
  end: at("2026-08-20T08:30:00Z"),
  km: 12,
  points: [{}, {}],
  surface: null,
};
const id = context.helpers.tripHistoryId(detected);
const merged = context.helpers.mergePersistedTripHistory([detected], {
  trips: [{
    id,
    day: "2026-08-20",
    start: detected.start,
    end: detected.end,
    km: 12,
    hard: 9,
    loose: 2,
    unknown: 1,
    coverage: 91.67,
    average_speed: 40,
    max_speed: 70,
  }],
});
assert.equal(merged.length, 1);
assert.equal(merged[0].surfacePersisted, true);
assert.equal(merged[0].surface.hard, 9);
assert.equal(merged[0].speed.average, 40);

const complete = context.helpers.addArchivedTripGaps(
  merged,
  {
    days: [
      { day: "2026-07-13", km: 38, trips: 2 },
      { day: "2026-08-20", km: 20, trips: 2 },
    ],
  },
  at("2026-07-01T00:00:00Z"),
  at("2026-09-01T00:00:00Z"),
);
const julyGap = complete.find((trip) => trip.day === "2026-07-13");
assert.equal(julyGap.archiveGap, true);
assert.equal(julyGap.archivedCount, 2);
assert.equal(julyGap.surface.unknown, 38);
const augustGap = complete.find((trip) => trip.archiveGap && trip.day === "2026-08-20");
assert.equal(augustGap.archivedCount, 1);
assert.equal(augustGap.km, 8);

const persisted = context.helpers.tripHistoryRecord({
  ...detected,
  surface: { hard: 9, loose: 2, unknown: 1, coverage: 91.67 },
  speed: { average: 40, max: 70 },
});
assert.equal(persisted.id, id);
assert.equal(persisted.day, "2026-08-20");
assert.equal(persisted.average_speed, 40);

console.log("mileage complete-history tests passed");
