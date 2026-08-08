"use strict";

const SETTINGS_ENTITY = "sensor.renault_zoe_new_cost_settings";
const DEFAULT_CENTER = [56.9496, 24.1052];
const DEFAULT_ZOOM = 10;
const LIST_LIMIT = 40;
const DETAIL_CACHE_MS = 30 * 60 * 1000;
const CONNECTOR_FILTER_STORAGE = "zoe-stations-disabled-connectors";
const OPERATOR_FILTER_STORAGE = "zoe-stations-disabled-operators";

const I18N = {
  lv: {
    plugFilters: "Spraudņi",
    operatorFilters: "Operatori",
    enableAll: "Ieslēgt visus",
    filterCount: "{enabled}/{total}",
    findNearest: "Tuvākās",
    locating: "Meklēju tuvākās atbilstošās stacijas...",
    nearestFound: "Atrastas {count} atbilstošas stacijas; tuvākā ir {distance} km.",
    noMatchingStations: "Nav staciju ar izvēlētajiem spraudņiem un operatoriem.",
    googleDirections: "Google Maps",
    wazeDirections: "Waze",
    occupiedSince: "Aizņemts kopš",
    observedSince: "Novērots kopš {time}",
    timeUnavailable: "Laiks nav pieejams",
    priceLoading: "Ielādēju cenu",
    operator: "Operators",
    plugNumber: "Spraudnis {number}",
    title: "Uzlādes stacijas",
    subtitle: "Elektrum Drive, Mobilly, e-mobi un PlugShare",
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
    visible: "Redzamas",
    loaded: "Ielādētas {count} stacijas. Elektrum dzīvie dati tiek nolasīti pēc stacijas izvēles.",
    partial: "Daļa datu nav pieejama: {errors}",
    loadFailed: "Neizdevās ielādēt stacijas: {error}",
    mapCount: "Kartē {count} stacijas",
    listCount: "Parādītas {shown} no {count}",
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
    locating: "Finding the nearest matching stations...",
    nearestFound: "Found {count} matching stations; the nearest is {distance} km away.",
    noMatchingStations: "No stations match the selected plugs and operators.",
    googleDirections: "Google Maps",
    wazeDirections: "Waze",
    occupiedSince: "Occupied since",
    observedSince: "Observed since {time}",
    timeUnavailable: "Time unavailable",
    priceLoading: "Loading price",
    operator: "Operator",
    plugNumber: "Plug {number}",
    title: "Charging stations",
    subtitle: "Elektrum Drive, Mobilly, e-mobi, and PlugShare",
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
    visible: "Visible",
    loaded: "Loaded {count} stations. Elektrum live data loads after station selection.",
    partial: "Some data is unavailable: {errors}",
    loadFailed: "Unable to load stations: {error}",
    mapCount: "{count} stations on map",
    listCount: "Showing {shown} of {count}",
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
let vehicleMarker;
let stations = [];
let filteredStations = [];
let vehicleLocation = null;
let selectedProvider = "all";
let selectedStationKey = "";
let selectedStation = null;
let markerByKey = new Map();
let detailsCache = new Map();
let cachedParentHass = null;
let searchTimer = null;
let listOrigin = null;
let disabledConnectorTypes = readStoredSet(CONNECTOR_FILTER_STORAGE);
let disabledOperators = readStoredSet(OPERATOR_FILTER_STORAGE);

const statusEl = document.getElementById("status");
const metricsEl = document.getElementById("metrics");
const mapSubtitleEl = document.getElementById("mapSubtitle");
const listSubtitleEl = document.getElementById("listSubtitle");
const stationListEl = document.getElementById("stationList");
const stationDetailEl = document.getElementById("stationDetail");
const searchEl = document.getElementById("search");
const powerFilterEl = document.getElementById("powerFilter");
const availableOnlyEl = document.getElementById("availableOnly");
const reloadEl = document.getElementById("reload");
const nearestEl = document.getElementById("nearest");
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

function showProviderView(provider) {
  const showPlugShare = provider === "plugshare";
  localStationsViewEl.hidden = showPlugShare;
  plugsharePanelEl.hidden = !showPlugShare;
  for (const control of localFilterEls) control.hidden = showPlugShare;
  if (showPlugShare) {
    updatePlugShareMap();
    return;
  }
  applyFilters();
  window.setTimeout(() => map?.invalidateSize(), 0);
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

function connectorTypes(station) {
  const values = (Array.isArray(station.connectors) ? station.connectors : [])
    .map((connector) => canonicalConnectorType(connector.connector_type || connector.type));
  return [...new Set(values)];
}

function stationOperator(station) {
  return String(
    station.operator
      || providerLabel(providerGroup(station)),
  );
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
    price_c_per_kwh: station.price_c_per_kwh,
    price_value: station.price_value,
    price_unit: station.price_unit,
    price_formatted: station.price_formatted,
    availability: station.availability,
    live_data_available: station.live_data_available,
  }];
}

function providerLabel(provider) {
  if (provider === "elektrum" || provider === "emobi_elektrum") return "Elektrum Drive";
  if (provider === "emobi") return "e-mobi";
  return "Mobilly";
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
  const operatorValues = [...new Set(stations.map(stationOperator))]
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

async function haApi(path) {
  const hass = await getParentHass();
  if (!hass?.callApi) throw new Error("Home Assistant connection is unavailable");
  return hass.callApi("GET", path.replace(/^\/api\//, ""));
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
  stationLayer = L.layerGroup().addTo(map);
  map.on("moveend", renderStationList);
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
  if (!Number.isFinite(Number(value))) return t("unknown");
  const unit = item.price_unit || "kWh";
  return `${formatNumber(value, 2)} c/${unit}`;
}

function priceSummary(station, group = selectedProvider) {
  const offers = stationOffers(station)
    .filter((offer) => group === "all" || (offer.provider_group || offer.provider) === group);
  if (!offers.length) return priceLabel(station);
  if (group !== "all") return priceLabel(offers[0]);
  return offers
    .map((offer) => `${providerLabel(offer.provider_group || offer.provider)}: ${priceLabel(offer)}`)
    .join(" · ");
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
  if (station.availability === "available") return "#2d8a4b";
  if (["occupied", "unavailable"].includes(station.availability)) return "#c24f3d";
  if (providerGroup(station) === "elektrum") return "#087f8c";
  if (providerGroup(station) === "emobi") return "#355f9e";
  return "#d67b0d";
}

function renderMarkers() {
  stationLayer.clearLayers();
  markerByKey = new Map();
  for (const station of filteredStations) {
    const marker = L.circleMarker([station.latitude, station.longitude], {
      radius: stationKey(station) === selectedStationKey ? 8 : 5,
      weight: stationKey(station) === selectedStationKey ? 3 : 1,
      color: "#ffffff",
      fillColor: markerColor(station),
      fillOpacity: 0.9,
    });
    const connectorRows = (Array.isArray(station.connectors) ? station.connectors : [])
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
      <span>${escapeHtml(stationOperator(station))}</span>
      <span>${escapeHtml(priceSummary(station))}</span>
      <div class="map-connector-list">${connectorRows || `<span>${escapeHtml(t("unknown"))}</span>`}</div>
    `, { maxWidth: 360 });
    marker.bindTooltip(
      `<strong>${escapeHtml(station.name)}</strong><span>${escapeHtml(station.price_value == null && station.price_c_per_kwh == null ? t("priceLoading") : priceLabel(station))}</span>`,
      { direction: "top", opacity: 0.95 },
    );
    marker.on("click", () => selectStation(station, false));
    marker.addTo(stationLayer);
    markerByKey.set(stationKey(station), marker);
    if (station.price_value != null || station.price_c_per_kwh != null) {
      L.tooltip({
        permanent: true,
        direction: "right",
        className: "station-price-label",
        offset: [7, 0],
      })
        .setLatLng([station.latitude, station.longitude])
        .setContent(escapeHtml(priceLabel(station)))
        .addTo(stationLayer);
    }
  }
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

function renderStationList() {
  if (!map) return;
  const nearest = [...filteredStations]
    .map((station) => ({ station, distance: distanceKm(station) }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, LIST_LIMIT);
  listSubtitleEl.textContent = t("listCount", { shown: nearest.length, count: filteredStations.length });
  stationListEl.innerHTML = nearest.map(({ station, distance }) => {
    const price = priceSummary(station);
    const plugs = connectorTypes(station).join(", ");
    return `
    <button class="station-list-item ${stationKey(station) === selectedStationKey ? "selected" : ""}" type="button" data-key="${escapeHtml(stationKey(station))}" data-provider="${escapeHtml(providerGroup(station))}">
      <i class="provider-line" aria-hidden="true"></i>
      <span class="station-list-copy">
        <strong>${escapeHtml(station.name)}</strong>
        <span>${escapeHtml(station.address || station.description || "")}</span>
        <span>${escapeHtml(stationOperator(station))} · ${escapeHtml(plugs || t("unknown"))}</span>
      </span>
      <span class="station-list-distance">${formatNumber(distance, distance < 10 ? 1 : 0)} km<br>${station.max_power_kw ? `${formatNumber(station.max_power_kw, 0)} kW` : ""}<br><strong>${escapeHtml(price)}</strong></span>
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
  const items = [
    [t("total"), stations.length],
    [t("elektrum"), elektrumCount],
    [t("mobilly"), mobillyCount],
    [t("emobi"), emobiCount],
    [t("visible"), filteredStations.length],
  ];
  metricsEl.innerHTML = items.map(([label, value]) => `
    <div class="metric"><span>${escapeHtml(label)}</span><strong>${formatNumber(value, 0)}</strong></div>
  `).join("");
}

function applyFilters() {
  const query = searchEl.value.trim().toLocaleLowerCase(language === "lv" ? "lv-LV" : "en-GB");
  const minimumPower = Number(powerFilterEl.value || 0);
  const availableOnly = availableOnlyEl.checked;
  filteredStations = stations.filter((station) => {
    if (selectedProvider !== "all" && !providerGroups(station).includes(selectedProvider)) return false;
    if (disabledOperators.has(stationOperator(station))) return false;
    const plugs = connectorTypes(station);
    if (plugs.length && plugs.every((plug) => disabledConnectorTypes.has(plug))) return false;
    if (minimumPower > 0 && Number(station.max_power_kw || 0) < minimumPower) return false;
    if (availableOnly && station.availability !== "available") return false;
    if (!query) return true;
    return [station.name, station.address, station.city, station.description]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase(language === "lv" ? "lv-LV" : "en-GB")
      .includes(query);
  });
  renderMarkers();
  renderStationList();
  updateMetrics();
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
    "live_data_available", "connector_live_data_available",
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
  const offers = stationOffers(station);
  const results = await Promise.allSettled(offers.map((offer) => haApi(
    `zoe_new_extended/stations/${encodeURIComponent(offer.provider)}/${encodeURIComponent(offer.id)}`,
  )));
  const details = results
    .filter((result) => result.status === "fulfilled")
    .map((result) => result.value);
  const enrichedOffers = offers.map((offer, index) => (
    results[index].status === "fulfilled" ? offerWithDetail(offer, results[index].value) : offer
  ));
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

function renderDetail(station, { loading = false, error = false } = {}) {
  const connectors = Array.isArray(station.connectors) ? station.connectors : [];
  const availability = availabilityClass(station.availability);
  const address = [station.address, station.city].filter(Boolean).join(", ");
  const destination = `${station.latitude},${station.longitude}`;
  const mapsUrl = `https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=${encodeURIComponent(destination)}`;
  const wazeUrl = `https://www.waze.com/ul?ll=${encodeURIComponent(destination)}&navigate=yes&zoom=17`;
  const locationUrl = `https://www.google.com/maps?q=${encodeURIComponent(`${station.latitude},${station.longitude}`)}`;
  const shareText = t("stationShare", { name: station.name, address, url: locationUrl });
  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
  const price = priceSummary(station);
  const visibleGroups = providerGroups(station)
    .filter((group) => selectedProvider === "all" || group === selectedProvider);
  stationDetailEl.innerHTML = `
    <div class="station-heading">
      <div>
        <h2>${escapeHtml(station.name)}</h2>
        <p>${escapeHtml(address || station.description || "")}</p>
      </div>
      <span class="provider-badges">${visibleGroups.map((group) => `<span class="provider-badge ${escapeHtml(group)}">${escapeHtml(providerLabel(group))}</span>`).join("")}</span>
    </div>
    <div class="station-facts">
      <div class="station-fact"><span>${escapeHtml(t("availability"))}</span><strong><span class="status-badge ${availability}">${escapeHtml(statusLabel(station.availability))}</span></strong></div>
      <div class="station-fact"><span>${escapeHtml(t("power"))}</span><strong>${station.max_power_kw ? `${formatNumber(station.max_power_kw, 1)} kW` : "-"}</strong></div>
      <div class="station-fact"><span>${escapeHtml(t("price"))}</span><strong>${escapeHtml(price)}</strong></div>
      <div class="station-fact"><span>${escapeHtml(t("operator"))}</span><strong>${escapeHtml(stationOperator(station))}</strong></div>
    </div>
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
      <a class="station-action" href="${escapeHtml(mapsUrl)}" target="_blank" rel="noopener noreferrer">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2"/></svg>
        ${escapeHtml(t("googleDirections"))}
      </a>
      <a class="station-action waze" href="${escapeHtml(wazeUrl)}" target="_blank" rel="noopener noreferrer">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 15a8 8 0 1 1 3 3l-3 2v-5Z"/><circle cx="10" cy="11" r=".5"/><circle cx="15" cy="11" r=".5"/><path d="M10 15c1.5 1 3.5 1 5 0"/></svg>
        ${escapeHtml(t("wazeDirections"))}
      </a>
      <a class="station-action whatsapp" href="${escapeHtml(whatsappUrl)}" target="_blank" rel="noopener noreferrer">
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
  selectedStationKey = stationKey(station);
  selectedStation = station;
  if (moveMap) map.flyTo([station.latitude, station.longitude], Math.max(map.getZoom(), 14), { duration: 0.45 });
  renderDetail(station, { loading: station.provider === "elektrum" });
  renderMarkers();
  renderStationList();

  const cached = detailsCache.get(selectedStationKey);
  if (cached && Date.now() - cached.loadedAt < DETAIL_CACHE_MS) {
    updateStationData(cached.detail);
    renderDetail(selectedStation);
    applyFilters();
    return;
  }
  try {
    await loadStationDetail(station);
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

async function showNearestStations() {
  nearestEl.disabled = true;
  statusEl.classList.remove("warn");
  statusEl.textContent = t("locating");
  try {
    listOrigin = vehicleLocation
      ? { lat: vehicleLocation.latitude, lng: vehicleLocation.longitude }
      : await browserLocation()
        || map.getCenter();
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

async function loadStations() {
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
    stations = Array.isArray(payload.stations) ? payload.stations : [];
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
      statusEl.textContent = t("loaded", { count: stations.length });
    }
  } catch (error) {
    statusEl.classList.add("warn");
    statusEl.textContent = t("loadFailed", { error: formatError(error) });
  } finally {
    reloadEl.disabled = false;
    window.setTimeout(() => map?.invalidateSize(), 150);
  }
}

for (const tab of document.querySelectorAll(".provider-tab")) {
  tab.addEventListener("click", () => {
    selectedProvider = tab.dataset.provider;
    for (const item of document.querySelectorAll(".provider-tab")) {
      const active = item === tab;
      item.classList.toggle("active", active);
      item.setAttribute("aria-selected", String(active));
    }
    showProviderView(selectedProvider);
  });
}

searchEl.addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(applyFilters, 220);
});
powerFilterEl.addEventListener("change", applyFilters);
availableOnlyEl.addEventListener("change", applyFilters);
reloadEl.addEventListener("click", loadStations);
document.getElementById("locate").addEventListener("click", showVehicleLocation);
nearestEl.addEventListener("click", showNearestStations);
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

applyLanguage();
ensureMap();
loadStations();
