"use strict";

const ENTITY = {
  location: "device_tracker.location",
  mileage: "sensor.mileage",
  battery: "sensor.battery",
  costSettings: "sensor.renault_zoe_new_cost_settings",
  nordPoolPrice: "sensor.renault_zoe_new_nord_pool_price",
  plannedCharging: "sensor.zoe_planned_charging_times",
  plannedChargeLevel: "sensor.zoe_planned_charge_level",
  sessions: [
    "sensor.zoe_charge_sessions_history",
    "sensor.zoe_charge_sessions_history_raw",
    "sensor.zoe_charge_sessions_31d",
    "sensor.zoe_charge_sessions_31d_raw",
  ],
};

const MOVE_THRESHOLD_KM = 0.25;
const MIN_TRIP_KM = 0.75;
const STOP_AFTER_MIN = 20;
const MAX_SAMPLE_GAP_MIN = 90;
const ENERGY_GROUP_GAP_MIN = 45;
const ENERGY_LOOKBACK_MIN = 35;
const MAX_ENERGY_LOOKBACK_MIN = 360;
const MIN_ASSUMED_TRIP_SPEED_KMH = 30;
const BATTERY_SETTLE_MIN = 12;
const MILEAGE_SETTLE_MIN = 15;
const MILEAGE_COVER_MARGIN_MIN = 20;
const AUTO_REFRESH_MS = 5 * 60 * 1000;
const SOURCE_CHANGE_CHECK_MS = 15 * 1000;
const TRANSLATIONS = {
  lv: {
    pageTitle: "Renault ZOE enerģijas izmaksas",
    pageSubtitle: "Uzlāžu pašizmaksa, baterijas enerģijas atlikums un braucienu izmaksas.",
    language: "Valoda",
    period: "Periods",
    currentMonth: "Tekošais mēnesis",
    day1: "Šodiena (00–24)",
    days3: "3 kalendāra dienas",
    days7: "7 kalendāra dienas",
    days14: "14 kalendāra dienas",
    days30: "30 kalendāra dienas",
    days90: "90 kalendāra dienas",
    allHistory: "Visa pieejamā vēsture",
    specificDate: "Konkrēts datums",
    clear: "Notīrīt",
    settings: "Iestatījumi",
    refresh: "Atjaunot",
    costSummary: "Izmaksu kopsavilkums",
    averageBatteryPrice: "Vidējā cena baterijā",
    batteryEnergy: "Enerģija baterijā",
    averageCost: "Vidējās izmaksas",
    averageConsumption: "Vidējais patēriņš",
    distanceInPeriod: "Nobraukums periodā",
    spentOnTrips: "Braucienos iztērēts",
    dailyCosts: "Izmaksas pa dienām",
    dailyCostsAria: "Braucienu izmaksas pa dienām",
    batteryUnitCost: "Baterijas kWh pašizmaksa",
    afterEachCharge: "Faktiskā cena mainās tikai pēc uzlādes; prognoze izmanto plānotās uzlādes",
    batteryPriceAria: "Vidējā baterijas enerģijas cena",
    actualUnitCost: "Faktiskā pašizmaksa",
    forecastUnitCost: "Prognoze pēc plānotās uzlādes",
    tripCosts: "Braucienu izmaksas",
    startEnd: "Sākums / beigas",
    minutes: "Min",
    batteryCents: "Baterijas c/kWh",
    costEur: "Izmaksas EUR",
    noTrips: "Izvēlētajā periodā braucienu nav.",
    loadingInitial: "Ielādēju Renault datus...",
    loading: "Ielādēju uzlāžu sesijas un braucienu vēsturi...",
    pricedSessions: "{count} uzlāžu cenu vēsture",
    pricedAndEstimated: "{priced} ar cenu, {estimated} novērtētas",
    batteryValue: "{soc}% · vērtība {cost} EUR",
    per100km: "uz 100 km",
    oneTripEstimated: "1 braucienam enerģija novērtēta",
    tripsEstimated: "{count} braucieniem enerģija novērtēta",
    trips: "{count} braucieni",
    noTripsShort: "Braucienu nav",
    chargedFor: "{energy} kWh · uzlādēts {charged} kWh par {cost} EUR",
    totalAverage: "Kopā / vidēji",
    noPeriodData: "Šajā periodā datu nav",
    noChargePriceData: "Uzlāžu cenu datu nav",
    sessionsUnavailable: "Uzlāžu sesiju sensors nav pieejams",
    sessionsEmpty: "Renault API uzlāžu sesiju vēsture ir tukša",
    updated: "Atjaunots {time}. {charges} uzlādes, {trips} braucieni, uzkrātais patēriņš {consumption} kWh/100 km{estimate}.",
    oneEstimate: ", 1 enerģijas novērtējums",
    estimates: ", {count} enerģijas novērtējumi",
    loadError: "Datus neizdevās ielādēt: {error}",
    dataUnavailable: "Dati nav pieejami",
    method: "<strong>Aprēķina princips.</strong> Renault uzlāde pievieno baterijai SOC pieaugumam atbilstošās kWh un sesijas faktiskās izmaksas ar pārvadi. Brauciena laikā vienas baterijas kWh pašizmaksa nemainās; tā tiek pārrēķināta tikai pēc uzlādes. Pārtrauktā prognozes līkne izmanto plānotos uzlādes intervālus, Nord Pool cenu, pārvadi un efektivitāti. Baterijas izmantojamā ietilpība ir {capacity} kWh, uzlādes efektivitāte {efficiency}%, pārvade {deliveryExcl} EUR/kWh bez PVN jeb {deliveryIncl} EUR/kWh ar {vat}% PVN. Simbols <span class=\"estimated\">~</span> norāda vērtību, kas SOC datu trūkuma vai neiespējamas nobīdes dēļ novērtēta pēc {fallback} kWh/100 km rezerves patēriņa.",
  },
  en: {
    pageTitle: "Renault ZOE energy costs",
    pageSubtitle: "Charging cost, remaining battery energy, and trip expenses.",
    language: "Language",
    period: "Period",
    currentMonth: "Current month",
    day1: "Today (00–24)",
    days3: "3 calendar days",
    days7: "7 calendar days",
    days14: "14 calendar days",
    days30: "30 calendar days",
    days90: "90 calendar days",
    allHistory: "All available history",
    specificDate: "Specific date",
    clear: "Clear",
    settings: "Settings",
    refresh: "Refresh",
    costSummary: "Cost summary",
    averageBatteryPrice: "Average battery price",
    batteryEnergy: "Energy in battery",
    averageCost: "Average cost",
    averageConsumption: "Average consumption",
    distanceInPeriod: "Distance in period",
    spentOnTrips: "Spent on trips",
    dailyCosts: "Daily costs",
    dailyCostsAria: "Trip costs by day",
    batteryUnitCost: "Battery kWh unit cost",
    afterEachCharge: "Actual cost changes only after charging; forecast uses planned charging",
    batteryPriceAria: "Average battery energy price",
    actualUnitCost: "Actual unit cost",
    forecastUnitCost: "Forecast after planned charging",
    tripCosts: "Trip costs",
    startEnd: "Start / end",
    minutes: "Min",
    batteryCents: "Battery c/kWh",
    costEur: "Cost EUR",
    noTrips: "No trips in the selected period.",
    loadingInitial: "Loading Renault data...",
    loading: "Loading charge sessions and trip history...",
    pricedSessions: "{count} priced charge sessions",
    pricedAndEstimated: "{priced} priced, {estimated} estimated",
    batteryValue: "{soc}% · value {cost} EUR",
    per100km: "per 100 km",
    oneTripEstimated: "Energy estimated for 1 trip",
    tripsEstimated: "Energy estimated for {count} trips",
    trips: "{count} trips",
    noTripsShort: "No trips",
    chargedFor: "{energy} kWh · charged {charged} kWh for {cost} EUR",
    totalAverage: "Total / average",
    noPeriodData: "No data in this period",
    noChargePriceData: "No charge-price data",
    sessionsUnavailable: "Charge sessions sensor is unavailable",
    sessionsEmpty: "Renault API charge session history is empty",
    updated: "Updated {time}. {charges} charges, {trips} trips, learned consumption {consumption} kWh/100 km{estimate}.",
    oneEstimate: ", 1 energy estimate",
    estimates: ", {count} energy estimates",
    loadError: "Could not load data: {error}",
    dataUnavailable: "Data unavailable",
    method: "<strong>Calculation method.</strong> A Renault charge adds the kWh represented by the SOC increase and the session's actual cost including delivery. The unit cost of one battery kWh stays unchanged while driving and is recalculated only after charging. The dashed forecast uses planned charging intervals, Nord Pool prices, delivery, and charging efficiency. Usable battery capacity is {capacity} kWh, charging efficiency is {efficiency}%, and delivery is {deliveryExcl} EUR/kWh before VAT or {deliveryIncl} EUR/kWh including {vat}% VAT. The <span class=\"estimated\">~</span> symbol marks a value estimated with the {fallback} kWh/100 km fallback consumption because SOC data was missing or implausible.",
  },
};

const LOCALES = { lv: "lv-LV", en: "en-GB" };
let currentLanguage = "lv";
let costSettings = {
  batteryCapacityKwh: 52,
  chargingEfficiencyPercent: 90,
  defaultChargingPowerKw: 11,
  deliveryPriceExclVat: 0.03962,
  deliveryPriceInclVat: 0.0479402,
  vatPercent: 21,
  fallbackConsumptionKwh100: 17.5,
};

const periodEl = document.getElementById("period");
const dayDateEl = document.getElementById("dayDate");
const dayDateToEl = document.getElementById("dayDateTo");
const clearDateEl = document.getElementById("clearDate");
const reloadEl = document.getElementById("reload");
const statusEl = document.getElementById("status");
const rowsEl = document.getElementById("tripRows");
const totalsEl = document.getElementById("tripTotals");
const emptyEl = document.getElementById("empty");
const tableSummaryEl = document.getElementById("tableSummary");
const dailyCanvas = document.getElementById("dailyChart");
const batteryCanvas = document.getElementById("batteryChart");
const actualRateToggleEl = document.getElementById("actualRateToggle");
const forecastRateToggleEl = document.getElementById("forecastRateToggle");
const methodEl = document.getElementById("method");
let cachedParentHass = null;
let lastModel = null;
let dateRange = null;
let loadingModel = false;
let lastSourceSignature = "";

function t(key, values = {}) {
  let text = TRANSLATIONS[currentLanguage][key] ?? key;
  for (const [name, value] of Object.entries(values)) {
    text = text.replaceAll(`{${name}}`, String(value));
  }
  return text;
}

function renderMethod() {
  methodEl.innerHTML = t("method", {
    capacity: formatNumber(costSettings.batteryCapacityKwh, 1),
    efficiency: formatNumber(costSettings.chargingEfficiencyPercent, 1),
    deliveryExcl: formatNumber(costSettings.deliveryPriceExclVat, 5),
    deliveryIncl: formatNumber(costSettings.deliveryPriceInclVat, 5),
    vat: formatNumber(costSettings.vatPercent, 1),
    fallback: formatNumber(costSettings.fallbackConsumptionKwh100, 1),
  });
}

function applyLanguage() {
  document.documentElement.lang = currentLanguage;
  document.title = t("pageTitle");
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = t(element.dataset.i18n);
  }
  for (const element of document.querySelectorAll("[data-i18n-aria]")) {
    element.setAttribute("aria-label", t(element.dataset.i18nAria));
  }
  document.getElementById("settings").title = t("settings");
  dateRange?.setLanguage(currentLanguage);
  renderMethod();
  if (lastModel) render(lastModel);
}

function localDateValue(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function setStatus(text, warn = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("warn", warn);
}

async function loadCostSettings() {
  try {
    const settingsState = await haFetch(
      `/api/states/${encodeURIComponent(ENTITY.costSettings)}`,
    );
    const attrs = settingsState.attributes || {};
    const configuredLanguage = attrs.dashboard_language === "en" ? "en" : "lv";
    if (configuredLanguage !== currentLanguage) {
      currentLanguage = configuredLanguage;
      applyLanguage();
    }
    const batteryCapacity = toNumber(attrs.battery_capacity_kwh);
    const efficiency = toNumber(attrs.charging_efficiency_percent);
    const defaultPower = toNumber(attrs.default_charging_power_kw);
    const deliveryExcl = toNumber(
      attrs.delivery_price_excl_vat_eur_per_kwh,
    );
    const deliveryIncl = toNumber(
      attrs.delivery_price_incl_vat_eur_per_kwh,
    );
    const vat = toNumber(attrs.vat_percent);
    const fallback = toNumber(
      attrs.fallback_consumption_kwh_per_100km,
    );
    costSettings = {
      batteryCapacityKwh: batteryCapacity > 0
        ? batteryCapacity
        : costSettings.batteryCapacityKwh,
      chargingEfficiencyPercent: efficiency > 0
        ? efficiency
        : costSettings.chargingEfficiencyPercent,
      defaultChargingPowerKw: defaultPower > 0
        ? defaultPower
        : costSettings.defaultChargingPowerKw,
      deliveryPriceExclVat: deliveryExcl >= 0
        ? deliveryExcl
        : costSettings.deliveryPriceExclVat,
      deliveryPriceInclVat: deliveryIncl >= 0
        ? deliveryIncl
        : costSettings.deliveryPriceInclVat,
      vatPercent: vat >= 0 ? vat : costSettings.vatPercent,
      fallbackConsumptionKwh100: fallback > 0
        ? fallback
        : costSettings.fallbackConsumptionKwh100,
    };
  } catch (error) {
    console.debug("Cost settings sensor is unavailable; using defaults", error);
  }
  renderMethod();
  return costSettings;
}

function parseMaybeJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

async function getParentHass() {
  if (cachedParentHass?.callApi) return cachedParentHass;
  if (window.parent === window) return null;

  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      const hass = window.parent.document.querySelector("home-assistant")?.hass;
      if (hass?.callApi) {
        cachedParentHass = hass;
        return hass;
      }
    } catch {
      return null;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 100));
  }
  return null;
}

async function refreshToken(tokens) {
  if (!tokens?.refresh_token) return null;
  const body = new URLSearchParams();
  body.set("grant_type", "refresh_token");
  body.set("refresh_token", tokens.refresh_token);
  body.set("client_id", `${location.origin}/`);
  const response = await fetch("/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) return null;
  const fresh = await response.json();
  const merged = {
    ...tokens,
    ...fresh,
    expires: Date.now() + fresh.expires_in * 1000,
  };
  localStorage.setItem("hassTokens", JSON.stringify(merged));
  return merged.access_token;
}

async function getAccessToken() {
  const direct = parseMaybeJson(localStorage.getItem("hassTokens"));
  if (direct?.access_token) {
    if (!direct.expires || direct.expires > Date.now() + 60000) {
      return direct.access_token;
    }
    const refreshed = await refreshToken(direct);
    if (refreshed) return refreshed;
  }
  for (let index = 0; index < localStorage.length; index += 1) {
    const value = parseMaybeJson(localStorage.getItem(localStorage.key(index)));
    if (value?.access_token) return value.access_token;
  }
  return null;
}

async function haFetch(path, options = {}) {
  const parentHass = await getParentHass();
  if (parentHass?.callApi) {
    const method = String(options.method || "GET").toUpperCase();
    const apiPath = path.replace(/^\/api\//, "");
    try {
      const result = await parentHass.callApi(method, apiPath, options.body);
      document.documentElement.dataset.authSource = "parent";
      return result;
    } catch (error) {
      console.debug("Parent Home Assistant API request failed", error);
    }
  }

  const token = await getAccessToken();
  document.documentElement.dataset.authSource = token ? "token" : "none";
  const makeRequest = (accessToken) => {
    const headers = { ...(options.headers || {}) };
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    const request = { ...options, headers, credentials: "same-origin" };
    if (request.body && typeof request.body !== "string") {
      request.body = JSON.stringify(request.body);
      headers["Content-Type"] = "application/json";
    }
    return fetch(path, request);
  };

  let response = await makeRequest(token);
  if (response.status === 401) {
    const refreshed = await refreshToken(
      parseMaybeJson(localStorage.getItem("hassTokens")),
    );
    if (refreshed) response = await makeRequest(refreshed);
  }
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function toNumber(value) {
  const number = Number.parseFloat(value);
  return Number.isFinite(number) ? number : null;
}

function toTime(state) {
  return new Date(
    state.last_updated || state.last_changed || state.last_reported,
  ).getTime();
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function kmBetween(left, right) {
  const radius = 6371;
  const latitude = (right.lat - left.lat) * Math.PI / 180;
  const longitude = (right.lon - left.lon) * Math.PI / 180;
  const leftLat = left.lat * Math.PI / 180;
  const rightLat = right.lat * Math.PI / 180;
  const haversine = (
    Math.sin(latitude / 2) ** 2
    + Math.cos(leftLat) * Math.cos(rightLat) * Math.sin(longitude / 2) ** 2
  );
  return 2 * radius * Math.asin(Math.sqrt(haversine));
}

function routeKm(points) {
  let total = 0;
  for (let index = 1; index < points.length; index += 1) {
    total += kmBetween(points[index - 1], points[index]);
  }
  return total;
}

function valueAt(samples, time) {
  let best = null;
  for (const sample of samples) {
    if (sample.t <= time) best = sample;
    else break;
  }
  return best?.value ?? samples[0]?.value ?? null;
}

function batteryUseBetween(samples, start, end) {
  const windowSamples = [];
  let before = null;
  for (const sample of samples) {
    if (sample.t <= start) before = sample;
    else if (sample.t <= end) windowSamples.push(sample);
    else break;
  }
  if (before) windowSamples.unshift(before);
  if (windowSamples.length < 2) {
    return { drop: 0, startValue: null, endValue: null };
  }

  let drop = 0;
  for (let index = 1; index < windowSamples.length; index += 1) {
    drop += Math.max(
      0,
      windowSamples[index - 1].value - windowSamples[index].value,
    );
  }
  return {
    drop,
    startValue: windowSamples[0].value,
    endValue: windowSamples[0].value - drop,
  };
}

function batteryIncreasedBetween(samples, start, end) {
  let previous = null;
  for (const sample of samples) {
    if (sample.t < start) {
      previous = sample;
      continue;
    }
    if (sample.t > end) break;
    if (previous && sample.value > previous.value) return true;
    previous = sample;
  }
  return false;
}

function normalizeHistory(history) {
  const byEntity = {};
  for (const group of history || []) {
    for (const state of group || []) {
      if (!byEntity[state.entity_id]) byEntity[state.entity_id] = [];
      byEntity[state.entity_id].push(state);
    }
  }
  for (const list of Object.values(byEntity)) {
    list.sort((left, right) => toTime(left) - toTime(right));
  }
  return byEntity;
}

function splitLocationTrips(locations) {
  const found = [];
  let current = null;
  let lastMovementAt = null;

  const closeCurrent = () => {
    if (current && current.end > current.start) found.push(current);
    current = null;
    lastMovementAt = null;
  };

  for (let index = 1; index < locations.length; index += 1) {
    const previous = locations[index - 1];
    const point = locations[index];
    const gapMinutes = (point.t - previous.t) / 60000;
    const distance = kmBetween(previous, point);

    if (gapMinutes > MAX_SAMPLE_GAP_MIN) {
      closeCurrent();
      continue;
    }

    if (distance >= MOVE_THRESHOLD_KM) {
      if (
        current
        && (point.t - lastMovementAt) / 60000 >= STOP_AFTER_MIN
      ) {
        closeCurrent();
      }
      if (!current) current = { points: [previous], start: previous.t };
      current.points.push(point);
      current.end = point.t;
      lastMovementAt = point.t;
    } else if (
      current
      && (point.t - lastMovementAt) / 60000 >= STOP_AFTER_MIN
    ) {
      closeCurrent();
    }
  }
  closeCurrent();
  return found;
}

function addUncoveredMileageTrips(found, mileage, locations) {
  const margin = MILEAGE_COVER_MARGIN_MIN * 60000;
  for (let index = 1; index < mileage.length; index += 1) {
    const startSample = mileage[index - 1];
    const endSample = mileage[index];
    const delta = endSample.value - startSample.value;
    if (delta < MIN_TRIP_KM) continue;

    const covered = found.some((trip) => (
      endSample.t >= trip.start - margin
      && endSample.t <= trip.end + margin
    ));
    if (covered) continue;

    const points = locations.filter(
      (point) => point.t >= startSample.t && point.t <= endSample.t,
    );
    found.push({
      points,
      start: startSample.t,
      end: endSample.t,
      mileageStart: startSample.value,
      mileageEnd: endSample.value,
    });
  }
}

function tripDistance(trip, mileage) {
  const startMileage = (
    trip.mileageStart ?? valueAt(mileage, trip.start)
  );
  const endMileage = (
    trip.mileageEnd
    ?? valueAt(mileage, trip.end + MILEAGE_SETTLE_MIN * 60000)
  );
  const mileageKm = (
    startMileage != null && endMileage != null
      ? Math.max(0, endMileage - startMileage)
      : 0
  );
  const gpsKm = routeKm(trip.points);
  return {
    km: mileageKm >= MIN_TRIP_KM ? mileageKm : gpsKm,
    mileageKm,
    gpsKm,
  };
}

function buildEnergyGroups(trips, battery) {
  const groups = [];
  let group = [];
  for (const trip of trips) {
    const previous = group.at(-1);
    const gapMinutes = previous
      ? (trip.start - previous.end) / 60000
      : Infinity;
    if (
      previous
      && (
        gapMinutes > ENERGY_GROUP_GAP_MIN
        || batteryIncreasedBetween(battery, previous.end, trip.start)
      )
    ) {
      groups.push(group);
      group = [];
    }
    group.push(trip);
  }
  if (group.length) groups.push(group);
  return groups;
}

function enrichTripGroups(trips, battery) {
  const groups = buildEnergyGroups(trips, battery);
  let previousEnergyEnd = null;

  groups.forEach((group, groupIndex) => {
    const totalKm = group.reduce((sum, trip) => sum + trip.km, 0);
    const distanceLookbackMinutes = (
      totalKm / MIN_ASSUMED_TRIP_SPEED_KMH * 60 + ENERGY_LOOKBACK_MIN
    );
    const lookbackMinutes = Math.min(
      MAX_ENERGY_LOOKBACK_MIN,
      Math.max(ENERGY_LOOKBACK_MIN, distanceLookbackMinutes),
    );
    const lookback = group[0].start - lookbackMinutes * 60000;
    const energyStart = previousEnergyEnd == null
      ? lookback
      : Math.max(lookback, previousEnergyEnd);
    const settleEnd = (
      group.at(-1).end + BATTERY_SETTLE_MIN * 60000
    );
    const nextStart = groups[groupIndex + 1]?.[0].start;
    const energyEnd = nextStart == null
      ? settleEnd
      : Math.min(settleEnd, nextStart);
    const batteryUse = batteryUseBetween(battery, energyStart, energyEnd);
    let runningSoc = batteryUse.startValue;

    group.forEach((trip) => {
      const distanceShare = totalKm > 0 ? trip.km / totalKm : 0;
      const batteryUsed = batteryUse.drop * distanceShare;
      trip.batteryUsed = batteryUsed;
      trip.energy = (
        batteryUsed * costSettings.batteryCapacityKwh / 100
      );
      trip.consumption = trip.km > 0
        ? trip.energy / trip.km * 100
        : 0;
      trip.socStart = runningSoc;
      trip.socEnd = runningSoc == null
        ? null
        : runningSoc - batteryUsed;
      runningSoc = trip.socEnd;
    });
    previousEnergyEnd = energyEnd;
  });

  return trips;
}

function buildTrips(history) {
  const byEntity = normalizeHistory(history);
  const locations = (byEntity[ENTITY.location] || [])
    .map((state) => ({
      t: toTime(state),
      lat: toNumber(state.attributes?.latitude),
      lon: toNumber(state.attributes?.longitude),
      state: state.state,
    }))
    .filter((point) => (
      Number.isFinite(point.t)
      && Number.isFinite(point.lat)
      && Number.isFinite(point.lon)
    ));
  const mileage = (byEntity[ENTITY.mileage] || [])
    .map((state) => ({ t: toTime(state), value: toNumber(state.state) }))
    .filter((point) => (
      Number.isFinite(point.t) && Number.isFinite(point.value)
    ));
  const battery = (byEntity[ENTITY.battery] || [])
    .map((state) => ({ t: toTime(state), value: toNumber(state.state) }))
    .filter((point) => (
      Number.isFinite(point.t) && Number.isFinite(point.value)
    ));

  const found = splitLocationTrips(locations);
  addUncoveredMileageTrips(found, mileage, locations);
  found.sort((left, right) => left.start - right.start);

  const prepared = found
    .map((trip) => ({ ...trip, ...tripDistance(trip, mileage) }))
    .filter((trip) => trip.km >= MIN_TRIP_KM);

  return enrichTripGroups(prepared, battery)
    .sort((left, right) => left.start - right.start);
}

function learnConsumption(trips) {
  const usable = trips.filter((trip) => (
    trip.km >= 3
    && trip.energy > 0
    && trip.consumption >= 6
    && trip.consumption <= 45
  ));
  const distance = usable.reduce((sum, trip) => sum + trip.km, 0);
  const energy = usable.reduce((sum, trip) => sum + trip.energy, 0);
  if (distance <= 0) return costSettings.fallbackConsumptionKwh100;
  return clamp(energy / distance * 100, 10, 35);
}

function normalizeTripEnergy(trips) {
  const learnedConsumption = learnConsumption(trips);
  for (const trip of trips) {
    const rawConsumption = trip.km > 0
      ? trip.energy / trip.km * 100
      : 0;
    const implausible = (
      !Number.isFinite(trip.energy)
      || trip.energy <= 0
      || rawConsumption < 4
      || rawConsumption > 55
    );
    if (implausible) {
      trip.rawEnergy = trip.energy;
      trip.energy = trip.km * learnedConsumption / 100;
      trip.consumption = learnedConsumption;
      trip.energyEstimated = true;
      if (
        Number.isFinite(trip.socStart)
        && !Number.isFinite(trip.socEnd)
      ) {
        trip.socEnd = (
          trip.socStart
          - trip.energy / costSettings.batteryCapacityKwh * 100
        );
      }
    }
  }
  return learnedConsumption;
}

function normalizeSessions(rawSessions) {
  return (Array.isArray(rawSessions) ? rawSessions : [])
    .map((session) => {
      const start = new Date(session.start).getTime();
      const end = new Date(session.end || session.start).getTime();
      const startSoc = toNumber(session.start_soc);
      const endSoc = toNumber(session.end_soc);
      const energy = toNumber(session.estimated_battery_energy_kwh);
      const socEnergy = (
        Number.isFinite(startSoc) && Number.isFinite(endSoc)
          ? (
            Math.max(0, endSoc - startSoc)
            * costSettings.batteryCapacityKwh
            / 100
          )
          : null
      );
      return {
        ...session,
        startTime: start,
        endTime: end,
        startSoc,
        endSoc,
        priceCoverage: toNumber(session.price_coverage_percent),
        batteryEnergy: (
          Number.isFinite(energy) && energy > 0 ? energy : socEnergy
        ),
        cost: toNumber(session.total_cost_eur),
      };
    })
    .filter((session) => (
      Number.isFinite(session.startTime)
      && Number.isFinite(session.endTime)
      && Number.isFinite(session.batteryEnergy)
      && session.batteryEnergy > 0
    ))
    .sort((left, right) => left.endTime - right.endTime);
}

function sessionUnitCost(session) {
  if (
    !Number.isFinite(session.cost)
    || !Number.isFinite(session.batteryEnergy)
    || session.batteryEnergy <= 0
  ) {
    return null;
  }
  return session.cost / session.batteryEnergy;
}

function applyWeightedCostModel(trips, sessions, currentSoc) {
  const pricedSessions = sessions.filter(
    (session) => Number.isFinite(sessionUnitCost(session)),
  );
  const firstRate = pricedSessions.length
    ? sessionUnitCost(pricedSessions[0])
    : 0;

  const firstEventTime = Math.min(
    sessions[0]?.endTime ?? Infinity,
    trips[0]?.start ?? Infinity,
  );
  const firstTrip = trips.find((trip) => trip.start === firstEventTime)
    || trips[0];
  const firstSession = sessions.find(
    (session) => session.endTime === firstEventTime,
  ) || sessions[0];
  const initialSoc = Number.isFinite(firstTrip?.socStart)
    ? firstTrip.socStart
    : (
      Number.isFinite(firstSession?.startSoc)
        ? firstSession.startSoc
        : currentSoc
    );

  let inventoryEnergy = clamp(
    (
      (Number.isFinite(initialSoc) ? initialSoc : 50)
      * costSettings.batteryCapacityKwh
      / 100
    ),
    0,
    costSettings.batteryCapacityKwh,
  );
  let inventoryRate = Number.isFinite(firstRate) ? Math.max(0, firstRate) : 0;
  let inventoryCost = inventoryEnergy * inventoryRate;
  const batteryRateHistory = [{
    time: Number.isFinite(firstEventTime) ? firstEventTime : Date.now(),
    rate: inventoryRate,
    energy: inventoryEnergy,
    type: "seed",
  }];

  const events = [
    ...sessions.map((session) => ({
      type: "charge",
      time: session.endTime,
      value: session,
    })),
    ...trips.map((trip) => ({
      type: "trip",
      time: trip.start,
      value: trip,
    })),
  ].sort((left, right) => (
    left.time - right.time
    || (left.type === "charge" ? -1 : 1)
  ));

  for (const event of events) {
    if (event.type === "charge") {
      const session = event.value;
      if (Number.isFinite(session.startSoc)) {
        inventoryEnergy = clamp(
          session.startSoc * costSettings.batteryCapacityKwh / 100,
          0,
          costSettings.batteryCapacityKwh,
        );
        inventoryCost = inventoryEnergy * inventoryRate;
      }

      const fallbackRate = inventoryRate || firstRate;
      const addedCost = Number.isFinite(session.cost)
        ? session.cost
        : session.batteryEnergy * fallbackRate;
      session.modelCost = addedCost;
      session.costEstimated = (
        !Number.isFinite(session.cost)
        || (
          Number.isFinite(session.priceCoverage)
          && session.priceCoverage < 99
        )
      );
      const targetEnergy = Number.isFinite(session.endSoc)
        ? clamp(
          session.endSoc * costSettings.batteryCapacityKwh / 100,
          0,
          costSettings.batteryCapacityKwh,
        )
        : clamp(
          inventoryEnergy + session.batteryEnergy,
          0,
          costSettings.batteryCapacityKwh,
        );
      const targetCost = inventoryCost + addedCost;
      inventoryEnergy = targetEnergy;
      inventoryRate = inventoryEnergy > 0
        ? targetCost / inventoryEnergy
        : inventoryRate;
      inventoryCost = inventoryEnergy * inventoryRate;
      session.inventoryRateAfter = inventoryRate;
      session.inventoryEnergyAfter = inventoryEnergy;
      session.inventoryValueAfter = inventoryCost;
      batteryRateHistory.push({
        time: session.endTime,
        rate: inventoryRate,
        energy: inventoryEnergy,
        type: "charge",
      });
      continue;
    }

    const trip = event.value;
    if (Number.isFinite(trip.socStart)) {
      inventoryEnergy = clamp(
        trip.socStart * costSettings.batteryCapacityKwh / 100,
        0,
        costSettings.batteryCapacityKwh,
      );
      inventoryCost = inventoryEnergy * inventoryRate;
    }

    trip.batteryRate = inventoryRate;
    trip.cost = trip.energy * inventoryRate;
    trip.costPer100 = trip.km > 0 ? trip.cost / trip.km * 100 : 0;
    inventoryEnergy = Math.max(0, inventoryEnergy - trip.energy);
    inventoryCost = inventoryEnergy * inventoryRate;

    if (Number.isFinite(trip.socEnd)) {
      inventoryEnergy = clamp(
        trip.socEnd * costSettings.batteryCapacityKwh / 100,
        0,
        costSettings.batteryCapacityKwh,
      );
      inventoryCost = inventoryEnergy * inventoryRate;
    }
  }

  if (Number.isFinite(currentSoc)) {
    inventoryEnergy = clamp(
      currentSoc * costSettings.batteryCapacityKwh / 100,
      0,
      costSettings.batteryCapacityKwh,
    );
    inventoryCost = inventoryEnergy * inventoryRate;
  }

  return {
    trips,
    sessions,
    batteryRateHistory,
    currentRate: inventoryRate,
    currentEnergy: inventoryEnergy,
    currentCost: inventoryCost,
    currentSoc,
    firstRate,
    pricedSessionCount: pricedSessions.length,
    estimatedSessionCount: sessions.filter(
      (session) => session.costEstimated,
    ).length,
  };
}

function parsePlannedChargingIntervals(value, now = new Date()) {
  const year = now.getFullYear();
  const reference = now.getTime();
  const halfYear = 183 * 86400000;
  const intervals = [];
  const pattern = /(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})/g;
  for (const match of String(value || "").matchAll(pattern)) {
    const [, day, month, startHour, startMinute, endHour, endMinute] = match;
    let start = new Date(
      year,
      Number(month) - 1,
      Number(day),
      Number(startHour),
      Number(startMinute),
    );
    if (start.getTime() < reference - halfYear) {
      start = new Date(
        year + 1,
        Number(month) - 1,
        Number(day),
        Number(startHour),
        Number(startMinute),
      );
    } else if (start.getTime() > reference + halfYear) {
      start = new Date(
        year - 1,
        Number(month) - 1,
        Number(day),
        Number(startHour),
        Number(startMinute),
      );
    }
    const end = new Date(start);
    end.setHours(Number(endHour), Number(endMinute), 0, 0);
    if (end <= start) end.setDate(end.getDate() + 1);
    intervals.push({ start: start.getTime(), end: end.getTime() });
  }
  return intervals.sort((left, right) => left.start - right.start);
}

function normalizeNordPoolSlots(state) {
  const attributes = state?.attributes || {};
  return [
    ...(Array.isArray(attributes.raw_today) ? attributes.raw_today : []),
    ...(Array.isArray(attributes.raw_tomorrow) ? attributes.raw_tomorrow : []),
  ]
    .map((slot) => ({
      start: new Date(slot.start).getTime(),
      end: new Date(slot.end).getTime(),
      value: toNumber(slot.value),
    }))
    .filter((slot) => (
      Number.isFinite(slot.start)
      && Number.isFinite(slot.end)
      && slot.end > slot.start
      && Number.isFinite(slot.value)
    ))
    .sort((left, right) => left.start - right.start);
}

function weightedPriceForInterval(priceSlots, start, end, fallback) {
  let weightedPrice = 0;
  let coveredDuration = 0;
  for (const slot of priceSlots) {
    const overlapStart = Math.max(start, slot.start);
    const overlapEnd = Math.min(end, slot.end);
    if (overlapEnd <= overlapStart) continue;
    const duration = overlapEnd - overlapStart;
    weightedPrice += slot.value * duration;
    coveredDuration += duration;
  }
  return coveredDuration > 0 ? weightedPrice / coveredDuration : fallback;
}

function buildBatteryRateForecast(
  model,
  plannedState,
  plannedLevelState,
  priceState,
  now = new Date(),
) {
  const nowTime = now.getTime();
  const targetSoc = toNumber(plannedLevelState?.state);
  const currentSoc = toNumber(model.currentSoc);
  if (
    !Number.isFinite(targetSoc)
    || !Number.isFinite(currentSoc)
    || targetSoc <= currentSoc
  ) {
    return [];
  }

  const intervals = parsePlannedChargingIntervals(
    plannedState?.state,
    now,
  ).filter((interval) => interval.end > nowTime);
  if (!intervals.length) return [];

  const priceSlots = normalizeNordPoolSlots(priceState);
  const fallbackPrice = toNumber(priceState?.state);
  const efficiency = clamp(
    costSettings.chargingEfficiencyPercent / 100,
    0.1,
    1,
  );
  const chargingPower = Math.max(0.1, costSettings.defaultChargingPowerKw);
  const targetEnergy = clamp(
    targetSoc * costSettings.batteryCapacityKwh / 100,
    0,
    costSettings.batteryCapacityKwh,
  );
  let remainingEnergy = Math.max(0, targetEnergy - model.currentEnergy);
  let inventoryEnergy = model.currentEnergy;
  let inventoryCost = model.currentCost;
  let inventoryRate = model.currentRate;
  const forecast = [{
    time: nowTime,
    rate: inventoryRate,
    energy: inventoryEnergy,
    type: "forecast",
  }];

  for (const interval of intervals) {
    const start = Math.max(interval.start, nowTime);
    if (interval.end <= start || remainingEnergy <= 0.001) continue;
    const durationHours = (interval.end - start) / 3600000;
    const possibleBatteryEnergy = chargingPower * durationHours * efficiency;
    const addedBatteryEnergy = Math.min(
      remainingEnergy,
      possibleBatteryEnergy,
      costSettings.batteryCapacityKwh - inventoryEnergy,
    );
    if (addedBatteryEnergy <= 0.001) continue;

    const priceCents = weightedPriceForInterval(
      priceSlots,
      start,
      interval.end,
      fallbackPrice,
    );
    if (!Number.isFinite(priceCents)) continue;

    const gridEnergy = addedBatteryEnergy / efficiency;
    const gridUnitCost = (
      priceCents / 100
      + costSettings.deliveryPriceInclVat
    );
    inventoryCost += gridEnergy * gridUnitCost;
    inventoryEnergy += addedBatteryEnergy;
    inventoryRate = inventoryEnergy > 0
      ? inventoryCost / inventoryEnergy
      : inventoryRate;
    remainingEnergy -= addedBatteryEnergy;
    forecast.push({
      time: interval.end,
      rate: inventoryRate,
      energy: inventoryEnergy,
      priceCents,
      addedBatteryEnergy,
      gridEnergy,
      type: "forecast",
    });
  }

  return forecast.length > 1 ? forecast : [];
}

function selectedRange(now = new Date()) {
  return dateRange.range(now, -Infinity);
}

function filterModel(model) {
  let range = selectedRange();
  if (!Number.isFinite(range.start)) {
    const availableTimes = [
      ...model.trips.map((trip) => trip.start),
      ...model.sessions.map((session) => session.startTime),
      ...model.batteryRateHistory.map((point) => point.time),
    ].filter(Number.isFinite);
    range = {
      ...range,
      start: availableTimes.length
        ? Math.min(...availableTimes)
        : Date.now() - 400 * 86400000,
    };
  }
  return {
    range,
    trips: model.trips.filter(
      (trip) => trip.start >= range.start && trip.start < range.end,
    ),
    sessions: model.sessions.filter(
      (session) => (
        session.endTime >= range.start && session.endTime < range.end
      ),
    ),
    batteryRateHistory: model.batteryRateHistory.filter(
      (point) => point.time < range.end,
    ),
    batteryRateForecast: (
      range.end >= Date.now() - 60000
        ? (model.batteryRateForecast || [])
        : []
    ),
  };
}

function localDayKey(time) {
  return localDateValue(new Date(time));
}

function groupDaily(trips) {
  const groups = new Map();
  for (const trip of trips) {
    const key = localDayKey(trip.start);
    if (!groups.has(key)) {
      groups.set(key, { key, km: 0, energy: 0, cost: 0, trips: 0 });
    }
    const group = groups.get(key);
    group.km += trip.km;
    group.energy += trip.energy;
    group.cost += trip.cost;
    group.trips += 1;
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      costPer100: group.km > 0 ? group.cost / group.km * 100 : 0,
      consumption: group.km > 0 ? group.energy / group.km * 100 : 0,
    }))
    .sort((left, right) => left.key.localeCompare(right.key));
}

function formatNumber(value, digits = 1) {
  return Number.isFinite(value)
    ? new Intl.NumberFormat(LOCALES[currentLanguage], {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(value)
    : "-";
}

function formatDateTime(time) {
  return new Intl.DateTimeFormat(LOCALES[currentLanguage], {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(time));
}

function formatDuration(start, end) {
  return Math.max(0, Math.round((end - start) / 60000));
}

function formatSoc(trip) {
  if (
    !Number.isFinite(trip.socStart)
    || !Number.isFinite(trip.socEnd)
  ) {
    return "-";
  }
  return `${formatNumber(trip.socStart, 0)} → ${formatNumber(trip.socEnd, 0)}%`;
}

function setText(id, text) {
  document.getElementById(id).textContent = text;
}

function renderMetrics(filtered, model) {
  const totalKm = filtered.trips.reduce((sum, trip) => sum + trip.km, 0);
  const totalEnergy = filtered.trips.reduce(
    (sum, trip) => sum + trip.energy,
    0,
  );
  const totalCost = filtered.trips.reduce(
    (sum, trip) => sum + trip.cost,
    0,
  );
  const estimatedCount = filtered.trips.filter(
    (trip) => trip.energyEstimated,
  ).length;
  const periodChargeEnergy = filtered.sessions.reduce(
    (sum, session) => sum + session.batteryEnergy,
    0,
  );
  const periodChargeCost = filtered.sessions.reduce(
    (sum, session) => sum + (session.modelCost || 0),
    0,
  );

  setText("mBatteryRate", `${formatNumber(model.currentRate * 100, 2)} c/kWh`);
  setText(
    "mBatteryRateNote",
    model.estimatedSessionCount
      ? t("pricedAndEstimated", {
        priced: model.pricedSessionCount,
        estimated: model.estimatedSessionCount,
      })
      : t("pricedSessions", { count: model.pricedSessionCount }),
  );
  setText("mBatteryEnergy", `${formatNumber(model.currentEnergy, 1)} kWh`);
  setText(
    "mBatteryValue",
    t("batteryValue", {
      soc: formatNumber(model.currentSoc, 0),
      cost: formatNumber(model.currentCost, 2),
    }),
  );
  setText(
    "mCost100",
    totalKm > 0
      ? `${formatNumber(totalCost / totalKm * 100, 2)} EUR`
      : "-",
  );
  setText("mCost100Note", t("per100km"));
  setText(
    "mConsumption",
    totalKm > 0
      ? `${formatNumber(totalEnergy / totalKm * 100, 1)} kWh`
      : "-",
  );
  setText(
    "mConsumptionNote",
    estimatedCount
      ? (
        estimatedCount === 1
          ? t("oneTripEstimated")
          : t("tripsEstimated", { count: estimatedCount })
      )
      : t("per100km"),
  );
  setText("mDistance", `${formatNumber(totalKm, 1)} km`);
  setText("mTrips", t("trips", { count: filtered.trips.length }));
  setText("mDriveCost", `${formatNumber(totalCost, 2)} EUR`);
  setText(
    "mDriveEnergy",
    t("chargedFor", {
      energy: formatNumber(totalEnergy, 1),
      charged: formatNumber(periodChargeEnergy, 1),
      cost: formatNumber(periodChargeCost, 2),
    }),
  );

  return { totalKm, totalEnergy, totalCost, estimatedCount };
}

function renderTable(filtered, summary) {
  rowsEl.replaceChildren();
  emptyEl.hidden = filtered.trips.length > 0;
  totalsEl.hidden = filtered.trips.length === 0;
  tableSummaryEl.textContent = filtered.trips.length
    ? t("trips", { count: filtered.trips.length })
    : t("noTripsShort");

  const newestFirst = [...filtered.trips].sort(
    (left, right) => right.start - left.start,
  );
  for (const trip of newestFirst) {
    const row = document.createElement("tr");
    const estimate = trip.energyEstimated ? "~" : "";
    row.innerHTML = `
      <td>${formatDateTime(trip.start)}<br>${formatDateTime(trip.end)}</td>
      <td>${formatDuration(trip.start, trip.end)}</td>
      <td>${formatSoc(trip)}</td>
      <td>${formatNumber(trip.km, 1)}</td>
      <td class="${trip.energyEstimated ? "estimated" : ""}">${estimate}${formatNumber(trip.energy, 2)}</td>
      <td class="${trip.energyEstimated ? "estimated" : ""}">${estimate}${formatNumber(trip.consumption, 1)}</td>
      <td>${formatNumber(trip.batteryRate * 100, 2)}</td>
      <td>${formatNumber(trip.cost, 2)}</td>
      <td>${formatNumber(trip.costPer100, 2)}</td>
    `;
    rowsEl.appendChild(row);
  }

  totalsEl.innerHTML = `
    <tr>
      <td>${t("totalAverage")}</td>
      <td></td>
      <td></td>
      <td>${formatNumber(summary.totalKm, 1)}</td>
      <td>${formatNumber(summary.totalEnergy, 2)}</td>
      <td>${summary.totalKm > 0 ? formatNumber(summary.totalEnergy / summary.totalKm * 100, 1) : "-"}</td>
      <td></td>
      <td>${formatNumber(summary.totalCost, 2)}</td>
      <td>${summary.totalKm > 0 ? formatNumber(summary.totalCost / summary.totalKm * 100, 2) : "-"}</td>
    </tr>
  `;
}

function prepareCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, Math.floor(rect.width));
  const height = Math.max(180, Math.floor(rect.height));
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { context, width, height };
}

function chartColors() {
  const styles = getComputedStyle(document.documentElement);
  return {
    text: styles.getPropertyValue("--muted").trim(),
    line: styles.getPropertyValue("--line").trim(),
    accent: styles.getPropertyValue("--accent").trim(),
    orange: styles.getPropertyValue("--orange").trim(),
    surface: styles.getPropertyValue("--surface").trim(),
  };
}

function renderEmptyChart(canvas, text) {
  const { context, width, height } = prepareCanvas(canvas);
  const colors = chartColors();
  context.clearRect(0, 0, width, height);
  context.fillStyle = colors.text;
  context.font = "13px Roboto, Segoe UI, Arial";
  context.textAlign = "center";
  context.fillText(text, width / 2, height / 2);
}

function renderBarChart(canvas, points) {
  if (!points.length) {
    renderEmptyChart(canvas, t("noPeriodData"));
    return;
  }
  const { context, width, height } = prepareCanvas(canvas);
  const colors = chartColors();
  const margin = { left: 46, right: 14, top: 12, bottom: 42 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const maxValue = Math.max(0.1, ...points.map((point) => point.costPer100));
  const axisMax = Math.ceil(maxValue * 1.15 * 10) / 10;

  context.clearRect(0, 0, width, height);
  context.font = "11px Roboto, Segoe UI, Arial";
  context.textBaseline = "middle";

  for (let index = 0; index <= 4; index += 1) {
    const y = margin.top + plotHeight * index / 4;
    const value = axisMax * (1 - index / 4);
    context.strokeStyle = colors.line;
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(margin.left, y);
    context.lineTo(width - margin.right, y);
    context.stroke();
    context.fillStyle = colors.text;
    context.textAlign = "right";
    context.fillText(formatNumber(value, 2), margin.left - 7, y);
  }

  const slot = plotWidth / points.length;
  const barWidth = Math.max(4, Math.min(38, slot * 0.62));
  points.forEach((point, index) => {
    const x = margin.left + slot * index + (slot - barWidth) / 2;
    const barHeight = point.costPer100 / axisMax * plotHeight;
    const y = margin.top + plotHeight - barHeight;
    context.fillStyle = colors.accent;
    context.fillRect(x, y, barWidth, barHeight);

    const showLabel = (
      points.length <= 12
      || index % Math.ceil(points.length / 8) === 0
      || index === points.length - 1
    );
    if (showLabel) {
      const labelDate = new Date(`${point.key}T12:00:00`);
      const label = new Intl.DateTimeFormat(LOCALES[currentLanguage], {
        day: "2-digit",
        month: "2-digit",
      }).format(labelDate);
      context.save();
      context.translate(x + barWidth / 2, height - margin.bottom + 17);
      context.rotate(-Math.PI / 5);
      context.fillStyle = colors.text;
      context.textAlign = "right";
      context.fillText(label, 0, 0);
      context.restore();
    }
  });
}

function renderLineChart(canvas, points, forecastPoints, range) {
  const showActual = actualRateToggleEl?.checked !== false;
  const showForecast = forecastRateToggleEl?.checked !== false;
  const now = Date.now();
  const forecastEnd = showForecast && forecastPoints.length
    ? forecastPoints.at(-1).time
    : -Infinity;
  const startTime = Number.isFinite(range.start)
    ? range.start
    : Math.min(
      points[0]?.time ?? now,
      forecastPoints[0]?.time ?? now,
    );
  const baseEnd = Number.isFinite(range.end) ? range.end : now;
  const endTime = Math.max(startTime + 3600000, baseEnd, forecastEnd);

  const actual = showActual
    ? points.filter(
      (point) => point.time >= startTime && point.time <= endTime,
    )
    : [];
  if (showActual) {
    const leading = [...points]
      .reverse()
      .find((point) => point.time < startTime);
    if (leading) actual.unshift({ ...leading, time: startTime });
    const last = actual.at(-1);
    const actualEnd = Math.min(endTime, now);
    if (last && last.time < actualEnd) {
      actual.push({ ...last, time: actualEnd, type: "hold" });
    }
  }

  const forecast = showForecast
    ? forecastPoints.filter(
      (point) => point.time >= startTime && point.time <= endTime,
    )
    : [];
  const visible = [...actual, ...forecast];
  if (!visible.length) {
    renderEmptyChart(canvas, t("noChargePriceData"));
    return;
  }

  const { context, width, height } = prepareCanvas(canvas);
  const colors = chartColors();
  const margin = { left: 48, right: 14, top: 12, bottom: 40 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const values = visible.map((point) => point.rate * 100);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const padding = Math.max(0.2, (maximum - minimum) * 0.2);
  const axisMin = Math.max(0, minimum - padding);
  const axisMax = Math.max(axisMin + 0.5, maximum + padding);
  const xFor = (time) => (
    margin.left + (time - startTime) / (endTime - startTime) * plotWidth
  );
  const yFor = (value) => (
    margin.top + (axisMax - value) / (axisMax - axisMin) * plotHeight
  );

  context.clearRect(0, 0, width, height);
  context.font = "11px Roboto, Segoe UI, Arial";
  context.textBaseline = "middle";

  for (let index = 0; index <= 4; index += 1) {
    const y = margin.top + plotHeight * index / 4;
    const value = axisMax - (axisMax - axisMin) * index / 4;
    context.strokeStyle = colors.line;
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(margin.left, y);
    context.lineTo(width - margin.right, y);
    context.stroke();
    context.fillStyle = colors.text;
    context.textAlign = "right";
    context.fillText(formatNumber(value, 2), margin.left - 7, y);
  }

  const drawStepSeries = (series, color, dashed = false) => {
    if (!series.length) return;
    context.save();
    context.strokeStyle = color;
    context.lineWidth = 2.5;
    context.setLineDash(dashed ? [8, 6] : []);
    context.beginPath();
    series.forEach((point, index) => {
      const x = xFor(point.time);
      const y = yFor(point.rate * 100);
      if (index === 0) {
        context.moveTo(x, y);
      } else {
        const previous = series[index - 1];
        context.lineTo(x, yFor(previous.rate * 100));
        context.lineTo(x, y);
      }
    });
    context.stroke();
    context.restore();
  };

  drawStepSeries(actual, colors.orange);
  drawStepSeries(forecast, colors.accent, true);

  const labelCount = 5;
  for (let index = 0; index < labelCount; index += 1) {
    const ratio = index / (labelCount - 1);
    const time = startTime + (endTime - startTime) * ratio;
    const x = margin.left + plotWidth * ratio;
    const label = new Intl.DateTimeFormat(LOCALES[currentLanguage], {
      day: "2-digit",
      month: "2-digit",
    }).format(new Date(time));
    context.fillStyle = colors.text;
    context.textAlign = index === 0
      ? "left"
      : (index === labelCount - 1 ? "right" : "center");
    context.fillText(label, x, height - 18);
  }
}

function render(model) {
  const filtered = filterModel(model);
  const summary = renderMetrics(filtered, model);
  renderTable(filtered, summary);
  renderBarChart(dailyCanvas, groupDaily(filtered.trips));
  renderLineChart(
    batteryCanvas,
    filtered.batteryRateHistory,
    filtered.batteryRateForecast,
    filtered.range,
  );
}

async function loadSessionState() {
  let lastError = null;
  for (const entityId of ENTITY.sessions) {
    try {
      const state = await haFetch(
        `/api/states/${encodeURIComponent(entityId)}`,
      );
      const sessions = state.attributes?.sessions;
      if (Array.isArray(sessions)) return { state, entityId, sessions };
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error(t("sessionsUnavailable"));
}

async function loadOptionalState(entityId) {
  try {
    return await haFetch(`/api/states/${encodeURIComponent(entityId)}`);
  } catch (error) {
    console.debug(`Optional entity ${entityId} is unavailable`, error);
    return null;
  }
}

async function loadModel() {
  if (loadingModel) return;
  loadingModel = true;
  setStatus(t("loading"));
  reloadEl.disabled = true;
  try {
    const [
      sessionState,
      batteryState,
      _settings,
      nordPoolState,
      plannedState,
      plannedLevelState,
    ] = await Promise.all([
      loadSessionState(),
      haFetch(`/api/states/${encodeURIComponent(ENTITY.battery)}`),
      loadCostSettings(),
      loadOptionalState(ENTITY.nordPoolPrice),
      loadOptionalState(ENTITY.plannedCharging),
      loadOptionalState(ENTITY.plannedChargeLevel),
    ]);
    const sessions = normalizeSessions(sessionState.sessions);
    if (!sessions.length) {
      throw new Error(t("sessionsEmpty"));
    }

    const historyStart = new Date(
      sessions[0].startTime - MAX_ENERGY_LOOKBACK_MIN * 60000,
    );
    const historyEnd = new Date();
    const entityIds = [
      ENTITY.location,
      ENTITY.mileage,
      ENTITY.battery,
    ].join(",");
    const historyPath = (
      `/api/history/period/${encodeURIComponent(historyStart.toISOString())}`
      + `?end_time=${encodeURIComponent(historyEnd.toISOString())}`
      + `&filter_entity_id=${encodeURIComponent(entityIds)}`
    );
    const history = await haFetch(historyPath);
    const trips = buildTrips(history);
    const learnedConsumption = normalizeTripEnergy(trips);
    const currentSoc = toNumber(batteryState.state);
    const model = applyWeightedCostModel(trips, sessions, currentSoc);
    model.batteryRateForecast = buildBatteryRateForecast(
      model,
      plannedState,
      plannedLevelState,
      nordPoolState,
    );
    model.learnedConsumption = learnedConsumption;
    model.sessionEntityId = sessionState.entityId;
    lastModel = model;
    render(model);
    lastSourceSignature = await currentSourceSignature();

    const lastUpdate = new Intl.DateTimeFormat(LOCALES[currentLanguage], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date());
    const estimatedCount = trips.filter(
      (trip) => trip.energyEstimated,
    ).length;
    const estimate = estimatedCount === 1
      ? t("oneEstimate")
      : (
        estimatedCount > 1
          ? t("estimates", { count: estimatedCount })
          : ""
      );
    setStatus(t("updated", {
      time: lastUpdate,
      charges: sessions.length,
      trips: trips.length,
      consumption: formatNumber(learnedConsumption, 1),
      estimate,
    }));
  } catch (error) {
    console.error(error);
    setStatus(t("loadError", { error: error.message }), true);
    renderEmptyChart(dailyCanvas, t("dataUnavailable"));
    renderEmptyChart(batteryCanvas, t("dataUnavailable"));
  } finally {
    reloadEl.disabled = false;
    loadingModel = false;
  }
}

async function currentSourceSignature() {
  const hass = await getParentHass();
  if (!hass?.states) return "";
  const entityIds = [
    ...ENTITY.sessions,
    ENTITY.battery,
    ENTITY.costSettings,
    ENTITY.nordPoolPrice,
    ENTITY.plannedCharging,
    ENTITY.plannedChargeLevel,
  ];
  return entityIds.map((entityId) => {
    const state = hass.states[entityId];
    return `${entityId}:${state?.state || ""}:${state?.last_updated || ""}`;
  }).join("|");
}

async function reloadWhenSourceChanges() {
  if (document.hidden || loadingModel) return;
  const signature = await currentSourceSignature();
  if (!signature) return;
  if (!lastSourceSignature) {
    lastSourceSignature = signature;
    return;
  }
  if (signature !== lastSourceSignature) await loadModel();
}

function navigateSettings(event) {
  if (window.parent === window) return;
  event.preventDefault();
  const path = event.currentTarget.getAttribute("href");
  window.parent.history.pushState(null, "", path);
  window.parent.dispatchEvent(new window.parent.Event("location-changed"));
}

document.querySelectorAll("a.settings-link").forEach((link) => {
  link.addEventListener("click", navigateSettings);
});
dateRange = window.RenaultDateRange.attach({
  periodEl,
  startEl: dayDateEl,
  endEl: dayDateToEl,
  clearEl: clearDateEl,
  defaultPreset: "current_month",
  language: currentLanguage,
  onChange: () => {
    if (lastModel) render(lastModel);
  },
});
[actualRateToggleEl, forecastRateToggleEl].forEach((toggle) => {
  toggle?.addEventListener("change", () => {
    if (lastModel) render(lastModel);
  });
});
reloadEl.addEventListener("click", loadModel);
window.addEventListener("resize", () => {
  if (lastModel) render(lastModel);
});
window.setInterval(() => {
  if (!document.hidden) loadModel();
}, AUTO_REFRESH_MS);
window.setInterval(reloadWhenSourceChanges, SOURCE_CHANGE_CHECK_MS);

applyLanguage();
setStatus(t("loadingInitial"));
loadModel();
