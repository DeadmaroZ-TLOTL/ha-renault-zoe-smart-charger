"use strict";

const assert = require("node:assert/strict");
const {
  isStrautaChargingSession,
  summarizeChargingCosts,
} = require("../renault_trips/www/renault_trips/cost-location.js");

assert.equal(isStrautaChargingSession({ price_source: "home_nord_pool" }), true);
assert.equal(
  isStrautaChargingSession({ price_source: "home_nord_pool_archive" }),
  true,
);
assert.equal(
  isStrautaChargingSession({ station_address: "Strauta iela 12" }),
  true,
);
assert.equal(
  isStrautaChargingSession({
    price_source: "ignitis_on_app",
    station_name: "Rīga LIDL Deglava",
  }),
  false,
);

const summary = summarizeChargingCosts([
  { price_source: "home_nord_pool", cost: 1.25, gridEnergy: 10 },
  { price_source: "ignitis_on_app", cost: 5.5, gridEnergy: 15 },
  { station_address: "Strauta iela", cost: 0.5, gridEnergy: 4 },
]);
assert.deepEqual(summary.total, { cost: 7.25, gridEnergy: 29, sessions: 3 });
assert.deepEqual(summary.public, { cost: 5.5, gridEnergy: 15, sessions: 1 });
assert.deepEqual(summary.strauta, { cost: 1.75, gridEnergy: 14, sessions: 2 });

console.log("Cost location tests passed");
