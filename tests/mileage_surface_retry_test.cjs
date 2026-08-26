"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync(
  "renault_trips/www/renault_trips/mileage.html",
  "utf8",
);
const start = source.indexOf("    async function fetchSurfaceData");
const end = source.indexOf("    async function getSurfaceBreakdown", start);
assert.ok(start >= 0 && end > start, "Surface request helper was not found");

function createContext(responses) {
  let calls = 0;
  const context = {
    SURFACE_REQUEST_ATTEMPTS: 3,
    SURFACE_REQUEST_TIMEOUT_MS: 30000,
    SURFACE_RETRY_DELAY_MS: 1,
    SURFACE_ROUTER_URL: "https://example.invalid/trace_attributes",
    AbortController: class {
      constructor() {
        this.signal = {};
      }

      abort() {}
    },
    window: {
      setTimeout(callback, delay) {
        if (delay < 30000) queueMicrotask(callback);
        return calls + 1;
      },
      clearTimeout() {},
    },
    async fetch() {
      const response = responses[Math.min(calls, responses.length - 1)];
      calls += 1;
      return response;
    },
  };
  vm.createContext(context);
  vm.runInContext(
    `${source.slice(start, end)}\nthis.fetchSurfaceData = fetchSurfaceData;`,
    context,
  );
  return { context, calls: () => calls };
}

(async () => {
  const retry = createContext([
    { ok: false, status: 503, async json() { return {}; } },
    { ok: true, status: 200, async json() { return { edges: [{ length: 1 }] }; } },
  ]);
  const data = await retry.context.fetchSurfaceData([[56.9, 24.1], [57.0, 24.2]]);
  assert.deepEqual(JSON.parse(JSON.stringify(data)), { edges: [{ length: 1 }] });
  assert.equal(retry.calls(), 2, "Temporary server errors should be retried");

  const clientError = createContext([
    { ok: false, status: 400, async json() { return {}; } },
  ]);
  await assert.rejects(
    clientError.context.fetchSurfaceData([[56.9, 24.1], [57.0, 24.2]]),
    /Valhalla HTTP 400/,
  );
  assert.equal(clientError.calls(), 1, "Permanent client errors must not be retried");

  console.log("mileage surface retry tests passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
