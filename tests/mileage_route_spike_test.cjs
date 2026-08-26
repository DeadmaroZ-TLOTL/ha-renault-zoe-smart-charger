"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync(
  "renault_trips/www/renault_trips/mileage.html",
  "utf8",
);
const start = source.indexOf("    function kmBetween");
const end = source.indexOf("    function valueAt", start);
assert.ok(start >= 0 && end > start, "Route cleanup helpers were not found");

const context = {};
vm.createContext(context);
vm.runInContext(
  `${source.slice(start, end)}\nthis.filterLocationSpikes = filterLocationSpikes;`,
  context,
);

const route = [
  { t: 0, lat: 56.94, lon: 24.27 },
  { t: 20_000, lat: 56.951916, lon: 24.5628602 },
  { t: 40_000, lat: 56.941, lon: 24.26 },
];
const cleaned = context.filterLocationSpikes(route);
assert.equal(cleaned.length, 2, "An impossible out-and-back location spike must be removed");
assert.equal(cleaned[0].lon, 24.27);
assert.equal(cleaned[1].lon, 24.26);

const realEndpoints = [
  { t: 0, lat: 56.951916, lon: 24.5628602 },
  { t: 10 * 60_000, lat: 56.945, lon: 24.44 },
  { t: 60 * 60_000, lat: 56.9519365, lon: 24.5628358 },
];
assert.equal(
  context.filterLocationSpikes(realEndpoints).length,
  3,
  "A genuine route origin and destination must not be removed",
);

console.log("mileage route-spike tests passed");
