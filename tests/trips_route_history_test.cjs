"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync(
  "renault_trips/www/renault_trips/index.html",
  "utf8",
);
const start = source.indexOf("    function routeHistoryStates");
const end = source.indexOf("    function splitLocationTrips", start);
assert.ok(start >= 0 && end > start, "Trips route-history helpers were not found");

const context = {
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
  kmBetween(left, right) {
    const x = (right.lon - left.lon) * 65;
    const y = (right.lat - left.lat) * 111;
    return Math.hypot(x, y);
  },
  async haFetch() {},
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)}\nthis.helpers = {
  routeHistoryStates,
  mergeRouteHistory,
  routePointsFromHistory,
  filterLocationSpikes,
};`, context);

const at = (iso) => new Date(iso).getTime();
const retained = {
  points: [
    { t: at("2026-07-13T10:00:00Z"), lat: 56.9, lon: 24.1, accuracy: 4 },
    { t: at("2026-07-13T10:05:00Z"), lat: 56.91, lon: 24.11, accuracy: 4 },
  ],
};
const states = context.helpers.routeHistoryStates(retained);
assert.equal(states.length, 2);
assert.equal(states[0].attributes.history_source, "retained_route_history");
const merged = context.helpers.mergeRouteHistory([], retained);
assert.equal(merged.length, 1);
assert.equal(context.helpers.routePointsFromHistory(merged).length, 2);
assert.equal(
  context.helpers.mergeRouteHistory(merged, retained).length,
  1,
  "Trips must not duplicate a GPS point already returned by Recorder",
);
assert.match(
  source,
  /api\/zoe_new_extended\/route_history\?start=/,
  "Trips must load the same retained GPS archive as Mileage",
);

console.log("trips route-history tests passed");
