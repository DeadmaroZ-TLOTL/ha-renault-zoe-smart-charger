"use strict";

const SETTINGS_ENTITY = "sensor.renault_zoe_new_cost_settings";
const DEFAULT_CENTER = [56.9496, 24.1052];
const DEFAULT_ZOOM = 10;
const LIST_PAGE_SIZE = 40;
const FILTERED_LIST_PAGE_SIZE = 200;
const MAX_PRICE_LABELS = 80;
const DETAIL_CACHE_MS = 30 * 60 * 1000;
const DETAIL_PREFETCH_BATCH_SIZE = 40;
const DETAIL_PREFETCH_SCOPE_LIMIT = 40;
const DETAIL_PREFETCH_CONCURRENCY = 3;
const DETAIL_PREFETCH_DELAY_MS = 260;
const DETAIL_PREFETCH_NEXT_BATCH_DELAY_MS = 450;
const DETAIL_REQUEST_RETRY_DELAY_MS = 1800;
const DETAIL_RETRY_MS = 5 * 60 * 1000;
const LOAD_RETRY_DELAY_MS = 5000;
const LOAD_RETRY_LIMIT = 12;
const LIVE_DETAIL_PROVIDERS = new Set(["elektrum", "mobilly"]);
const CONNECTOR_FILTER_STORAGE = "zoe-stations-disabled-connectors";
const OPERATOR_FILTER_STORAGE = "zoe-stations-disabled-operators";
const CHEAPEST_DISTANCE_STORAGE = "zoe-stations-cheapest-distance-km";
const DEFAULT_CHEAPEST_DISTANCE_KM = 50;

const I18N = {
  lv: {
    plugFilters: "Spraudņi",
    operatorFilters: "Operatori",
    enableAll: "Ieslēgt visus",
    filterCount: "{enabled}/{total}",
    findNearest: "Tuvākās",
    maxDistance: "Maks. attālums",
    findCheapest: "Tuvākā lētākā",
    locating: "Meklēju tuvākās atbilstošās stacijas...",
    findingCheapest: "Meklēju lētāko staciju norādītajā attālumā...",
    nearestFound: "Atrastas {count} atbilstošas stacijas; tuvākā ir {distance} km.",
    cheapestFound: "Lētākā zināmā cena {price}; stacija ir {distance} km attālumā.",
    noMatchingStations: "Nav staciju ar izvēlētajiem spraudņiem un operatoriem.",
    noStationsInRange: "Norādītajā attālumā nav izvēlētajiem filtriem atbilstošu staciju.",
    noPricedStations: "Norādītajā attālumā nav staciju ar zināmu salīdzināmu cenu.",
    invalidDistance: "Ievadi maksimālo attālumu no 1 līdz 500 km.",
    googleDirections: "Google Maps",
    wazeDirections: "Waze",
    occupiedSince: "Aizņemts kopš",
    observedSince: "Novērots kopš {time}",
    timeUnavailable: "Laiks nav pieejams",
    priceLoading: "Ielādēju cenu",
    operator: "Operators",
    description: "Apraksts un piekļuve",
    plugNumber: "Spraudnis {number}",
    title: "Uzlādes stacijas",
    subtitle: "Elektrum Drive, Mobilly, e-mobi, Ignitis ON, IKRAUTAS, Latvijas NPP un PlugShare",
    search: "Meklēt",
    searchPlaceholder: "Meklēt vietu vai adresi",
    allPowers: "Visas jaudas",
    settings: "Iestatījumi",
    locate: "Rādīt auto atrašanās vietu",
    refresh: "Atjaunot",
    allProviders: "Visi",
    availableOnly: "Tikai zināmi brīvas",
    loading: "Ielādēju stacijas...",
    map: "Karte",
    available: "Brīva",
    selectStation: "Izvēlies staciju kartē vai sarakstā",
    selectStationHint: "Pēc izvēles tiks nolasīts aktuālais savienotāju statuss un cena.",
    nearby: "Tuvākās kartes centram",
    total: "Stacijas",
    elektrum: "Elektrum Drive",
    mobilly: "Mobilly",
    emobi: "e-mobi",
    nap: "Latvijas NPP",
    ignitis: "Ignitis ON",
    ikrautas: "IKRAUTAS",
    sourceRecords: "Avotu ieraksti",
    visible: "Redzamas",
    loaded: "Ielādētas {count} unikālas stacijas no {sourceCount} avotu ierakstiem.",
    partial: "Daļa datu nav pieejama: {errors}",
    loadFailed: "Neizdevās ielādēt stacijas: {error}",
    mapCount: "Kartē visas {count} stacijas",
    listCount: "Parādītas {shown} no {count}",
    showMoreStations: "Parādīt vēl ({remaining} atlikušas)",
    sourceCount: "{count} avotā",
    connectors: "Savienotāji",
    power: "Maks. jauda",
    price: "Cena",
    availability: "Pieejamība",
    unknown: "Nav zināms",
    occupied: "Aizņemta",
    unavailable: "Nav pieejama",
    statusAvailable: "Brīvs",
    statusOccupied: "Aizņemts",
    statusCharging: "Notiek uzlāde",
    statusUnknown: "Nav zināms",
    route: "Atvērt maršrutu",
    whatsapp: "Nosūtīt WhatsApp",
    detailLoading: "Nolasu aktuālo statusu un cenu...",
    liveUnavailable: "Mobilly publiskais katalogs rāda vietu, spraudņus un jaudu. Dzīvajam aizņemtības statusam un cenai nepieciešama Mobilly mobilā sesija.",
    liveError: "Aktuālos datus neizdevās nolasīt; redzami publiskā kataloga dati.",
    connectorCount: "{count} gab.",
    fromPrice: "no {price}",
    noLocation: "Renault atrašanās vieta pašlaik nav pieejama.",
    stationShare: "{name}\n{address}\n{url}",
    plugshareMap: "PlugShare karte",
    openPlugShare: "Atvērt PlugShare",
  },
  en: {
    plugFilters: "Plugs",
    operatorFilters: "Operators",
    enableAll: "Enable all",
    filterCount: "{enabled}/{total}",
    findNearest: "Nearest",
    maxDistance: "Max distance",
    findCheapest: "Nearest cheapest",
    locating: "Finding the nearest matching stations...",
    findingCheapest: "Finding the cheapest station within the selected distance...",
    nearestFound: "Found {count} matching stations; the nearest is {distance} km away.",
    cheapestFound: "The lowest known price is {price}; the station is {distance} km away.",
    noMatchingStations: "No stations match the selected plugs and operators.",
    noStationsInRange: "No station matching the selected filters is within that distance.",
    noPricedStations: "No station with a known comparable price is within that distance.",
    invalidDistance: "Enter a maximum distance from 1 to 500 km.",
    googleDirections: "Google Maps",
    wazeDirections: "Waze",
    occupiedSince: "Occupied since",
    observedSince: "Observed since {time}",
    timeUnavailable: "Time unavailable",
    priceLoading: "Loading price",
    operator: "Operator",
    description: "Description and access",
    plugNumber: "Plug {number}",
    title: "Charging stations",
    subtitle: "Elektrum Drive, Mobilly, e-mobi, Ignitis ON, IKRAUTAS, Latvia NAP, and PlugShare",
    search: "Search",
    searchPlaceholder: "Search place or address",
    allPowers: "All power levels",
    settings: "Settings",
    locate: "Show vehicle location",
    refresh: "Refresh",
    allProviders: "All",
    availableOnly: "Known available only",
    loading: "Loading stations...",
    map: "Map",
    available: "Available",
    selectStation: "Select a station on the map or in the list",
    selectStationHint: "The current connector status and price will load after selection.",
    nearby: "Nearest to map center",
    total: "Stations",
    elektrum: "Elektrum Drive",
    mobilly: "Mobilly",
    emobi: "e-mobi",
    nap: "Latvia NAP",
    ignitis: "Ignitis ON",
    ikrautas: "IKRAUTAS",
    sourceRecords: "Source records",
    visible: "Visible",
    loaded: "Loaded {count} unique stations from {sourceCount} source records.",
    partial: "Some data is unavailable: {errors}",
    loadFailed: "Unable to load stations: {error}",
    mapCount: "All {count} stations on map",
    listCount: "Showing {shown} of {count}",
    showMoreStations: "Show more ({remaining} remaining)",
    sourceCount: "{count} at source",
    connectors: "Connectors",
    power: "Max power",
    price: "Price",
    availability: "Availability",
    unknown: "Unknown",
    occupied: "Occupied",
    unavailable: "Unavailable",
    statusAvailable: "Available",
    statusOccupied: "Occupied",
    statusCharging: "Charging",
    statusUnknown: "Unknown",
    route: "Open directions",
    whatsapp: "Share in WhatsApp",
    detailLoading: "Reading current status and price...",
    liveUnavailable: "The Mobilly public catalog provides location, plugs, and power. Live availability and pricing require a Mobilly mobile session.",
    liveError: "Live data could not be read; public catalog data is shown.",
    connectorCount: "{count} pcs.",
    fromPrice: "from {price}",
    noLocation: "The Renault location is currently unavailable.",
    stationShare: "{name}\n{address}\n{url}",
    plugshareMap: "PlugShare map",
    openPlugShare: "Open PlugShare",
  },
};

let language = "lv";
let map;
let stationLayer;
let priceLabelLayer;
let vehicleMarker;
let stations = [];
let filteredStations = [];
let sourceStationCount = 0;
let sourceCounts = {};
let vehicleLocation = null;
let selectedProvider = "all";
let selectedStationKey = "";
let selectedStation = null;
let markerByKey = new Map();
let detailsCache = new Map();
let detailRequests = new Map();
let cachedParentHass = null;
let searchTimer = null;
let loadRetryTimer = null;
let loadRetryAttempt = 0;
let detailPrefetchTimer = null;
let detailPrefetchRunning = false;
let detailPrefetchQueued = false;
let detailPrefetchFailures = new Map();
let detailPrefetchGeneration = 0;
let listOrigin = null;
let stationListLimit = LIST_PAGE_SIZE;
let disabledConnectorTypes = readStoredSet(CONNECTOR_FILTER_STORAGE);
let disabledOperators = readStoredSet(OPERATOR_FILTER_STORAGE);

const statusEl = document.getElementById("status");
const metricsEl = document.getElementById("metrics");
const mapSubtitleEl = document.getElementById("mapSubtitle");
const listSubtitleEl = document.getElementById("listSubtitle");
const stationListEl = document.getElementById("stationList");
const showAllStationsEl = document.getElementById("showAllStations");
const stationDetailEl = document.getElementById("stationDetail");
const searchEl = document.getElementById("search");
const powerFilterEl = document.getElementById("powerFilter");
const availableOnlyEl = document.getElementById("availableOnly");
const reloadEl = document.getElementById("reload");
const nearestEl = document.getElementById("nearest");
const cheapestEl = document.getElementById("cheapest");
const cheapestDistanceEl = document.getElementById("cheapestDistance");
const connectorOptionsEl = document.getElementById("connectorOptions");
const operatorOptionsEl = document.getElementById("operatorOptions");
const connectorFilterLabelEl = document.getElementById("connectorFilterLabel");
const operatorFilterLabelEl = document.getElementById("operatorFilterLabel");
const localStationsViewEl = document.getElementById("localStationsView");
const plugsharePanelEl = document.getElementById("plugsharePanel");
const plugshareFrameEl = document.getElementById("plugshareFrame");
const openPlugShareEl = document.getElementById("openPlugShare");
const localFilterEls = [
  searchEl.closest(".search-field"),
  powerFilterEl,
  document.getElementById("connectorFilterMenu"),
  document.getElementById("operatorFilterMenu"),
  nearestEl,
  cheapestDistanceEl.closest(".distance-field"),
  cheapestEl,
  availableOnlyEl.closest("label"),
  document.getElementById("locate"),
  reloadEl,
].filter(Boolean);

function t(key, values = {}) {
  let result = I18N[language][key] ?? I18N.lv[key] ?? key;
  for (const [name, value] of Object.entries(values)) {
    result = result.replaceAll(`{${name}}`, String(value));
  }
  return result;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function readStoredSet(key) {
  try {
    const value = JSON.parse(window.localStorage.getItem(key) || "[]");
    return new Set(Array.isArray(value) ? value.map(String) : []);
  } catch (_error) {
    return new Set();
  }
}

function storeSet(key, values) {
  try {
    window.localStorage.setItem(key, JSON.stringify([...values].sort()));
  } catch (_error) {
    // Filtering still works when storage is unavailable in a restricted iframe.
  }
}

function readStoredNumber(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw == null || !raw.trim()) return fallback;
    const value = Number(raw);
    return Number.isFinite(value) ? value : fallback;
  } catch (_error) {
    return fallback;
  }
}

function storeNumber(key, value) {
  try {
    window.localStorage.setItem(key, String(value));
  } catch (_error) {
    // The control remains usable when storage is unavailable in a restricted iframe.
  }
}

function plugshareRegion() {
  const center = vehicleLocation
    ? { lat: vehicleLocation.latitude, lng: vehicleLocation.longitude }
    : map?.getCenter() || { lat: DEFAULT_CENTER[0], lng: DEFAULT_CENTER[1] };
  return {
    latitude: Number(center.lat),
    longitude: Number(center.lng),
    spanLat: 0.55,
    spanLng: 0.85,
  };
}

function updatePlugShareMap() {
  const region = plugshareRegion();
  const query = new URLSearchParams({
    latitude: region.latitude.toFixed(6),
    longitude: region.longitude.toFixed(6),
    spanLat: String(region.spanLat),
    spanLng: String(region.spanLng),
  });
  const widgetUrl = `https://www.plugshare.com/widget2.html?${query}`;
  const permalinkUrl = `https://api.plugshare.com/view/map?${query}`;
  if (plugshareFrameEl.dataset.url !== widgetUrl) {
    plugshareFrameEl.src = widgetUrl;
    plugshareFrameEl.dataset.url = widgetUrl;
  }
  openPlugShareEl.href = permalinkUrl;
}

function resetStationListLimit() {
  stationListLimit = searchEl.value.trim() || selectedProvider !== "all"
    ? FILTERED_LIST_PAGE_SIZE
    : LIST_PAGE_SIZE;
}

function showProviderView(provider) {
  const showPlugShare = provider === "plugshare";
  localStationsViewEl.hidden = showPlugShare;
  plugsharePanelEl.hidden = !showPlugShare;
  for (const control of localFilterEls) control.hidden = showPlugShare;
  if (showPlugShare) {
    updatePlugShareMap();
    return;
  }
  resetStationListLimit();
  applyFilters();
  if (provider !== "all") {
    fitMapToStations(filteredStations);
  }
  window.setTimeout(() => map?.invalidateSize(), 0);
}

function fitMapToStations(items) {
  if (!map || !items.length) return;
  if (items.length === 1) {
    map.setView([items[0].latitude, items[0].longitude], 14);
    return;
  }
  const bounds = L.latLngBounds(
    items.map((station) => [station.latitude, station.longitude]),
  );
  if (bounds.isValid()) {
    map.fitBounds(bounds, { padding: [34, 34], maxZoom: 11 });
  }
}

function canonicalConnectorType(value) {
  const source = String(value || "Unknown").trim();
  const normalized = source.toLowerCase().replaceAll(/[^a-z0-9]/g, "");
  if (normalized.includes("ccs") || normalized.includes("combo")) return "CCS";
  if (normalized.includes("chademo")) return "CHAdeMO";
  if (normalized.includes("type2") || normalized === "t2") return "Type 2";
  if (normalized.includes("type1") || normalized === "t1") return "Type 1";
  if (normalized.includes("schuko")) return "Schuko";
  if (normalized.includes("tesla")) return "Tesla";
  return source || "Unknown";
}

function offersForProvider(station, group = selectedProvider) {
  return stationOffers(station)
    .filter((offer) => group === "all" || (offer.provider_group || offer.provider) === group);
}

function stationConnectors(station, group = selectedProvider) {
  const offers = offersForProvider(station, group);
  const offered = offers
    .flatMap((offer) => Array.isArray(offer.connectors) ? offer.connectors : []);
  const source = offers.length
    ? offered
    : (Array.isArray(station.connectors) ? station.connectors : []);
  const seen = new Set();
  return source.filter((connector) => {
    const key = [
      connector.code,
      connector.connector_number ?? connector.connector_index,
      connector.connector_type || connector.type,
      connector.power_kw,
    ].join("|");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function connectorTypes(station, group = selectedProvider) {
  const values = stationConnectors(station, group)
    .map((connector) => canonicalConnectorType(connector.connector_type || connector.type));
  return [...new Set(values)];
}

function stationOperators(station, group = selectedProvider) {
  const values = offersForProvider(station, group).map((offer) => String(
    offer.operator || providerLabel(offer.provider_group || offer.provider),
  ));
  if (!values.length) {
    values.push(String(station.operator || providerLabel(providerGroup(station))));
  }
  return [...new Set(values.filter(Boolean))];
}

function stationOperator(station, group = selectedProvider) {
  return stationOperators(station, group).join(", ");
}

function stationAvailability(station, group = selectedProvider) {
  const offers = offersForProvider(station, group);
  const statuses = offers
    .map((offer) => String(offer.availability || "unknown").toLowerCase());
  if (statuses.includes("available")) return "available";
  if (statuses.some((status) => [
    "occupied", "charging", "finishing", "preparing", "suspendedev", "suspendedevse",
  ].includes(status))) return "occupied";
  if (statuses.some((status) => status === "unavailable")) return "unavailable";
  if (offers.length) return "unknown";
  return station.availability || "unknown";
}

function stationMaxPower(station, group = selectedProvider) {
  const offers = offersForProvider(station, group);
  const values = offers
    .map((offer) => Number(offer.max_power_kw))
    .filter(Number.isFinite);
  if (values.length) return Math.max(...values);
  if (offers.length) return null;
  return Number(station.max_power_kw) || null;
}

function providerGroup(station) {
  return station.provider_group || station.provider;
}

function providerGroups(station) {
  const groups = Array.isArray(station.provider_groups)
    ? station.provider_groups.map(String)
    : [providerGroup(station)];
  return [...new Set(groups.filter(Boolean))];
}

function stationOffers(station) {
  if (Array.isArray(station.provider_offers) && station.provider_offers.length) {
    return station.provider_offers;
  }
  return [{
    provider: station.provider,
    provider_group: providerGroup(station),
    id: station.id,
    operator: station.operator,
    description: station.description,
    descriptions: station.descriptions,
    price_c_per_kwh: station.price_c_per_kwh,
    price_value: station.price_value,
    price_unit: station.price_unit,
    price_formatted: station.price_formatted,
    availability: station.availability,
    live_data_available: station.live_data_available,
    connector_live_data_available: station.connector_live_data_available,
    connectors: Array.isArray(station.connectors) ? station.connectors : [],
    connector_count: station.connector_count,
    max_power_kw: station.max_power_kw,
  }];
}

function stationDescriptions(station) {
  const excluded = new Set(
    [station.name, station.address, station.city]
      .filter(Boolean)
      .map((value) => String(value).trim().toLocaleLowerCase(language === "lv" ? "lv-LV" : "en-GB")),
  );
  const values = [
    ...(Array.isArray(station.descriptions) ? station.descriptions : []),
    station.description,
    ...stationOffers(station).flatMap((offer) => [
      ...(Array.isArray(offer.descriptions) ? offer.descriptions : []),
      offer.description,
    ]),
  ];
  const seen = new Set();
  const result = [];
  for (const value of values) {
    if (typeof value !== "string") continue;
    for (const line of value.split(/\r?\n/)) {
      const text = line.replaceAll(/\s+/g, " ").trim();
      const normalized = text.toLocaleLowerCase(language === "lv" ? "lv-LV" : "en-GB");
      if (!text || excluded.has(normalized) || seen.has(normalized)) continue;
      seen.add(normalized);
      result.push(text);
    }
  }
  return result;
}

function providerLabel(provider) {
  if (provider === "elektrum" || provider === "emobi_elektrum") return "Elektrum Drive";
  if (provider === "emobi") return "e-mobi";
  if (provider === "nap" || provider === "latvia_nap") return t("nap");
  if (provider === "mobilly") return "Mobilly";
  if (provider === "ignitis" || provider === "ignitis_on") return "Ignitis ON";
  if (provider === "ikrautas") return "IKRAUTAS";
  return String(provider || t("unknown"));
}

function formatStatusTime(connector) {
  const value = connector.status_since || connector.status_observed_since;
  if (!value) return t("timeUnavailable");
  const time = new Date(value);
  if (!Number.isFinite(time.getTime())) return t("timeUnavailable");
  const formatted = new Intl.DateTimeFormat(language === "lv" ? "lv-LV" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(time);
  return connector.status_time_source === "home_assistant_observation"
    ? t("observedSince", { time: formatted })
    : formatted;
}

function connectorNumberLabel(connector) {
  const number = connector.connector_number ?? connector.connector_index;
  return number == null ? "" : t("plugNumber", { number });
}

function stationKey(station) {
  return `${station.provider}:${station.id}`;
}

function applyLanguage() {
  document.documentElement.lang = language;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = t(element.dataset.i18n);
  }
  for (const element of document.querySelectorAll("[data-i18n-title]")) {
    const label = t(element.dataset.i18nTitle);
    element.title = label;
    element.setAttribute("aria-label", label);
  }
  searchEl.placeholder = t("searchPlaceholder");
  renderFilterMenus();
}

function renderFilterMenus() {
  if (!connectorOptionsEl || !operatorOptionsEl) return;
  const connectorValues = [...new Set(stations.flatMap(connectorTypes))]
    .sort((left, right) => left.localeCompare(right, language));
  const operatorValues = [...new Set(stations.flatMap((station) => stationOperators(station, "all")))]
    .sort((left, right) => left.localeCompare(right, language));

  connectorOptionsEl.innerHTML = connectorValues.map((value) => `
    <label class="filter-option">
      <input type="checkbox" data-connector-filter="${escapeHtml(value)}" ${disabledConnectorTypes.has(value) ? "" : "checked"} />
      <span>${escapeHtml(value)}</span>
    </label>
  `).join("");
  operatorOptionsEl.innerHTML = operatorValues.map((value) => `
    <label class="filter-option">
      <input type="checkbox" data-operator-filter="${escapeHtml(value)}" ${disabledOperators.has(value) ? "" : "checked"} />
      <span>${escapeHtml(value)}</span>
    </label>
  `).join("");

  const connectorEnabled = connectorValues.filter((value) => !disabledConnectorTypes.has(value)).length;
  const operatorEnabled = operatorValues.filter((value) => !disabledOperators.has(value)).length;
  connectorFilterLabelEl.textContent = `${t("plugFilters")} ${t("filterCount", { enabled: connectorEnabled, total: connectorValues.length })}`;
  operatorFilterLabelEl.textContent = `${t("operatorFilters")} ${t("filterCount", { enabled: operatorEnabled, total: operatorValues.length })}`;

  for (const input of connectorOptionsEl.querySelectorAll("[data-connector-filter]")) {
    input.addEventListener("change", () => {
      if (input.checked) disabledConnectorTypes.delete(input.dataset.connectorFilter);
      else disabledConnectorTypes.add(input.dataset.connectorFilter);
      storeSet(CONNECTOR_FILTER_STORAGE, disabledConnectorTypes);
      renderFilterMenus();
      applyFilters();
    });
  }
  for (const input of operatorOptionsEl.querySelectorAll("[data-operator-filter]")) {
    input.addEventListener("change", () => {
      if (input.checked) disabledOperators.delete(input.dataset.operatorFilter);
      else disabledOperators.add(input.dataset.operatorFilter);
      storeSet(OPERATOR_FILTER_STORAGE, disabledOperators);
      renderFilterMenus();
      applyFilters();
    });
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
    } catch (_error) {
      return null;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 100));
  }
  return null;
}

function parseMaybeJson(value) {
  try {
    return JSON.parse(value);
  } catch (_error) {
    return null;
  }
}

async function refreshAccessToken(tokens) {
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
    const refreshed = await refreshAccessToken(direct);
    if (refreshed) return refreshed;
  }
  for (let index = 0; index < localStorage.length; index += 1) {
    const value = parseMaybeJson(localStorage.getItem(localStorage.key(index)));
    if (value?.access_token) return value.access_token;
  }
  return null;
}

async function haApi(path) {
  const hass = await getParentHass();
  const apiPath = path.replace(/^\/api\//, "");
  const separator = apiPath.includes("?") ? "&" : "?";
  const uncachedApiPath = `${apiPath}${separator}_=${Date.now()}`;
  if (hass?.callApi) {
    try {
      return await hass.callApi("GET", uncachedApiPath);
    } catch (error) {
      console.debug("Parent Home Assistant API request failed", error);
    }
  }
  const token = await getAccessToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await fetch(`/api/${uncachedApiPath}`, {
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function formatError(error) {
  if (typeof error === "string") return error;
  for (const candidate of [
    error?.message,
    error?.error,
    error?.body?.message,
    error?.body?.error,
  ]) {
    if (typeof candidate === "string" && candidate.trim()) return candidate;
  }
  try {
    const serialized = JSON.stringify(error);
    if (serialized && serialized !== "{}") return serialized;
  } catch (_serializationError) {
    // Fall through to a stable message below.
  }
  return "Unknown Home Assistant API error";
}

function ensureMap() {
  if (map) return;
  map = L.map("map", { preferCanvas: true, zoomControl: true }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    maxZoom: 20,
    attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
  }).addTo(map);
  stationLayer = typeof L.markerClusterGroup === "function"
    ? L.markerClusterGroup({
      chunkedLoading: true,
      chunkInterval: 50,
      chunkDelay: 10,
      removeOutsideVisibleBounds: true,
      showCoverageOnHover: false,
      spiderfyOnMaxZoom: true,
      disableClusteringAtZoom: 15,
      maxClusterRadius: 55,
      iconCreateFunction(cluster) {
        const count = cluster.getChildCount();
        const size = count >= 100 ? 48 : count >= 10 ? 42 : 36;
        return L.divIcon({
          html: `<span>${count}</span>`,
          className: "station-cluster",
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
        });
      },
    })
    : L.layerGroup();
  stationLayer.addTo(map);
  priceLabelLayer = L.layerGroup().addTo(map);
  map.on("moveend", () => {
    renderPriceLabels();
    renderStationList();
    detailPrefetchGeneration += 1;
    scheduleDetailPrefetch();
  });
}

function formatNumber(value, digits = 1) {
  if (!Number.isFinite(Number(value))) return "-";
  return new Intl.NumberFormat(language === "lv" ? "lv-LV" : "en-GB", {
    maximumFractionDigits: digits,
  }).format(Number(value));
}

function priceLabel(item) {
  if (!item) return t("unknown");
  if (item.price_formatted) return String(item.price_formatted);
  const value = item.price_value ?? item.price_c_per_kwh;
  if (value === null || value === undefined || value === "") return t("unknown");
  if (!Number.isFinite(Number(value))) return t("unknown");
  const unit = item.price_unit || "kWh";
  return `${formatNumber(value, 2)} c/${unit}`;
}

function priceSummary(station, group = selectedProvider) {
  const offers = stationOffers(station)
    .filter((offer) => group === "all" || (offer.provider_group || offer.provider) === group);
  if (!offers.length) return priceLabel(station);
  if (group !== "all") {
    return [...new Set(offers.map(priceLabel))].join(" / ");
  }
  return offers
    .map((offer) => `${providerLabel(offer.provider_group || offer.provider)}: ${priceLabel(offer)}`)
    .join(" · ");
}

function comparableOfferPrice(offer) {
  const directKwh = Number(offer?.price_c_per_kwh);
  if (Number.isFinite(directKwh) && directKwh > 0) {
    return { value: directKwh, unit: "kWh", offer };
  }
  const value = Number(offer?.price_value);
  if (!Number.isFinite(value) || value <= 0) return null;
  const unit = String(offer?.price_unit || "").toLowerCase().replaceAll(/[^a-z]/g, "");
  if (unit.includes("kwh")) return { value, unit: "kWh", offer };
  if (unit.includes("min")) return { value, unit: "min", offer };
  return null;
}

function stationComparablePrices(station) {
  return stationOffers(station)
    .filter((offer) => selectedProvider === "all"
      || (offer.provider_group || offer.provider) === selectedProvider)
    .map(comparableOfferPrice)
    .filter(Boolean);
}

function providerPriceRows(station) {
  const offers = stationOffers(station)
    .filter((offer) => selectedProvider === "all" || (offer.provider_group || offer.provider) === selectedProvider);
  return offers.map((offer) => {
    const group = offer.provider_group || offer.provider;
    return `<div class="provider-price-row"><span class="provider-badge ${escapeHtml(group)}">${escapeHtml(providerLabel(group))}</span><strong>${escapeHtml(priceLabel(offer))}</strong></div>`;
  }).join("");
}

function statusLabel(status) {
  const normalized = String(status || "unknown").toLowerCase();
  if (normalized === "available") return t("statusAvailable");
  if (["occupied", "preparing", "suspendedev", "suspendedevse"].includes(normalized)) return t("statusOccupied");
  if (["charging", "finishing"].includes(normalized)) return t("statusCharging");
  if (normalized === "unavailable" || normalized === "faulted") return t("unavailable");
  return t("statusUnknown");
}

function availabilityClass(status) {
  const normalized = String(status || "unknown").toLowerCase();
  if (normalized === "available") return "available";
  if (["occupied", "preparing", "charging", "finishing", "suspendedev", "suspendedevse"].includes(normalized)) return "occupied";
  if (["unavailable", "faulted"].includes(normalized)) return "unavailable";
  return "unknown";
}

function markerColor(station) {
  const availability = stationAvailability(station);
  if (availability === "available") return "#2d8a4b";
  if (["occupied", "unavailable"].includes(availability)) return "#c24f3d";
  const group = selectedProvider === "all" ? providerGroup(station) : selectedProvider;
  if (group === "elektrum") return "#087f8c";
  if (group === "emobi") return "#355f9e";
  if (group === "nap") return "#7b4b94";
  if (group === "ignitis") return "#a52335";
  if (group === "ikrautas") return "#267a42";
  return "#d67b0d";
}

function stationMarkerIcon(station, selected = false) {
  const size = selected ? 18 : 13;
  return L.divIcon({
    html: `<span style="--station-marker-color:${markerColor(station)}"></span>`,
    className: `station-marker${selected ? " selected" : ""}`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function renderPriceLabels() {
  if (!priceLabelLayer) return;
  priceLabelLayer.clearLayers();
  if (map.getZoom() < 13) return;
  const center = map.getCenter();
  const labelBounds = map.getBounds().pad(0.2);
  filteredStations
    .filter((station) => labelBounds.contains([station.latitude, station.longitude]))
    .filter((station) => stationComparablePrices(station).length)
    .map((station) => ({ station, distance: distanceKm(station, center) }))
    .sort((left, right) => left.distance - right.distance)
    .slice(0, MAX_PRICE_LABELS)
    .forEach(({ station }) => {
      L.tooltip({
        permanent: true,
        direction: "right",
        className: "station-price-label",
        offset: [7, 0],
      })
        .setLatLng([station.latitude, station.longitude])
        .setContent(escapeHtml(priceSummary(station)))
        .addTo(priceLabelLayer);
    });
}

function renderMarkers() {
  stationLayer.clearLayers();
  priceLabelLayer.clearLayers();
  markerByKey = new Map();
  const markers = [];
  for (const station of filteredStations) {
    const key = stationKey(station);
    const marker = L.marker([station.latitude, station.longitude], {
      icon: stationMarkerIcon(station, key === selectedStationKey),
      keyboard: true,
      title: station.name,
    });
    const connectorRows = stationConnectors(station)
      .map((connector) => {
        const connectorPrice = priceLabel(connector);
        const connectorStatus = statusLabel(connector.status);
        const statusTime = availabilityClass(connector.status) === "occupied"
          ? ` · ${formatStatusTime(connector)}`
          : "";
        const plugNumber = connectorNumberLabel(connector);
        return `<div class="map-connector"><strong>${escapeHtml([plugNumber, canonicalConnectorType(connector.connector_type)].filter(Boolean).join(" · "))}</strong><span>${escapeHtml(connector.code || "")} · ${escapeHtml(connectorPrice)} · ${escapeHtml(connectorStatus + statusTime)}</span></div>`;
      }).join("");
    marker.bindPopup(`
      <strong>${escapeHtml(station.name)}</strong>
      <span>${escapeHtml(station.address || "")}</span>
      ${stationDescriptions(station)[0] ? `<span>${escapeHtml(stationDescriptions(station)[0])}</span>` : ""}
      <span>${escapeHtml(stationOperator(station))}</span>
      <span>${escapeHtml(priceSummary(station))}</span>
      <div class="map-connector-list">${connectorRows || `<span>${escapeHtml(t("unknown"))}</span>`}</div>
    `, { maxWidth: 360 });
    marker.bindTooltip(
      `<strong>${escapeHtml(station.name)}</strong><span>${escapeHtml(priceSummary(station))}</span>`,
      { direction: "top", opacity: 0.95 },
    );
    marker.on("click", () => selectStation(station, false));
    markers.push(marker);
    markerByKey.set(key, marker);
  }
  if (typeof stationLayer.addLayers === "function") stationLayer.addLayers(markers);
  else for (const marker of markers) marker.addTo(stationLayer);
  renderPriceLabels();
  document.getElementById("map").dataset.stationCount = String(filteredStations.length);
  mapSubtitleEl.textContent = t("mapCount", { count: filteredStations.length });
}

function distanceKm(station, center = listOrigin || map.getCenter()) {
  const latitudeA = Number(center.lat ?? center[0]);
  const longitudeA = Number(center.lng ?? center[1]);
  const latitudeB = Number(station.latitude);
  const longitudeB = Number(station.longitude);
  const toRad = (value) => value * Math.PI / 180;
  const dLat = toRad(latitudeB - latitudeA);
  const dLon = toRad(longitudeB - longitudeA);
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(latitudeA)) * Math.cos(toRad(latitudeB)) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function listedStations(limit = stationListLimit) {
  return [...filteredStations]
    .map((station) => ({ station, distance: distanceKm(station) }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, limit);
}

function renderStationList() {
  if (!map) return;
  const nearest = listedStations();
  listSubtitleEl.textContent = t("listCount", { shown: nearest.length, count: filteredStations.length });
  showAllStationsEl.hidden = nearest.length >= filteredStations.length;
  showAllStationsEl.textContent = t("showMoreStations", {
    remaining: filteredStations.length - nearest.length,
  });
  stationListEl.innerHTML = nearest.map(({ station, distance }) => {
    const price = priceSummary(station);
    const plugs = connectorTypes(station).join(", ");
    const maxPower = stationMaxPower(station);
    return `
    <button class="station-list-item ${stationKey(station) === selectedStationKey ? "selected" : ""}" type="button" data-key="${escapeHtml(stationKey(station))}" data-provider="${escapeHtml(selectedProvider === "all" ? providerGroup(station) : selectedProvider)}">
      <i class="provider-line" aria-hidden="true"></i>
      <span class="station-list-copy">
        <strong>${escapeHtml(station.name)}</strong>
        <span>${escapeHtml(station.address || station.description || "")}</span>
        <span>${escapeHtml(stationOperator(station))} · ${escapeHtml(plugs || t("unknown"))}</span>
      </span>
      <span class="station-list-distance">${formatNumber(distance, distance < 10 ? 1 : 0)} km<br>${maxPower ? `${formatNumber(maxPower, 0)} kW` : ""}<br><strong>${escapeHtml(price)}</strong></span>
    </button>
  `;
  }).join("");
  for (const button of stationListEl.querySelectorAll(".station-list-item")) {
    button.addEventListener("click", () => {
      const station = filteredStations.find((item) => stationKey(item) === button.dataset.key);
      if (station) selectStation(station, true);
    });
  }
}

function updateMetrics() {
  const elektrumCount = stations.filter((item) => providerGroups(item).includes("elektrum")).length;
  const mobillyCount = stations.filter((item) => providerGroups(item).includes("mobilly")).length;
  const emobiCount = stations.filter((item) => providerGroups(item).includes("emobi")).length;
  const napCount = stations.filter((item) => providerGroups(item).includes("nap")).length;
  const ignitisCount = stations.filter((item) => providerGroups(item).includes("ignitis")).length;
  const ikrautasCount = stations.filter((item) => providerGroups(item).includes("ikrautas")).length;
  const items = [
    [t("total"), stations.length, null],
    [t("sourceRecords"), sourceStationCount, null],
    [t("elektrum"), elektrumCount, sourceCounts.elektrum],
    [t("mobilly"), mobillyCount, sourceCounts.mobilly],
    [t("emobi"), emobiCount, sourceCounts.emobi],
    [t("nap"), napCount, sourceCounts.latvia_nap],
    [t("ignitis"), ignitisCount, sourceCounts.ignitis],
    [t("ikrautas"), ikrautasCount, sourceCounts.ikrautas],
    [t("visible"), filteredStations.length, null],
  ];
  metricsEl.innerHTML = items.map(([label, value, source]) => `
    <div class="metric"><span>${escapeHtml(label)}</span><strong>${formatNumber(value, 0)}</strong>${source !== null && source !== undefined && Number.isFinite(Number(source)) ? `<small>${escapeHtml(t("sourceCount", { count: formatNumber(source, 0) }))}</small>` : ""}</div>
  `).join("");
}

function applyFilters({ prefetch = true } = {}) {
  const query = searchEl.value.trim().toLocaleLowerCase(language === "lv" ? "lv-LV" : "en-GB");
  const minimumPower = Number(powerFilterEl.value || 0);
  const availableOnly = availableOnlyEl.checked;
  filteredStations = stations.filter((station) => {
    if (selectedProvider !== "all" && !providerGroups(station).includes(selectedProvider)) return false;
    const operators = stationOperators(station);
    if (operators.length && operators.every((operator) => disabledOperators.has(operator))) return false;
    const plugs = connectorTypes(station);
    if (plugs.length && plugs.every((plug) => disabledConnectorTypes.has(plug))) return false;
    if (minimumPower > 0 && Number(stationMaxPower(station) || 0) < minimumPower) return false;
    if (availableOnly && stationAvailability(station) !== "available") return false;
    if (!query) return true;
    return [
      station.name,
      station.address,
      station.city,
      ...stationDescriptions(station),
      ...stationOperators(station, "all"),
      ...providerGroups(station).map(providerLabel),
    ]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase(language === "lv" ? "lv-LV" : "en-GB")
      .includes(query);
  });
  renderMarkers();
  renderStationList();
  updateMetrics();
  if (prefetch) {
    detailPrefetchGeneration += 1;
    scheduleDetailPrefetch();
  }
}

function stationByKey(key) {
  return stations.find((item) => stationKey(item) === key);
}

function updateStationData(detail) {
  const key = stationKey(detail);
  const index = stations.findIndex((item) => stationKey(item) === key);
  if (index >= 0) stations[index] = { ...stations[index], ...detail };
  if (selectedStationKey === key) selectedStation = stations[index] || detail;
}

function offerWithDetail(offer, detail) {
  const result = { ...offer };
  for (const key of [
    "price_c_per_kwh", "price_value", "price_unit", "price_formatted",
    "price_source", "availability", "available_connectors", "occupied_connectors",
    "live_data_available", "connector_live_data_available", "description", "descriptions",
    "connectors", "connector_count", "max_power_kw", "status_source", "detail_source",
  ]) {
    if (detail?.[key] !== undefined && detail?.[key] !== null) result[key] = detail[key];
  }
  return result;
}

function detailQuality(detail) {
  return (detail?.connector_live_data_available ? 8 : 0)
    + (detail?.live_data_available ? 4 : 0)
    + ((detail?.price_value != null || detail?.price_c_per_kwh != null) ? 2 : 0)
    + (Array.isArray(detail?.connectors) && detail.connectors.length ? 1 : 0);
}

async function loadStationDetail(station) {
  const key = stationKey(station);
  const cached = detailsCache.get(key);
  if (cached && Date.now() - cached.loadedAt < DETAIL_CACHE_MS) return cached.detail;
  const pending = detailRequests.get(key);
  if (pending) return pending;
  const request = loadStationDetailUncached(station);
  detailRequests.set(key, request);
  try {
    return await request;
  } finally {
    detailRequests.delete(key);
  }
}

async function loadStationDetailUncached(station) {
  const key = stationKey(station);
  const offers = stationOffers(station);
  const results = await Promise.allSettled(offers.map((offer) => (
    LIVE_DETAIL_PROVIDERS.has(String(offer.provider || ""))
      ? haApi(`zoe_new_extended/stations/${encodeURIComponent(offer.provider)}/${encodeURIComponent(offer.id)}`)
      : Promise.resolve(offer)
  )));
  const liveResults = results.filter((_, index) => (
    LIVE_DETAIL_PROVIDERS.has(String(offers[index]?.provider || ""))
  ));
  if (liveResults.length && !liveResults.some((result) => result.status === "fulfilled")) {
    throw new Error("All live station detail requests failed");
  }
  const enrichedOffers = offers.map((offer, index) => (
    results[index].status === "fulfilled" ? offerWithDetail(offer, results[index].value) : offer
  ));
  const details = results
    .map((result, index) => ({ result, offer: offers[index] }))
    .filter(({ result, offer }) => result.status === "fulfilled"
      && (selectedProvider === "all"
        || (offer.provider_group || offer.provider) === selectedProvider))
    .map(({ result }) => result.value);
  const best = [...details].sort((left, right) => detailQuality(right) - detailQuality(left))[0];
  const detail = {
    ...station,
    ...(best || {}),
    provider: station.provider,
    provider_group: station.provider_group,
    id: station.id,
    provider_offers: enrichedOffers,
    provider_groups: [...new Set(enrichedOffers.map((offer) => offer.provider_group || offer.provider))],
  };
  detailsCache.set(key, { detail, loadedAt: Date.now() });
  updateStationData(detail);
  return detail;
}

async function loadStationDetailWithRetry(station) {
  try {
    return await loadStationDetail(station);
  } catch (_error) {
    await new Promise((resolve) => window.setTimeout(
      resolve,
      DETAIL_REQUEST_RETRY_DELAY_MS,
    ));
    return loadStationDetail(station);
  }
}

function offerNeedsLiveDetail(offer) {
  if (!LIVE_DETAIL_PROVIDERS.has(String(offer?.provider || ""))) return false;
  const group = offer.provider_group || offer.provider;
  if (selectedProvider !== "all" && selectedProvider !== group) return false;
  const hasPrice = offer.price_value !== null && offer.price_value !== undefined
    || offer.price_c_per_kwh !== null && offer.price_c_per_kwh !== undefined;
  const connectors = Array.isArray(offer.connectors) ? offer.connectors : [];
  const hasConnectorStatus = connectors.some((connector) => (
    availabilityClass(connector.status) !== "unknown"
  ));
  return !hasPrice || !hasConnectorStatus;
}

function prefetchCandidates() {
  if (!map || selectedProvider === "plugshare") return [];
  const now = Date.now();
  return listedStations(DETAIL_PREFETCH_SCOPE_LIMIT)
    .map(({ station }) => station)
    .filter((station) => {
      const cached = detailsCache.get(stationKey(station));
      if (cached && now - cached.loadedAt < DETAIL_CACHE_MS) return false;
      const failedAt = detailPrefetchFailures.get(stationKey(station));
      if (failedAt && now - failedAt < DETAIL_RETRY_MS) return false;
      if (!stationOffers(station).some(offerNeedsLiveDetail)) return false;
      return true;
    })
    .slice(0, DETAIL_PREFETCH_BATCH_SIZE);
}

function scheduleDetailPrefetch(delay = DETAIL_PREFETCH_DELAY_MS) {
  window.clearTimeout(detailPrefetchTimer);
  detailPrefetchTimer = window.setTimeout(runDetailPrefetch, delay);
}

async function loadFirstFilteredStationDetail() {
  const station = listedStations(1)[0]?.station;
  if (!station || !stationOffers(station).some(offerNeedsLiveDetail)) return;
  try {
    await loadStationDetailWithRetry(station);
    renderStationList();
    renderPriceLabels();
  } catch (error) {
    console.debug("Priority station detail failed", stationKey(station), error);
  }
}

async function runDetailPrefetch() {
  if (detailPrefetchRunning) {
    detailPrefetchQueued = true;
    return;
  }
  const candidates = prefetchCandidates();
  if (!candidates.length) return;
  detailPrefetchRunning = true;
  const generation = detailPrefetchGeneration;
  let nextIndex = 0;
  const worker = async () => {
    while (
      nextIndex < candidates.length
      && generation === detailPrefetchGeneration
    ) {
      const station = candidates[nextIndex];
      nextIndex += 1;
      try {
        await loadStationDetailWithRetry(station);
        detailPrefetchFailures.delete(stationKey(station));
        renderStationList();
        if (selectedStationKey === stationKey(station)) {
          const current = stationByKey(selectedStationKey);
          if (current) renderDetail(current);
        }
      } catch (error) {
        detailPrefetchFailures.set(stationKey(station), Date.now());
        console.debug("Station price prefetch failed", stationKey(station), error);
      }
    }
  };
  try {
    await Promise.all(
      Array.from(
        { length: Math.min(DETAIL_PREFETCH_CONCURRENCY, candidates.length) },
        worker,
      ),
    );
    renderStationList();
    renderPriceLabels();
    if (selectedStationKey) {
      const current = stationByKey(selectedStationKey);
      if (current) renderDetail(current);
    }
  } finally {
    detailPrefetchRunning = false;
    if (detailPrefetchQueued) {
      detailPrefetchQueued = false;
      scheduleDetailPrefetch();
    } else if (prefetchCandidates().length) {
      scheduleDetailPrefetch(DETAIL_PREFETCH_NEXT_BATCH_DELAY_MS);
    } else {
      renderMarkers();
    }
  }
}

function renderDetail(station, { loading = false, error = false } = {}) {
  const connectors = stationConnectors(station);
  const currentAvailability = stationAvailability(station);
  const availability = availabilityClass(currentAvailability);
  const maxPower = stationMaxPower(station);
  const address = [station.address, station.city].filter(Boolean).join(", ");
  const destination = `${station.latitude},${station.longitude}`;
  const mapsUrl = `https://www.google.com/maps/dir/?api=1&travelmode=driving&dir_action=navigate&destination=${encodeURIComponent(destination)}`;
  const wazeUrl = `https://www.waze.com/ul?ll=${encodeURIComponent(destination)}&navigate=yes&zoom=17`;
  const locationUrl = `https://www.google.com/maps?q=${encodeURIComponent(`${station.latitude},${station.longitude}`)}`;
  const shareText = t("stationShare", { name: station.name, address, url: locationUrl });
  const whatsappUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`;
  const price = priceSummary(station);
  const descriptions = stationDescriptions(station);
  const visibleGroups = providerGroups(station)
    .filter((group) => selectedProvider === "all" || group === selectedProvider);
  stationDetailEl.innerHTML = `
    <div class="station-heading">
      <div>
        <h2>${escapeHtml(station.name)}</h2>
        <p>${escapeHtml(address)}</p>
      </div>
      <span class="provider-badges">${visibleGroups.map((group) => `<span class="provider-badge ${escapeHtml(group)}">${escapeHtml(providerLabel(group))}</span>`).join("")}</span>
    </div>
    <div class="station-facts">
      <div class="station-fact"><span>${escapeHtml(t("availability"))}</span><strong><span class="status-badge ${availability}">${escapeHtml(statusLabel(currentAvailability))}</span></strong></div>
      <div class="station-fact"><span>${escapeHtml(t("power"))}</span><strong>${maxPower ? `${formatNumber(maxPower, 1)} kW` : "-"}</strong></div>
      <div class="station-fact"><span>${escapeHtml(t("price"))}</span><strong>${escapeHtml(price)}</strong></div>
      <div class="station-fact"><span>${escapeHtml(t("operator"))}</span><strong>${escapeHtml(stationOperator(station))}</strong></div>
    </div>
    ${descriptions.length ? `
      <div class="station-description">
        <strong>${escapeHtml(t("description"))}</strong>
        ${descriptions.map((description) => `<p>${escapeHtml(description)}</p>`).join("")}
      </div>
    ` : ""}
    <div class="provider-price-list">${providerPriceRows(station)}</div>
    <div class="connector-list">
      ${connectors.length ? connectors.map((connector) => `
        <div class="connector-row">
          <span class="connector-name"><strong>${escapeHtml([connectorNumberLabel(connector), canonicalConnectorType(connector.connector_type || connector.type)].filter(Boolean).join(" · "))}</strong><small>${escapeHtml(connector.code || "-")}</small></span>
          <span>${connector.power_kw ? `${formatNumber(connector.power_kw, 1)} kW` : "-"}</span>
          <span class="connector-price">${escapeHtml(priceLabel(connector))}</span>
          <span class="connector-status"><strong class="status-badge ${availabilityClass(connector.status)}">${escapeHtml(statusLabel(connector.status))}</strong><small>${escapeHtml(availabilityClass(connector.status) === "occupied" ? formatStatusTime(connector) : "")}</small></span>
        </div>
      `).join("") : `<div class="connector-row"><strong>${escapeHtml(t("connectors"))}</strong><span>-</span><span>-</span><span class="connector-status">${escapeHtml(t("unknown"))}</span></div>`}
    </div>
    <div class="station-actions">
      <a class="station-action" href="${escapeHtml(mapsUrl)}" data-external-url="${escapeHtml(mapsUrl)}" target="_blank" rel="noopener noreferrer">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2"/></svg>
        ${escapeHtml(t("googleDirections"))}
      </a>
      <a class="station-action waze" href="${escapeHtml(wazeUrl)}" data-external-url="${escapeHtml(wazeUrl)}" target="_blank" rel="noopener noreferrer">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 15a8 8 0 1 1 3 3l-3 2v-5Z"/><circle cx="10" cy="11" r=".5"/><circle cx="15" cy="11" r=".5"/><path d="M10 15c1.5 1 3.5 1 5 0"/></svg>
        ${escapeHtml(t("wazeDirections"))}
      </a>
      <a class="station-action whatsapp" href="${escapeHtml(whatsappUrl)}" data-external-url="${escapeHtml(whatsappUrl)}" target="_blank" rel="noopener noreferrer">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11.5a8 8 0 0 1-11.8 7L4 20l1.5-4A8 8 0 1 1 20 11.5Z"/><path d="M8.5 8.5c1 3 2 4 5 5"/></svg>
        ${escapeHtml(t("whatsapp"))}
      </a>
    </div>
    ${loading ? `<p class="live-note">${escapeHtml(t("detailLoading"))}</p>` : ""}
    ${error ? `<p class="live-note">${escapeHtml(t("liveError"))}</p>` : ""}
    ${!station.live_data_available && station.provider === "mobilly" ? `<p class="live-note">${escapeHtml(t("liveUnavailable"))}</p>` : ""}
  `;
}

async function selectStation(station, moveMap = false) {
  const previousStationKey = selectedStationKey;
  selectedStationKey = stationKey(station);
  selectedStation = station;
  for (const key of new Set([previousStationKey, selectedStationKey])) {
    const marker = markerByKey.get(key);
    const item = stationByKey(key);
    if (marker && item) marker.setIcon(stationMarkerIcon(item, key === selectedStationKey));
  }
  if (moveMap) {
    const marker = markerByKey.get(selectedStationKey);
    if (marker && typeof stationLayer.zoomToShowLayer === "function") {
      stationLayer.zoomToShowLayer(marker, () => marker.openPopup());
    } else {
      map.flyTo([station.latitude, station.longitude], Math.max(map.getZoom(), 15), { duration: 0.45 });
      marker?.openPopup();
    }
  }
  renderDetail(station, { loading: station.provider === "elektrum" });
  renderStationList();

  const cached = detailsCache.get(selectedStationKey);
  if (cached && Date.now() - cached.loadedAt < DETAIL_CACHE_MS) {
    updateStationData(cached.detail);
    renderDetail(selectedStation);
    applyFilters();
    return;
  }
  try {
    await loadStationDetailWithRetry(station);
    renderDetail(selectedStation);
    applyFilters();
  } catch (error) {
    console.error("Station detail failed", error);
    renderDetail(station, { error: true });
  }
}

function showVehicleLocation() {
  if (!vehicleLocation) {
    statusEl.classList.add("warn");
    statusEl.textContent = t("noLocation");
    return;
  }
  listOrigin = { lat: vehicleLocation.latitude, lng: vehicleLocation.longitude };
  map.flyTo([vehicleLocation.latitude, vehicleLocation.longitude], 13, { duration: 0.55 });
  renderStationList();
}

function browserLocation() {
  if (!navigator.geolocation) return Promise.resolve(null);
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: 7000, maximumAge: 60000 },
    );
  });
}

async function resolveSearchOrigin() {
  return vehicleLocation
    ? { lat: vehicleLocation.latitude, lng: vehicleLocation.longitude }
    : await browserLocation() || map.getCenter();
}

async function showNearestStations() {
  nearestEl.disabled = true;
  statusEl.classList.remove("warn");
  statusEl.textContent = t("locating");
  try {
    listOrigin = await resolveSearchOrigin();
    applyFilters();
    if (!filteredStations.length) {
      statusEl.classList.add("warn");
      statusEl.textContent = t("noMatchingStations");
      return;
    }
    const nearest = [...filteredStations]
      .map((station) => ({ station, distance: distanceKm(station, listOrigin) }))
      .sort((left, right) => left.distance - right.distance);
    const visible = nearest.slice(0, Math.min(8, nearest.length));
    const bounds = L.latLngBounds([
      [listOrigin.lat, listOrigin.lng],
      ...visible.map(({ station }) => [station.latitude, station.longitude]),
    ]);
    map.fitBounds(bounds, { padding: [34, 34], maxZoom: 13 });
    statusEl.textContent = t("nearestFound", {
      count: filteredStations.length,
      distance: formatNumber(nearest[0].distance, nearest[0].distance < 10 ? 1 : 0),
    });
    renderStationList();
  } finally {
    nearestEl.disabled = false;
  }
}

async function showCheapestStation() {
  const maxDistance = Number(cheapestDistanceEl.value);
  if (!Number.isFinite(maxDistance) || maxDistance < 1 || maxDistance > 500) {
    statusEl.classList.add("warn");
    statusEl.textContent = t("invalidDistance");
    return;
  }
  storeNumber(CHEAPEST_DISTANCE_STORAGE, maxDistance);
  cheapestEl.disabled = true;
  cheapestDistanceEl.disabled = true;
  statusEl.classList.remove("warn");
  statusEl.textContent = t("findingCheapest");
  try {
    listOrigin = await resolveSearchOrigin();
    applyFilters();
    const nearby = filteredStations
      .map((station) => ({ station, distance: distanceKm(station, listOrigin) }))
      .filter(({ distance }) => Number.isFinite(distance) && distance <= maxDistance);
    if (!nearby.length) {
      statusEl.classList.add("warn");
      statusEl.textContent = t("noStationsInRange");
      return;
    }
    const priced = nearby.flatMap(({ station, distance }) => (
      stationComparablePrices(station).map((price) => ({ station, distance, ...price }))
    ));
    const comparable = priced.some((item) => item.unit === "kWh")
      ? priced.filter((item) => item.unit === "kWh")
      : priced.filter((item) => item.unit === "min");
    if (!comparable.length) {
      statusEl.classList.add("warn");
      statusEl.textContent = t("noPricedStations");
      return;
    }
    comparable.sort((left, right) => left.value - right.value || left.distance - right.distance);
    const winner = comparable[0];
    await selectStation(winner.station, true);
    statusEl.textContent = t("cheapestFound", {
      price: priceLabel(winner.offer),
      distance: formatNumber(winner.distance, winner.distance < 10 ? 1 : 0),
    });
    stationDetailEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } finally {
    cheapestEl.disabled = false;
    cheapestDistanceEl.disabled = false;
  }
}

function openExternalUrl(url) {
  try {
    const targetDocument = window.top?.document;
    if (targetDocument?.body) {
      const link = targetDocument.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.hidden = true;
      targetDocument.body.appendChild(link);
      link.click();
      link.remove();
      return;
    }
  } catch (_error) {
    // Fall back to the current browsing context when top-level access is restricted.
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

function renderVehicleLocation() {
  if (vehicleMarker) {
    map.removeLayer(vehicleMarker);
    vehicleMarker = null;
  }
  if (!vehicleLocation) return;
  vehicleMarker = L.marker([vehicleLocation.latitude, vehicleLocation.longitude], {
    title: "Renault ZOE",
    zIndexOffset: 1000,
  }).addTo(map).bindTooltip("Renault ZOE", { permanent: false, direction: "top" });
}

async function loadStations({ clearDetails = false } = {}) {
  window.clearTimeout(loadRetryTimer);
  loadRetryTimer = null;
  if (clearDetails) {
    detailsCache.clear();
    detailPrefetchFailures.clear();
  }
  reloadEl.disabled = true;
  statusEl.classList.remove("warn");
  statusEl.textContent = t("loading");
  try {
    const hass = await getParentHass();
    language = hass?.states?.[SETTINGS_ENTITY]?.attributes?.dashboard_language === "en" ? "en" : "lv";
    applyLanguage();
    const payload = await haApi("zoe_new_extended/stations");
    if (!payload || typeof payload !== "object") {
      throw new Error("Station API returned an invalid response");
    }
    loadRetryAttempt = 0;
    stations = Array.isArray(payload.stations) ? payload.stations : [];
    sourceStationCount = Number(payload.source_station_count || stations.length);
    sourceCounts = payload.source_counts && typeof payload.source_counts === "object"
      ? payload.source_counts
      : {};
    vehicleLocation = payload.vehicle_location || null;
    if (selectedProvider === "plugshare") updatePlugShareMap();
    renderFilterMenus();
    ensureMap();
    renderVehicleLocation();
    if (vehicleLocation) map.setView([vehicleLocation.latitude, vehicleLocation.longitude], 11);
    if (selectedProvider !== "plugshare") applyFilters();
    const errors = Object.entries(payload.errors || {}).map(([provider, message]) => `${provider}: ${message}`);
    if (errors.length) {
      statusEl.classList.add("warn");
      statusEl.textContent = t("partial", { errors: errors.join("; ") });
    } else {
      statusEl.textContent = t("loaded", {
        count: stations.length,
        sourceCount: sourceStationCount,
      });
    }
  } catch (error) {
    const errorText = formatError(error);
    if (/\b(?:404|503)\b/.test(errorText) && loadRetryAttempt < LOAD_RETRY_LIMIT) {
      loadRetryAttempt += 1;
      statusEl.textContent = `${t("loading")} (${loadRetryAttempt}/${LOAD_RETRY_LIMIT})`;
      loadRetryTimer = window.setTimeout(loadStations, LOAD_RETRY_DELAY_MS);
      return;
    }
    statusEl.classList.add("warn");
    statusEl.textContent = t("loadFailed", { error: errorText });
  } finally {
    reloadEl.disabled = false;
    window.setTimeout(() => map?.invalidateSize(), 150);
  }
}

function activateProviderTab(tab) {
  const provider = tab.dataset.provider;
  if (!provider) return;
  if (selectedProvider === provider && tab.classList.contains("active")) return;
  selectedProvider = provider;
  for (const item of document.querySelectorAll(".provider-tab")) {
    const active = item === tab;
    item.classList.toggle("active", active);
    item.setAttribute("aria-selected", String(active));
  }
  showProviderView(selectedProvider);
}

for (const tab of document.querySelectorAll(".provider-tab")) {
  tab.addEventListener("pointerdown", () => activateProviderTab(tab));
  tab.addEventListener("click", () => activateProviderTab(tab));
  tab.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") activateProviderTab(tab);
  });
}

searchEl.addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => {
    resetStationListLimit();
    applyFilters();
    if (searchEl.value.trim()) {
      fitMapToStations(filteredStations);
      loadFirstFilteredStationDetail();
    }
  }, 220);
});
powerFilterEl.addEventListener("change", applyFilters);
availableOnlyEl.addEventListener("change", applyFilters);
reloadEl.addEventListener("click", () => loadStations({ clearDetails: true }));
showAllStationsEl.addEventListener("click", () => {
  stationListLimit = Math.min(
    filteredStations.length,
    stationListLimit + FILTERED_LIST_PAGE_SIZE,
  );
  renderStationList();
  scheduleDetailPrefetch();
});
document.getElementById("locate").addEventListener("click", showVehicleLocation);
nearestEl.addEventListener("click", showNearestStations);
cheapestEl.addEventListener("click", showCheapestStation);
cheapestDistanceEl.value = String(Math.min(
  500,
  Math.max(1, readStoredNumber(CHEAPEST_DISTANCE_STORAGE, DEFAULT_CHEAPEST_DISTANCE_KM)),
));
cheapestDistanceEl.addEventListener("change", () => {
  const value = Number(cheapestDistanceEl.value);
  if (Number.isFinite(value) && value >= 1 && value <= 500) {
    storeNumber(CHEAPEST_DISTANCE_STORAGE, value);
  }
});
stationDetailEl.addEventListener("click", (event) => {
  const link = event.target.closest("[data-external-url]");
  if (!link) return;
  event.preventDefault();
  openExternalUrl(link.dataset.externalUrl);
});
document.getElementById("enableAllConnectors").addEventListener("click", () => {
  disabledConnectorTypes.clear();
  storeSet(CONNECTOR_FILTER_STORAGE, disabledConnectorTypes);
  renderFilterMenus();
  applyFilters();
});
document.getElementById("enableAllOperators").addEventListener("click", () => {
  disabledOperators.clear();
  storeSet(OPERATOR_FILTER_STORAGE, disabledOperators);
  renderFilterMenus();
  applyFilters();
});
document.addEventListener("click", (event) => {
  for (const menu of document.querySelectorAll(".multi-filter[open]")) {
    if (!menu.contains(event.target)) menu.removeAttribute("open");
  }
});
window.addEventListener("resize", () => map?.invalidateSize());

searchEl.value = "";
applyLanguage();
ensureMap();
loadStations();
