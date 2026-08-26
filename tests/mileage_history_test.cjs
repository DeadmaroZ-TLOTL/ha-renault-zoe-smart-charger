"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync(
  "renault_trips/www/renault_trips/mileage.html",
  "utf8",
);
const start = source.indexOf("    function mileageTotalsByDay");
const end = source.indexOf("    function routeWaypoints", start);
assert.ok(start >= 0 && end > start, "Mileage history helpers were not found");

const context = {
  localDateValue(date) {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  },
  toNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  },
  tripDisplayStart(trip) {
    return trip.start;
  },
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)}\nthis.helpers = {
  mileageTotalsByDay,
  archivedTripCounts,
  addDetectedTripCounts,
  addArchivedMileageDays,
};`, context);

const {
  mileageTotalsByDay,
  archivedTripCounts,
  addDetectedTripCounts,
  addArchivedMileageDays,
} = context.helpers;

const at = (iso) => new Date(iso).getTime();
const rangeStart = at("2026-08-01T00:00:00Z");
const rangeEnd = at("2026-08-03T00:00:00Z");
const mileage = [
  { t: at("2026-07-31T23:00:00Z"), value: 100, reconstructed: true },
  { t: at("2026-08-01T01:00:00Z"), value: 110, reconstructed: true },
  { t: at("2026-08-01T01:10:00Z"), value: 109, reconstructed: false },
  { t: at("2026-08-01T02:00:00Z"), value: 110, reconstructed: true },
  { t: at("2026-08-01T03:00:00Z"), value: 115, reconstructed: true },
  { t: at("2026-08-01T03:05:00Z"), value: 114, reconstructed: false },
  { t: at("2026-08-01T04:00:00Z"), value: 118, reconstructed: false },
];

const totals = mileageTotalsByDay(mileage, rangeStart, rangeEnd);
assert.equal(totals.get("2026-08-01"), 18);

const archive = {
  days: [
    { day: "2026-08-01", km: 99, trips: 2 },
    { day: "2026-08-02", km: 20, trips: 3 },
    { day: "2026-08-03", km: 30, trips: 4 },
  ],
};
addArchivedMileageDays(totals, archive, rangeStart, rangeEnd);
assert.equal(totals.get("2026-08-01"), 18, "Archive must not replace odometer data");
assert.equal(totals.get("2026-08-02"), 20, "Archive must fill a missing day");
assert.equal(totals.has("2026-08-03"), false, "End date must be exclusive");

const counts = archivedTripCounts(archive, rangeStart, rangeEnd);
addDetectedTripCounts(counts, [
  { start: at("2026-08-01T12:00:00Z") },
  { start: at("2026-08-02T12:00:00Z") },
]);
assert.equal(counts.get("2026-08-01"), 2);
assert.equal(counts.get("2026-08-02"), 3);

const routeStart = source.indexOf("    function routeHistoryStates");
const routeEnd = source.indexOf("    function splitLocationTrips", routeStart);
assert.ok(routeStart >= 0 && routeEnd > routeStart, "Route archive helpers were not found");

const routeContext = {
  ENTITY: { location: "device_tracker.location" },
  toNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  },
  toTime(state) {
    return new Date(state.last_updated).getTime();
  },
  normalizeHistory(history) {
    const byEntity = {};
    for (const group of history) {
      for (const state of group) {
        if (!byEntity[state.entity_id]) byEntity[state.entity_id] = [];
        byEntity[state.entity_id].push(state);
      }
    }
    return byEntity;
  },
};
vm.createContext(routeContext);
vm.runInContext(`${source.slice(routeStart, routeEnd)}\nthis.routeHelpers = {
  routeHistoryStates,
  mergeRouteHistory,
  routePointsFromHistory,
};`, routeContext);

const retained = {
  points: [
    { t: at("2026-08-01T12:00:00Z"), lat: 56.9, lon: 24.1, accuracy: 5 },
    { t: "bad", lat: 56.9, lon: 24.1 },
  ],
};
const retainedStates = routeContext.routeHelpers.routeHistoryStates(retained);
assert.equal(retainedStates.length, 1);
assert.equal(retainedStates[0].attributes.history_source, "retained_route_history");

const mergedRoutes = routeContext.routeHelpers.mergeRouteHistory([], retained);
assert.equal(mergedRoutes.length, 1);
const roundTripPoints = routeContext.routeHelpers.routePointsFromHistory(mergedRoutes);
assert.deepEqual(
  JSON.parse(JSON.stringify(roundTripPoints)),
  [{ t: at("2026-08-01T12:00:00Z"), lat: 56.9, lon: 24.1, accuracy: 5 }],
);
assert.equal(
  routeContext.routeHelpers.mergeRouteHistory(mergedRoutes, retained).length,
  1,
  "A retained point already returned by Recorder must not be duplicated",
);

const surfaceStart = source.indexOf("    function normalizeSurfaceDistance");
const surfaceEnd = source.indexOf("    function surfaceGroupsByDay", surfaceStart);
assert.ok(surfaceStart >= 0 && surfaceEnd > surfaceStart, "Surface helper was not found");
const surfaceContext = {};
vm.createContext(surfaceContext);
vm.runInContext(`${source.slice(surfaceStart, surfaceEnd)}\nthis.normalize = normalizeSurfaceDistance;`, surfaceContext);
assert.deepEqual(
  JSON.parse(JSON.stringify(surfaceContext.normalize(100, 90, 30))),
  { total: 100, hard: 75, loose: 25, unknown: 0 },
);
assert.deepEqual(
  JSON.parse(JSON.stringify(surfaceContext.normalize(100, 60, 10))),
  { total: 100, hard: 60, loose: 10, unknown: 30 },
);

console.log("mileage history tests passed");
