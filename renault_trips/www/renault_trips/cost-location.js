(function initRenaultCostLocation(root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.RenaultCostLocation = api;
}(typeof window !== "undefined" ? window : globalThis, () => {
  "use strict";

  const STRAUTA_PRICE_SOURCES = new Set([
    "home_nord_pool",
    "home_nord_pool_archive",
    "legacy_nord_pool",
  ]);

  function isStrautaChargingSession(session) {
    const priceSource = String(session?.price_source || "").trim().toLowerCase();
    if (STRAUTA_PRICE_SOURCES.has(priceSource)) return true;
    const locationText = [
      session?.station_name,
      session?.station_address,
      session?.station_city,
    ].filter(Boolean).join(" ").toLowerCase();
    return locationText.includes("strauta");
  }

  function emptySummary() {
    return { cost: 0, gridEnergy: 0, sessions: 0 };
  }

  function summarizeChargingCosts(sessions) {
    const summary = {
      total: emptySummary(),
      public: emptySummary(),
      strauta: emptySummary(),
    };
    for (const session of Array.isArray(sessions) ? sessions : []) {
      const category = isStrautaChargingSession(session) ? "strauta" : "public";
      const cost = Number(session?.cost);
      const gridEnergy = Number(session?.gridEnergy);
      const values = {
        cost: Number.isFinite(cost) && cost > 0 ? cost : 0,
        gridEnergy: Number.isFinite(gridEnergy) && gridEnergy > 0 ? gridEnergy : 0,
        sessions: 1,
      };
      for (const target of [summary.total, summary[category]]) {
        target.cost += values.cost;
        target.gridEnergy += values.gridEnergy;
        target.sessions += 1;
      }
    }
    return summary;
  }

  return { isStrautaChargingSession, summarizeChargingCosts };
}));
