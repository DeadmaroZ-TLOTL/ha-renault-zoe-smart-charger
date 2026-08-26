const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

global.window = {};
require(path.join(
  __dirname,
  "..",
  "renault_trips",
  "www",
  "renault_trips",
  "history-fallback.js",
));

const helper = global.window.RenaultHistoryFallback;
const start = Date.parse("2026-08-01T00:00:00Z");
const rawStart = Date.parse("2026-08-16T00:00:00Z");
const end = Date.parse("2026-08-27T00:00:00Z");
const raw = [[{
  entity_id: "sensor.mileage",
  state: "25100",
  last_updated: new Date(rawStart).toISOString(),
  attributes: {},
}]];
const statistics = {
  "sensor.mileage": [
    {
      start,
      end: start + 3600000,
      state: 24929,
      mean: null,
    },
    {
      start: rawStart,
      end: rawStart + 3600000,
      state: 25101,
      mean: null,
    },
  ],
  "sensor.battery": [{
    start,
    end: start + 3600000,
    state: null,
    mean: 28.5,
  }],
};

const merged = helper.mergeStatistics(raw, statistics, {
  entityIds: ["sensor.mileage", "sensor.battery"],
  start,
  end,
  valueKeys: {
    "sensor.mileage": ["state", "mean"],
    "sensor.battery": ["mean", "state"],
  },
});
const mileage = merged.find((group) => group[0].entity_id === "sensor.mileage");
const battery = merged.find((group) => group[0].entity_id === "sensor.battery");

assert.deepEqual(mileage.map((state) => Number(state.state)), [24929, 25100]);
assert.equal(mileage[0].attributes.history_source, "long_term_statistics");
assert.equal(Number(battery[0].state), 28.5);

const mergedAll = helper.mergeStatistics(raw, statistics, {
  entityIds: ["sensor.mileage"],
  start,
  end,
  valueKeys: { "sensor.mileage": ["state", "mean"] },
  mergeModes: { "sensor.mileage": "all" },
});
assert.deepEqual(
  mergedAll[0].map((state) => Number(state.state)),
  [24929, 25100, 25101],
);

for (const filename of ["index.html", "mileage.html"]) {
  const html = fs.readFileSync(path.join(
    __dirname,
    "..",
    "renault_trips",
    "www",
    "renault_trips",
    filename,
  ), "utf8");
  const inlineScripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)];
  assert.ok(inlineScripts.length, `${filename} must contain an inline script`);
  for (const [, source] of inlineScripts) {
    new Function(source);
  }
}

console.log("history fallback tests passed");
