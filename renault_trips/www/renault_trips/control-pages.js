"use strict";

const QUERY = new URLSearchParams(window.location.search);
const PAGE = QUERY.get("page") === "immax" ? "immax" : "charging";
const DAY_MS = 86400000;
const REFRESH_CURRENT_MS = 15000;
const REFRESH_HISTORY_MS = 300000;

const I18N = {
  lv: {
    refresh: "Atjaunot",
    settings: "Iestatījumi",
    entitySettings: "IMMAX entītiju avoti",
    clearDate: "Notīrīt datumu",
    periodLabel: "Vēstures periods",
    specificDate: "Konkrēts datums",
    summary: "Kopsavilkums",
    commands: "Komandas",
    historyChart: "Vēstures grafiks",
    detailedHistoryChart: "Detalizētas vēstures grafiks",
    loading: "Ielādēju Home Assistant datus...",
    updated: "Atjaunots {time}. Grafikos var pārvietot peli vai pieskarties, lai redzētu vērtības konkrētā laikā.",
    loadError: "Datus neizdevās ielādēt: {error}",
    unavailable: "Nav pieejams",
    noHistory: "Izvēlētajā periodā vēstures datu nav.",
    lastChanged: "Mainīts {time}",
    chargingTitle: "Renault ZOE uzlāde",
    chargingSubtitle: "Uzlādes vadība, Nord Pool cenas, auto stāvoklis un pilna vēsture.",
    immaxTitle: "IMMAX viedā uzlāde",
    immaxSubtitle: "Lādētāja vadība, saules pārpalikums, jaudas ierobežojumi un pilna vēsture.",
    actions: "Komandas",
    startCharge: "Sākt uzlādi",
    stopCharge: "Apturēt uzlādi",
    startClimate: "Ieslēgt klimatu",
    smartCharging: "Viedā uzlāde",
    planAndTarget: "Plāns un mērķis",
    locationAndStatus: "Lokācija un statuss",
    chargerControl: "Lādētāja vadība",
    localControls: "Tuya Local vadība",
    limitsAndTarget: "Limiti un mērķis",
    activeMode: "Aktīvā režīma iestatījumi",
    measurements: "Mērījumi",
    deviceDetails: "Ierīces informācija",
    priceAndPower: "Nord Pool cena un ZOE uzlādes jauda",
    priceAndPowerNote: "Cena c/kWh, jauda kW",
    batteryHistory: "Baterijas un uzlādes vēsture",
    batteryHistoryNote: "SOC % un uzlādes jauda kW",
    immaxPower: "IMMAX, saules un kopējās slodzes vēsture",
    immaxPowerNote: "Jauda kW, baterijas SOC %",
    immaxNordpool: "Nord Pool cenas un cenas iestatījums",
    immaxNordpoolNote: "Nord Pool cena un maksimālās cenas setpoints, c/kWh",
    phaseHistory: "Fāžu strāvas un sprieguma vēsture",
    phaseHistoryNote: "Strāva A, spriegums V",
    chargeSessions: "Renault API uzlādes sesijas",
    chargeSessionsNote: "Tekošā mēneša pabeigtās sesijas",
    entityHistory: "IMMAX datu svaigums",
    entityHistoryNote: "Klikšķini uz vērtības, lai atvērtu HA vēsturi.",
    battery: "Baterija",
    range: "Atlikums",
    mileage: "Nobraukums",
    chargeState: "Uzlādes stāvoklis",
    plugState: "Spraudnis",
    chargingMode: "Uzlādes režīms",
    currentPrice: "Pašreizējā cena",
    location: "Atrašanās vieta",
    elektrumStation: "Elektrum Drive stacija",
    effectivePrice: "Faktiskā uzlādes cena",
    notDetected: "Nav noteikta",
    chargerStatus: "Lādētāja statuss",
    chargerOnline: "Lādētājs tiešsaistē",
    chargerProblem: "Lādētāja kļūda",
    chargingPower: "Uzlādes jauda",
    totalPower: "Kopējā lādētāja jauda",
    totalLoad: "Kopējā AC slodze",
    currentLimit: "Strāvas limits",
    chargerEnergy: "Lādētāja enerģija",
    sessionEnergy: "Šīs uzlādes enerģija",
    chargerTemperature: "Lādētāja temperatūra",
    siteBatterySoc: "Mājas baterijas SOC",
    smartMode: "Viedais režīms",
    detectedPhases: "Noteiktās fāzes",
    smartEnabled: "Ieslēgt viedo uzlādi",
    usePriceCap: "Lietot maksimālo cenu",
    maxPrice: "Maksimālā cena ar PVN",
    targetMode: "Mērķa režīms",
    targetSoc: "Mērķa SOC",
    targetRange: "Mērķa atlikums",
    readyBy: "Gatavs līdz",
    smartStatus: "Viedās uzlādes statuss",
    plannedCharging: "Plānotā uzlāde",
    expectedLevel: "Sagaidāmais uzlādes līmenis",
    estimatedCost: "Prognozētās izmaksas",
    actualCost: "Faktiskās izmaksas",
    remainingTime: "Atlikušais uzlādes laiks",
    calculatedPower: "Aprēķinātā uzlādes jauda",
    estimatedFullAt: "100% būs ap",
    notChargingNow: "Netiek lādēts",
    notScheduled: "Nav ieplānots",
    locationControl: "Viedā uzlāde šajā lokācijā",
    anyLocation: "Atļaut jebkurā lokācijā",
    locationMatches: "Pašreizējā lokācija atbilst",
    apiUpdated: "Renault API atjaunots",
    delayPeriod: "Atlikšanas periods",
    totalPowerLimit: "Kopējās AC jaudas limits",
    socStop: "Apturēt pie baterijas SOC",
    socResume: "Atsākt pie baterijas SOC",
    externalSocTarget: "Lietot ārējo EV SOC mērķi",
    energyToAdd: "Pievienojamā enerģija",
    chargeTarget: "EV uzlādes mērķis",
    nordpoolCurrent: "Nord Pool uzlādes strāva",
    planningPower: "Plānošanas jauda",
    phaseMode: "Fāžu režīms",
    reservePower: "Rezerve (+) / baterijas atbalsts (-)",
    minSolarPower: "Minimālā uzlādes jauda",
    maxSolarPower: "Maksimālā uzlādes jauda",
    solarProduction: "Saules ražošana",
    availableSolar: "Pieejamais saules pārpalikums",
    targetPower: "Mērķa uzlādes jauda",
    gridExport: "Nodošana tīklā",
    batteryCharging: "Baterijas uzlāde",
    batteryDischarging: "Baterijas izlāde",
    aiAdvisor: "AI padomdevējs",
    aiAdvice: "AI ieteikums",
    phaseA: "Fāze A",
    phaseB: "Fāze B",
    phaseC: "Fāze C",
    phaseAVoltage: "Fāze A spriegums",
    phaseACurrent: "Fāze A strāva",
    phaseBVoltage: "Fāze B spriegums",
    phaseBCurrent: "Fāze B strāva",
    phaseCVoltage: "Fāze C spriegums",
    phaseCCurrent: "Fāze C strāva",
    phaseAPower: "Fāze A jauda",
    phaseBPower: "Fāze B jauda",
    phaseCPower: "Fāze C jauda",
    workMode: "Darba režīms",
    delayTimer: "Atlikšanas taimeris",
    requireEarth: "Pieprasīt zemējumu",
    onlineControl: "Lādētāja online slēdzis",
    chargeNow: "Sākt tūlīt",
    pause12h: "Atlikt uz 12 stundām",
    restartCharger: "Pārstartēt lādētāju",
    disableEarth: "Atslēgt zemējuma kontroli",
    disableEarthConfirm: "Vai tiešām atslēgt lādētāja zemējuma kontroli?",
    deviceVersion: "Sistēmas versija",
    deviceInfo: "Aparatūras informācija",
    realtimeData: "Tuya Local reāllaika dati",
    supportedCurrent: "Atbalstītās strāvas",
    faultCode: "Kļūdas kods",
    analysisInterval: "Analīzes intervāls",
    aiCurrentCap: "AI strāvas limits",
    voltage: "spriegums",
    current: "strāva",
    power: "jauda",
    startEnd: "Sākums / beigas",
    station: "Stacija",
    connector: "Konektors",
    homeNordPool: "Mājas / Nord Pool",
    elektrumDrive: "Elektrum Drive",
    elektrumDriveApp: "Elektrum Drive",
    mobilly: "Mobilly",
    ignitisOnApp: "Ignitis ON",
    ikrautasApp: "IKRAUTAS",
    operatorExact: "operatora dati",
    calculatedFallback: "aprēķināts, operatora dati nav pieejami",
    duration: "Ilgums",
    batteryEnergy: "Baterijas enerģija",
    gridEnergy: "Tīkla enerģija",
    priceDelivery: "Cena ar pārvadi",
    cost: "Izmaksas",
    status: "Statuss",
    total: "Kopā",
    noSessions: "Šajā mēnesī pabeigtu uzlādes sesiju nav.",
    valueSaved: "Saglabāts: {value}",
    commandDone: "Komanda izpildīta.",
    commandNotConfirmed: "IMMAX komandu neapstiprināja. Pašreizējais stāvoklis: {state}.",
    chargerWaiting: "Komanda pieņemta. IMMAX gaida auto uzlādes pieprasījumu (pašlaik 0 A); pāreja var ilgt līdz 2 minūtēm.",
    chargerStarted: "Komanda pieņemta. IMMAX uzlādē ar {current} A.",
    chargerDelayed: "Komanda pieņemta. IMMAX uzlāde atlikta uz 12 stundām.",
    chargerOfflineCommand: "IMMAX Tuya Local nav sasniedzams. Komanda netika sūtīta.",
  },
  en: {
    refresh: "Refresh",
    settings: "Settings",
    entitySettings: "IMMAX entity sources",
    clearDate: "Clear date",
    periodLabel: "History period",
    specificDate: "Specific date",
    summary: "Summary",
    commands: "Commands",
    historyChart: "History chart",
    detailedHistoryChart: "Detailed history chart",
    loading: "Loading Home Assistant data...",
    updated: "Updated {time}. Hover or touch the charts to inspect values at a specific time.",
    loadError: "Could not load data: {error}",
    unavailable: "Unavailable",
    noHistory: "No history data in the selected period.",
    lastChanged: "Changed {time}",
    chargingTitle: "Renault ZOE charging",
    chargingSubtitle: "Charging control, Nord Pool prices, vehicle state and full history.",
    immaxTitle: "IMMAX smart charging",
    immaxSubtitle: "Charger control, solar surplus, power limits and full history.",
    actions: "Commands",
    startCharge: "Start charging",
    stopCharge: "Stop charging",
    startClimate: "Start climate",
    smartCharging: "Smart charging",
    planAndTarget: "Plan and target",
    locationAndStatus: "Location and status",
    chargerControl: "Charger control",
    localControls: "Tuya Local controls",
    limitsAndTarget: "Limits and target",
    activeMode: "Active mode settings",
    measurements: "Measurements",
    deviceDetails: "Device information",
    priceAndPower: "Nord Pool price and ZOE charging power",
    priceAndPowerNote: "Price c/kWh, power kW",
    batteryHistory: "Battery and charging history",
    batteryHistoryNote: "SOC %, charging power kW",
    immaxPower: "IMMAX, solar and total load history",
    immaxPowerNote: "Power kW, battery SOC %",
    immaxNordpool: "Nord Pool prices and price setpoint",
    immaxNordpoolNote: "Nord Pool price and maximum-price setpoint, c/kWh",
    phaseHistory: "Phase current and voltage history",
    phaseHistoryNote: "Current A, voltage V",
    chargeSessions: "Renault API charge sessions",
    chargeSessionsNote: "Completed sessions in the current month",
    entityHistory: "IMMAX data freshness",
    entityHistoryNote: "Click a value to open its Home Assistant history.",
    battery: "Battery",
    range: "Range",
    mileage: "Mileage",
    chargeState: "Charge state",
    plugState: "Plug state",
    chargingMode: "Charging mode",
    currentPrice: "Current price",
    location: "Location",
    elektrumStation: "Elektrum Drive station",
    effectivePrice: "Effective charging price",
    notDetected: "Not detected",
    chargerStatus: "Charger status",
    chargerOnline: "Charger online",
    chargerProblem: "Charger problem",
    chargingPower: "Charging power",
    totalPower: "Total charger power",
    totalLoad: "Total AC load",
    currentLimit: "Current limit",
    chargerEnergy: "Charger energy",
    sessionEnergy: "Current session energy",
    chargerTemperature: "Charger temperature",
    siteBatterySoc: "Site battery SOC",
    smartMode: "Smart mode",
    detectedPhases: "Detected phases",
    smartEnabled: "Enable smart charging",
    usePriceCap: "Use maximum price",
    maxPrice: "Maximum price incl. VAT",
    targetMode: "Target mode",
    targetSoc: "Target SOC",
    targetRange: "Target range",
    readyBy: "Ready by",
    smartStatus: "Smart charging status",
    plannedCharging: "Planned charging",
    expectedLevel: "Expected charge level",
    estimatedCost: "Estimated cost",
    actualCost: "Actual cost",
    remainingTime: "Charging time remaining",
    calculatedPower: "Calculated charging power",
    estimatedFullAt: "Estimated 100%",
    notChargingNow: "Not charging",
    notScheduled: "Not scheduled",
    locationControl: "Smart charging at this location",
    anyLocation: "Allow at any location",
    locationMatches: "Current location matches",
    apiUpdated: "Renault API updated",
    delayPeriod: "Delay period",
    totalPowerLimit: "Total AC power limit",
    socStop: "Pause at battery SOC",
    socResume: "Resume at battery SOC",
    externalSocTarget: "Use external EV SOC target",
    energyToAdd: "Energy to add",
    chargeTarget: "EV charge target",
    nordpoolCurrent: "Nord Pool charging current",
    planningPower: "Planning power",
    phaseMode: "Phase mode",
    reservePower: "Reserve (+) / battery support (-)",
    minSolarPower: "Minimum charging power",
    maxSolarPower: "Maximum charging power",
    solarProduction: "Solar production",
    availableSolar: "Available solar surplus",
    targetPower: "Target charging power",
    gridExport: "Grid export",
    batteryCharging: "Battery charging",
    batteryDischarging: "Battery discharging",
    aiAdvisor: "AI advisor",
    aiAdvice: "AI advice",
    phaseA: "Phase A",
    phaseB: "Phase B",
    phaseC: "Phase C",
    phaseAVoltage: "Phase A voltage",
    phaseACurrent: "Phase A current",
    phaseBVoltage: "Phase B voltage",
    phaseBCurrent: "Phase B current",
    phaseCVoltage: "Phase C voltage",
    phaseCCurrent: "Phase C current",
    phaseAPower: "Phase A power",
    phaseBPower: "Phase B power",
    phaseCPower: "Phase C power",
    workMode: "Work mode",
    delayTimer: "Delay timer",
    requireEarth: "Require protective earth",
    onlineControl: "Charger online switch",
    chargeNow: "Charge now",
    pause12h: "Delay for 12 hours",
    restartCharger: "Restart charger",
    disableEarth: "Disable earth control",
    disableEarthConfirm: "Disable the charger's protective-earth check?",
    deviceVersion: "System version",
    deviceInfo: "Hardware information",
    realtimeData: "Tuya Local realtime data",
    supportedCurrent: "Supported currents",
    faultCode: "Fault code",
    analysisInterval: "Analysis interval",
    aiCurrentCap: "AI current cap",
    voltage: "voltage",
    current: "current",
    power: "power",
    startEnd: "Start / end",
    station: "Station",
    connector: "Connector",
    homeNordPool: "Home / Nord Pool",
    elektrumDrive: "Elektrum Drive",
    elektrumDriveApp: "Elektrum Drive",
    mobilly: "Mobilly",
    ignitisOnApp: "Ignitis ON",
    ikrautasApp: "IKRAUTAS",
    operatorExact: "operator data",
    calculatedFallback: "calculated; operator data unavailable",
    duration: "Duration",
    batteryEnergy: "Battery energy",
    gridEnergy: "Grid energy",
    priceDelivery: "Price incl. delivery",
    cost: "Cost",
    status: "Status",
    total: "Total",
    noSessions: "No completed charge sessions in the current month.",
    valueSaved: "Saved: {value}",
    commandDone: "Command completed.",
    commandNotConfirmed: "IMMAX did not confirm the command. Current state: {state}.",
    chargerWaiting: "Command accepted. IMMAX is waiting for the vehicle to request charging (currently 0 A); the transition can take up to 2 minutes.",
    chargerStarted: "Command accepted. IMMAX is charging at {current} A.",
    chargerDelayed: "Command accepted. IMMAX charging is delayed for 12 hours.",
    chargerOfflineCommand: "IMMAX Tuya Local is offline. The command was not sent.",
  },
};

const CONFIG = {
  charging: {
    icon: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 17h14l-1.2-6.2A2 2 0 0 0 15.84 9H8.16a2 2 0 0 0-1.96 1.8L5 17Z"/>
        <path d="M7 9l1.2-3h7.6L17 9M7 17v2M17 17v2M8 14h.01M16 14h.01"/>
        <path d="M12.5 6.2 11 9h2l-1.5 3"/>
      </svg>`,
    titleKey: "chargingTitle",
    subtitleKey: "chargingSubtitle",
    metrics: [
      ["sensor.battery", "battery"],
      ["sensor.battery_autonomy", "range"],
      ["sensor.mileage", "mileage"],
      ["sensor.zoe_calculated_charging_power", "calculatedPower"],
      ["sensor.battery", "estimatedFullAt", { display: "estimatedFull" }],
      ["sensor.charge_state", "chargeState"],
      ["sensor.plug_state", "plugState"],
      ["select.renault_zoe_new_charging_mode", "chargingMode"],
      ["sensor.renault_zoe_new_effective_charging_price", "effectivePrice"],
      ["sensor.renault_zoe_new_elektrum_drive_station", "elektrumStation"],
    ],
    actions: [
      ["button.start_charge", "startCharge", "start", "play"],
      ["button.stop_charge", "stopCharge", "stop", "square"],
      ["button.start_air_conditioner", "startClimate", "start", "fan"],
    ],
    panels: [
      {
        title: "smartCharging",
        items: [
          ["input_boolean.zoe_smart_charging", "smartEnabled"],
          ["input_boolean.zoe_max_price_enabled", "usePriceCap"],
          ["input_number.zoe_max_energy_price", "maxPrice"],
          ["input_select.zoe_charge_target_mode", "targetMode"],
          ["input_number.zoe_charge_target", "targetSoc", { whenMode: "soc" }],
          ["input_number.zoe_charge_range_target", "targetRange", { whenMode: "range" }],
          ["input_datetime.zoe_ready_by", "readyBy"],
        ],
      },
      {
        title: "locationAndStatus",
        items: [
          ["select.renault_zoe_new_charging_mode", "chargingMode"],
          ["switch.renault_zoe_new_smart_charging_location_allowed", "locationControl"],
          ["switch.renault_zoe_new_any_location", "anyLocation"],
          ["binary_sensor.renault_zoe_new_smart_charging_location_allowed", "locationMatches"],
          ["input_text.zoe_smart_charge_status", "smartStatus"],
          ["sensor.zoe_planned_charging_times", "plannedCharging"],
          ["sensor.zoe_planned_charge_level", "expectedLevel"],
          ["sensor.zoe_estimated_charge_cost", "estimatedCost"],
          ["sensor.zoe_actual_charging_cost", "actualCost"],
          ["sensor.zoe_charging_remaining_time", "remainingTime"],
          ["sensor.zoe_calculated_charging_power", "calculatedPower"],
          ["sensor.renault_zoe_new_api_last_updated", "apiUpdated"],
        ],
      },
    ],
    mainChart: {
      title: "priceAndPower",
      subtitle: "priceAndPowerNote",
    },
    secondaryChart: {
      title: "batteryHistory",
      subtitle: "batteryHistoryNote",
    },
    detailTitle: "chargeSessions",
    detailSubtitle: "chargeSessionsNote",
  },
  immax: {
    icon: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8 3v6M16 3v6M6 9h12v3a6 6 0 0 1-6 6v3"/>
        <path d="m13.5 10-3 4h3l-3 4"/>
      </svg>`,
    titleKey: "immaxTitle",
    subtitleKey: "immaxSubtitle",
    metrics: [
      ["sensor.immax_ev_charger_status", "chargerStatus"],
      ["sensor.renault_zoe_new_immax_solar_charger_power", "chargingPower"],
      ["sensor.renault_zoe_new_immax_total_site_load", "totalLoad"],
      ["number.immax_ev_charger_current", "currentLimit"],
      ["sensor.immax_ev_charger_energy", "chargerEnergy"],
      ["sensor.unibms_soc", "siteBatterySoc"],
      ["input_select.immax_smart_charging_mode", "smartMode"],
      ["sensor.renault_zoe_new_immax_detected_phase_mode", "detectedPhases"],
      ["binary_sensor.renault_zoe_new_immax_online", "chargerOnline"],
      ["binary_sensor.renault_zoe_new_immax_problem", "chargerProblem"],
      ["sensor.immax_ev_charger_temperature", "chargerTemperature"],
      ["sensor.immax_ev_charger_charge_energy_once", "sessionEnergy"],
    ],
    actions: [
      [
        "select.immax_ev_charger_charging_mode",
        "chargeNow",
        "start",
        "play",
        {
          command: "immaxStart",
        },
      ],
      [
        "select.immax_ev_charger_charging_mode",
        "pause12h",
        "stop",
        "clock",
        {
          command: "immaxDelay",
        },
      ],
      [
        "switch.immax_ev_charger_require_earth",
        "disableEarth",
        "stop",
        "shieldOff",
        {
          confirmKey: "disableEarthConfirm",
          requiresState: "on",
          expectedState: "off",
          calls: [
            {
              domain: "switch",
              service: "turn_off",
              entityId: "switch.immax_ev_charger_require_earth",
            },
          ],
        },
      ],
      [
        "button.immax_ev_charger_restart",
        "restartCharger",
        "neutral",
        "restart",
      ],
    ],
    panels: [
      {
        title: "localControls",
        items: [
          ["select.immax_ev_charger_charging_mode", "chargingMode"],
          ["number.immax_ev_charger_current", "currentLimit"],
          ["number.immax_ev_charger_delay_timer", "delayTimer"],
          ["switch.immax_ev_charger_require_earth", "requireEarth"],
          ["switch.immax_ev_charger_online_state", "onlineControl"],
          ["sensor.immax_ev_charger_status", "chargerStatus"],
          ["binary_sensor.immax_ev_charger_problem", "chargerProblem"],
        ],
      },
      {
        title: "chargerControl",
        items: [
          ["input_select.immax_smart_charging_mode", "smartMode"],
          ["sensor.renault_zoe_new_immax_smart_charge_status", "smartStatus"],
          ["input_number.immax_delay_period", "delayPeriod"],
          ["input_boolean.immax_ai_advisor_enabled", "aiAdvisor"],
          ["input_text.immax_ai_advice", "aiAdvice"],
        ],
      },
      {
        title: "limitsAndTarget",
        items: [
          ["input_number.immax_total_power_limit", "totalPowerLimit"],
          ["input_boolean.immax_charge_to_percentage_enabled", "externalSocTarget"],
          ["input_number.immax_energy_to_add", "energyToAdd"],
          ["input_number.immax_charge_target_percentage", "chargeTarget"],
          ["input_number.immax_planning_power", "planningPower"],
        ],
      },
      {
        title: "activeMode",
        items: [
          ["input_boolean.immax_max_price_enabled", "usePriceCap", { whenSmartMode: "nord" }],
          ["input_number.immax_max_energy_price", "maxPrice", { whenSmartMode: "nord" }],
          ["input_number.immax_nordpool_current", "nordpoolCurrent", { whenSmartMode: "nord" }],
          ["sensor.renault_zoe_new_immax_planned_charging_times", "plannedCharging", { whenSmartMode: "nord" }],
          ["sensor.renault_zoe_new_immax_planned_energy", "energyToAdd", { whenSmartMode: "nord" }],
          ["sensor.renault_zoe_new_immax_estimated_charge_cost", "estimatedCost", { whenSmartMode: "nord" }],
          ["input_select.immax_solar_phase_mode", "phaseMode", { whenSmartMode: "solar" }],
          ["input_number.immax_solar_reserve_power", "reservePower", { whenSmartMode: "solar" }],
          ["input_number.immax_solar_min_power", "minSolarPower", { whenSmartMode: "solar" }],
          ["input_number.immax_solar_max_power", "maxSolarPower", { whenSmartMode: "solar" }],
          ["sensor.renault_zoe_new_immax_solar_production", "solarProduction", { whenSmartMode: "solar" }],
          ["sensor.renault_zoe_new_immax_solar_available_power", "availableSolar", { whenSmartMode: "solar" }],
          ["sensor.renault_zoe_new_immax_solar_target_power", "targetPower", { whenSmartMode: "solar" }],
          ["sensor.renault_zoe_new_immax_solar_grid_export", "gridExport", { whenSmartMode: "solar" }],
          ["sensor.renault_zoe_new_immax_solar_battery_charge", "batteryCharging", { whenSmartMode: "solar" }],
          ["sensor.renault_zoe_new_immax_solar_battery_discharge", "batteryDischarging", { whenSmartMode: "solar" }],
        ],
      },
      {
        title: "measurements",
        items: [
          ["sensor.immax_ev_charger_voltage_a", "phaseAVoltage"],
          ["sensor.immax_ev_charger_current_a", "phaseACurrent"],
          ["sensor.immax_ev_charger_power_a", "phaseAPower"],
          ["sensor.immax_ev_charger_voltage_b", "phaseBVoltage"],
          ["sensor.immax_ev_charger_current_b", "phaseBCurrent"],
          ["sensor.immax_ev_charger_power_b", "phaseBPower"],
          ["sensor.immax_ev_charger_voltage_c", "phaseCVoltage"],
          ["sensor.immax_ev_charger_current_c", "phaseCCurrent"],
          ["sensor.immax_ev_charger_power_c", "phaseCPower"],
          ["sensor.immax_ev_charger_power_total", "totalPower"],
          ["sensor.immax_ev_charger_temperature", "chargerTemperature"],
          ["sensor.immax_ev_charger_charge_energy_once", "sessionEnergy"],
          ["sensor.immax_ev_charger_energy", "chargerEnergy"],
        ],
      },
      {
        title: "deviceDetails",
        items: [
          ["sensor.immax_ev_charger_system_version", "deviceVersion"],
          ["sensor.immax_ev_charger_device_info", "deviceInfo"],
          ["sensor.immax_ev_charger_realtime_data", "realtimeData"],
          ["sensor.immax_ev_charger_current_list", "supportedCurrent"],
          ["sensor.immax_ev_charger_fault", "faultCode"],
        ],
      },
    ],
    mainChart: {
      title: "immaxPower",
      subtitle: "immaxPowerNote",
    },
    secondaryChart: {
      title: "phaseHistory",
      subtitle: "phaseHistoryNote",
    },
    detailTitle: "entityHistory",
    detailSubtitle: "entityHistoryNote",
  },
};

const ICONS = {
  play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7Z"/></svg>',
  square: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6h12v12H6z"/></svg>',
  fan: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 12c-1.5-2.8-.8-7 2-8.5 2.1-1.1 3.8.6 3.3 2.7-.6 2.4-2.5 4.6-5.3 5.8Z"/><path d="M12 12c2.8-1.5 7-.8 8.5 2 1.1 2.1-.6 3.8-2.7 3.3-2.4-.6-4.6-2.5-5.8-5.3Z"/><path d="M12 12c1.5 2.8.8 7-2 8.5-2.1 1.1-3.8-.6-3.3-2.7.6-2.4 2.5-4.6 5.3-5.8Z"/><path d="M12 12c-2.8 1.5-7 .8-8.5-2-1.1-2.1.6-3.8 2.7-3.3 2.4.6 4.6 2.5 5.8 5.3Z"/><circle cx="12" cy="12" r="1.3"/></svg>',
  clock: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  restart: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/></svg>',
  shieldOff: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5 6v5c0 4.4 2.9 8.4 7 10 1.2-.5 2.3-1.2 3.2-2"/><path d="M19 15V6l-7-3M4 4l16 16"/></svg>',
};

const pageConfig = CONFIG[PAGE];
const pageTitleEl = document.getElementById("pageTitle");
const pageSubtitleEl = document.getElementById("pageSubtitle");
const titleIconEl = document.getElementById("titleIcon");
const statusEl = document.getElementById("status");
const metricsEl = document.getElementById("metrics");
const actionsEl = document.getElementById("actions");
const controlPanelsEl = document.getElementById("controlPanels");
const periodEl = document.getElementById("period");
const dayDateEl = document.getElementById("dayDate");
const clearDateEl = document.getElementById("clearDate");
const settingsEl = document.getElementById("settings");
const entitySettingsEl = document.getElementById("entitySettings");
const reloadEl = document.getElementById("reload");
const reloadLabelEl = document.getElementById("reloadLabel");
const detailTitleEl = document.getElementById("detailTitle");
const detailSubtitleEl = document.getElementById("detailSubtitle");
const detailContentEl = document.getElementById("detailContent");
const mainChartTitleEl = document.getElementById("mainChartTitle");
const mainChartSubtitleEl = document.getElementById("mainChartSubtitle");
const secondaryChartTitleEl = document.getElementById("secondaryChartTitle");
const secondaryChartSubtitleEl = document.getElementById("secondaryChartSubtitle");

let language = "lv";
let cachedParentHass = null;
let currentStates = {};
let loading = false;
let historyLoading = false;
let lastHistoryLoad = 0;
let activeRange = null;
let statusLockUntil = 0;
let commandInProgress = false;
let cachedHistoryMap = new Map();
let cachedStatisticsMap = new Map();

function t(key, values = {}) {
  let text = I18N[language][key] ?? I18N.lv[key] ?? key;
  for (const [name, value] of Object.entries(values)) {
    text = text.replaceAll(`{${name}}`, value);
  }
  return text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function localDateValue(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function toNumber(value) {
  if (value === null || value === undefined || String(value).trim() === "") {
    return null;
  }
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function stateTime(state) {
  return new Date(
    state?.last_updated || state?.last_changed || state?.last_reported || 0,
  ).getTime();
}

function setStatus(text, warn = false, lockMilliseconds = 0) {
  if (lockMilliseconds > 0) {
    statusLockUntil = Date.now() + lockMilliseconds;
  } else if (!warn && Date.now() < statusLockUntil) {
    return;
  }
  statusEl.textContent = text;
  statusEl.classList.toggle("warn", warn);
}

function parseMaybeJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

async function getParentHass() {
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
  return cachedParentHass;
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
      return await parentHass.callApi(method, apiPath, options.body);
    } catch (error) {
      console.debug("Parent Home Assistant API request failed", error);
    }
  }

  const token = await getAccessToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const request = { ...options, headers, credentials: "same-origin" };
  if (request.body && typeof request.body !== "string") {
    request.body = JSON.stringify(request.body);
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, request);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  if (response.status === 204) return null;
  return response.json();
}

async function callService(domain, service, entityId, data = {}) {
  const serviceData = { ...data, entity_id: entityId };
  const hass = await getParentHass();
  if (hass?.callService) {
    return hass.callService(domain, service, serviceData);
  }
  return haFetch(`/api/services/${domain}/${service}`, {
    method: "POST",
    body: serviceData,
  });
}

function waitFor(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function isStateAvailable(state) {
  return Boolean(
    state
    && state.state !== "unknown"
    && state.state !== "unavailable",
  );
}

function immaxControlAvailable() {
  return [
    "select.immax_ev_charger_charging_mode",
    "number.immax_ev_charger_current",
    "text.immax_ev_charger_charge_mode",
  ].every((entityId) => isStateAvailable(stateFor(entityId)));
}

function immaxModePayload(delayed) {
  if (!delayed) {
    return JSON.stringify({ pt: 0, dt: 0, ss: "00:00", se: "00:00" });
  }
  const start = new Date(Date.now() + 12 * 60 * 60 * 1000);
  const hours = String(start.getHours()).padStart(2, "0");
  const minutes = String(start.getMinutes()).padStart(2, "0");
  return JSON.stringify({
    pt: 1,
    dt: 24,
    ss: `${hours}:${minutes}`,
    se: "00:00",
  });
}

async function selectImmaxManualMode() {
  if (stateFor("input_select.immax_smart_charging_mode")?.state === "Off") return;
  await callService(
    "input_select",
    "select_option",
    "input_select.immax_smart_charging_mode",
    { option: "Off" },
  );
  // The existing mode-change automation first puts the charger into a safe
  // delayed state. Let that sequence finish before issuing a manual command.
  await waitFor(5000);
}

async function setImmaxDelayedMode() {
  await callService(
    "text",
    "set_value",
    "text.immax_ev_charger_charge_mode",
    { value: immaxModePayload(true) },
  );
  await callService(
    "number",
    "set_value",
    "number.immax_ev_charger_delay_timer",
    { value: 12 },
  );
  await callService(
    "number",
    "set_value",
    "number.immax_ev_charger_current",
    { value: 6 },
  );
  await callService(
    "select",
    "select_option",
    "select.immax_ev_charger_charging_mode",
    { option: "delayed_charge" },
  );
}

async function refreshImmaxCommandState() {
  // Tuya Local shares one connection between all entities on this device.
  // Refreshing several entities at once can create overlapping polls, so rely
  // on the integration's normal update and its optimistic command state.
  await waitFor(1200);
  await loadCurrent(true);
}

async function runImmaxCommand(command) {
  if (!immaxControlAvailable()) {
    throw new Error(t("chargerOfflineCommand"));
  }

  const scriptEntityId = command === "immaxDelay"
    ? "script.immax_delay_12h"
    : "script.immax_charge_now_6a";
  if (isStateAvailable(stateFor(scriptEntityId))) {
    await callService("script", "turn_on", scriptEntityId);
    await waitFor(command === "immaxDelay" ? 7500 : 12500);
    await refreshImmaxCommandState();
  } else {
    await selectImmaxManualMode();
    await setImmaxDelayedMode();
    if (command === "immaxDelay") {
      await waitFor(1800);
    } else {
      // Writing immediate while it is already selected is ignored. Start from
      // delayed mode at 6 A, then make the real immediate transition.
      await waitFor(4000);
      await callService(
        "text",
        "set_value",
        "text.immax_ev_charger_charge_mode",
        { value: immaxModePayload(false) },
      );
      await callService(
        "select",
        "select_option",
        "select.immax_ev_charger_charging_mode",
        { option: "immediate" },
      );
      await waitFor(1800);
    }
    await refreshImmaxCommandState();
  }

  const mode = stateFor("select.immax_ev_charger_charging_mode")?.state;
  if (command === "immaxDelay") {
    return mode === "delayed_charge"
      ? { message: t("chargerDelayed"), warn: false }
      : {
        message: t("commandNotConfirmed", { state: displayState(stateFor(
          "select.immax_ev_charger_charging_mode",
        )) }),
        warn: true,
      };
  }
  if (mode !== "immediate") {
    return {
      message: t("commandNotConfirmed", { state: displayState(stateFor(
        "select.immax_ev_charger_charging_mode",
      )) }),
      warn: true,
    };
  }
  const current = toNumber(stateFor("sensor.immax_ev_charger_current_a")?.state);
  const status = stateFor("sensor.immax_ev_charger_status")?.state;
  if (status === "charging" || current > 0.5) {
    return {
      message: t("chargerStarted", {
        current: Number.isFinite(current) ? current.toFixed(1) : "6",
      }),
      warn: false,
    };
  }
  return { message: t("chargerWaiting"), warn: true };
}

async function showMoreInfo(entityId) {
  try {
    const homeAssistant = window.parent.document.querySelector("home-assistant");
    homeAssistant?.dispatchEvent(new window.parent.CustomEvent("hass-more-info", {
      detail: { entityId },
      bubbles: true,
      composed: true,
    }));
  } catch (error) {
    console.debug("Could not open more-info", error);
    window.parent.location.assign(`/history?entity_id=${encodeURIComponent(entityId)}`);
  }
}

function stateFor(entityId) {
  return currentStates[entityId] || null;
}

function plannedFullChargeDisplay() {
  const plannedLevel = toNumber(stateFor("sensor.zoe_planned_charge_level")?.state);
  if (!Number.isFinite(plannedLevel) || plannedLevel < 99.5) return null;
  const plannedTimes = stateFor("sensor.zoe_planned_charging_times")?.state || "";
  const matches = [
    ...plannedTimes.matchAll(/(\d{2})\.(\d{2})\s+\d{2}:\d{2}-(\d{2}:\d{2})/g),
  ];
  if (!matches.length) return null;
  const lastWindow = matches[matches.length - 1];
  return `~${lastWindow[1]}.${lastWindow[2]} ${lastWindow[3]}`;
}

function estimatedFullChargeDisplay() {
  const batteryState = stateFor("sensor.battery");
  const powerState = stateFor("sensor.zoe_calculated_charging_power");
  const soc = toNumber(batteryState?.state);
  if (!Number.isFinite(soc)) return t("unavailable");
  if (soc >= 99.5) return "100%";

  const charging = stateFor("binary_sensor.charging")?.state === "on"
    || stateFor("sensor.charge_state")?.state === "charge_in_progress";
  const smartCharging = stateFor("input_boolean.zoe_smart_charging")?.state === "on";
  const power = toNumber(powerState?.state);
  if (charging && Number.isFinite(power) && power > 0) {
    const capacity = toNumber(powerState?.attributes?.battery_capacity_kwh) || 52;
    const efficiency = toNumber(powerState?.attributes?.charging_efficiency) || 0.9;
    const hoursRemaining = ((100 - soc) / 100 * capacity) / (power * efficiency);
    if (Number.isFinite(hoursRemaining) && hoursRemaining >= 0 && hoursRemaining <= 48) {
      const fullAt = new Date(Date.now() + hoursRemaining * 3600000);
      const now = new Date();
      const sameDay = fullAt.getFullYear() === now.getFullYear()
        && fullAt.getMonth() === now.getMonth()
        && fullAt.getDate() === now.getDate();
      const formatted = new Intl.DateTimeFormat(language === "lv" ? "lv-LV" : "en-GB", {
        ...(sameDay ? {} : { day: "2-digit", month: "2-digit" }),
        hour: "2-digit",
        minute: "2-digit",
      }).format(fullAt);
      return `~${formatted}`;
    }
  }

  if (charging) return t("unavailable");
  if (!smartCharging) return t("notChargingNow");
  return plannedFullChargeDisplay() || t("notScheduled");
}

function displayState(state) {
  if (!state || ["unknown", "unavailable", "none", ""].includes(state.state)) {
    return t("unavailable");
  }
  const unit = state.attributes?.unit_of_measurement;
  const numeric = toNumber(state.state);
  if (Number.isFinite(numeric)) {
    const decimals = Math.abs(numeric) >= 100 ? 0 : Math.abs(numeric) >= 10 ? 1 : 2;
    const formatted = new Intl.NumberFormat(language === "lv" ? "lv-LV" : "en-GB", {
      maximumFractionDigits: decimals,
    }).format(numeric);
    return unit ? `${formatted} ${unit}` : formatted;
  }
  if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(state.state)) {
    const timestamp = new Date(state.state).getTime();
    if (Number.isFinite(timestamp)) {
      return new Intl.DateTimeFormat(language === "lv" ? "lv-LV" : "en-GB", {
        dateStyle: "short",
        timeStyle: "medium",
      }).format(timestamp);
    }
  }
  const translatedStates = {
    lv: {
      not_in_charge: "Netiek lādēts",
      charge_in_progress: "Notiek uzlāde",
      unplugged: "Atvienots",
      plugged: "Pievienots",
      always: "Vienmēr",
      delayed: "Atlikts",
      scheduled: "Ieplānots",
      plugged_in: "Pievienots",
      immediate: "Tūlītēja uzlāde",
      delayed_charge: "Atlikta uzlāde",
      charge_to_percent: "Uzlāde līdz procentiem",
      fixed_charge: "Fiksēta uzlāde",
      scheduled_charge: "Ieplānota uzlāde",
      not_detected: "Nav noteikta",
      "Solar surplus": "Saules pārpalikums",
      "Nord Pool": "Nord Pool",
      Off: "Izslēgts",
    },
    en: {
      not_in_charge: "Not charging",
      charge_in_progress: "Charging",
      unplugged: "Unplugged",
      plugged: "Plugged",
      always: "Always",
      delayed: "Delayed",
      scheduled: "Scheduled",
      plugged_in: "Plugged in",
      immediate: "Immediate",
      delayed_charge: "Delayed charge",
      charge_to_percent: "Charge to percentage",
      fixed_charge: "Fixed charge",
      scheduled_charge: "Scheduled charge",
      not_detected: "Not detected",
      "Solar surplus": "Solar surplus",
      "Nord Pool": "Nord Pool",
      Off: "Off",
    },
  };
  if (translatedStates[language][state.state]) {
    return translatedStates[language][state.state];
  }
  if (state.state === "on") return language === "lv" ? "Ieslēgts" : "On";
  if (state.state === "off") return language === "lv" ? "Izslēgts" : "Off";
  return state.state;
}

function displayOption(option) {
  const translations = {
    lv: {
      Off: "Izslēgts",
      "Solar surplus": "Saules pārpalikums",
      Auto: "Automātiski",
      "1 phase": "1 fāze",
      "3 phases": "3 fāzes",
      "SOC (%)": "SOC (%)",
      "Range (km)": "Nobraukums (km)",
      immediate: "Tūlītēja uzlāde",
      charge_to_percent: "Uzlāde līdz procentiem",
      fixed_charge: "Fiksēta uzlāde",
      scheduled_charge: "Ieplānota uzlāde",
      delayed_charge: "Atlikta uzlāde",
      charge_now: "Uzlādēt tūlīt",
      charge_pct: "Uzlādēt līdz procentiem",
      charge_energy: "Uzlādēt noteiktu enerģiju",
      charge_schedule: "Uzlāde pēc grafika",
      charge_delay: "Atlikta uzlāde",
    },
    en: {
      Off: "Off",
      "Solar surplus": "Solar surplus",
      Auto: "Automatic",
      "1 phase": "1 phase",
      "3 phases": "3 phases",
      "SOC (%)": "SOC (%)",
      "Range (km)": "Range (km)",
      immediate: "Immediate charging",
      charge_to_percent: "Charge to percentage",
      fixed_charge: "Fixed charging",
      scheduled_charge: "Scheduled charging",
      delayed_charge: "Delayed charging",
      charge_now: "Charge now",
      charge_pct: "Charge to percentage",
      charge_energy: "Charge fixed energy",
      charge_schedule: "Scheduled charging",
      charge_delay: "Delayed charging",
    },
  };
  return translations[language][option] || option;
}

function isWritable(entityId) {
  return [
    "input_boolean",
    "switch",
    "input_number",
    "number",
    "input_select",
    "select",
    "input_datetime",
  ].includes(entityId.split(".")[0]);
}

function itemIsVisible(item) {
  const options = item[2] || {};
  if (options.whenMode) {
    const mode = stateFor("input_select.zoe_charge_target_mode")?.state?.toLowerCase() || "";
    if (options.whenMode === "soc" && !mode.includes("soc")) return false;
    if (options.whenMode === "range" && !mode.includes("range")) return false;
  }
  if (options.whenSmartMode) {
    const mode = stateFor("input_select.immax_smart_charging_mode")?.state?.toLowerCase() || "";
    if (options.whenSmartMode === "nord" && !mode.includes("nord")) return false;
    if (options.whenSmartMode === "solar" && !mode.includes("solar")) return false;
  }
  return true;
}

function renderMetrics() {
  metricsEl.replaceChildren();
  for (const [entityId, labelKey, options = {}] of pageConfig.metrics) {
    const state = stateFor(entityId);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "metric";
    button.dataset.entity = entityId;
    button.title = entityId;
    const changed = options.display === "estimatedFull"
      ? Math.max(
        stateTime(state),
        stateTime(stateFor("sensor.zoe_calculated_charging_power")),
        stateTime(stateFor("sensor.zoe_planned_charging_times")),
      )
      : stateTime(state);
    const value = options.display === "estimatedFull"
      ? estimatedFullChargeDisplay()
      : displayState(state);
    button.innerHTML = `
      <span class="metric-label">${escapeHtml(t(labelKey))}</span>
      <strong class="metric-value">${escapeHtml(value)}</strong>
      <span class="metric-note">${changed ? escapeHtml(t("lastChanged", {
        time: new Intl.DateTimeFormat(language === "lv" ? "lv-LV" : "en-GB", {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        }).format(changed),
      })) : ""}</span>`;
    button.addEventListener("click", () => showMoreInfo(entityId));
    metricsEl.append(button);
  }
}

function renderActions() {
  actionsEl.replaceChildren();
  actionsEl.hidden = pageConfig.actions.length === 0;
  for (const [entityId, labelKey, style, icon, actionConfig = {}] of pageConfig.actions) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = style === "stop"
      ? "action-stop"
      : style === "start"
        ? "action-start"
        : "";
    button.innerHTML = `${ICONS[icon] || ""}<span>${escapeHtml(t(labelKey))}</span>`;
    const actionState = stateFor(entityId);
    button.disabled = (
      commandInProgress
      || !actionState
      || actionState.state === "unavailable"
      || (
        actionConfig.requiresState
        && actionState.state !== actionConfig.requiresState
      )
    );
    button.addEventListener("click", async () => {
      if (actionConfig.confirmKey && !window.confirm(t(actionConfig.confirmKey))) {
        return;
      }
      commandInProgress = true;
      button.disabled = true;
      try {
        if (actionConfig.command) {
          const result = await runImmaxCommand(actionConfig.command);
          setStatus(result.message, result.warn, 120000);
        } else {
          const calls = actionConfig.calls || [
            {
              domain: "button",
              service: "press",
              entityId,
              data: {},
            },
          ];
          for (const call of calls) {
            await callService(
              call.domain,
              call.service,
              call.entityId,
              call.data || {},
            );
          }
          await waitFor(1500);
          if (actionConfig.expectedState) {
            try {
              await callService("homeassistant", "update_entity", entityId);
            } catch (error) {
              console.debug("Could not refresh action entity", error);
            }
            await waitFor(700);
          }
          await loadCurrent(true);
          const actual = stateFor(entityId);
          if (
            actionConfig.expectedState
            && actual?.state !== actionConfig.expectedState
          ) {
            setStatus(t("commandNotConfirmed", {
              state: displayState(actual),
            }), true, 120000);
          } else {
            setStatus(t("commandDone"), false, 10000);
          }
        }
      } catch (error) {
        setStatus(t("loadError", { error: error.message }), true, 120000);
      } finally {
        commandInProgress = false;
        renderActions();
      }
    });
    actionsEl.append(button);
  }
}

function controlValue(entityId, state) {
  const domain = entityId.split(".")[0];
  if (!state || !isWritable(entityId)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "state-value";
    button.textContent = displayState(state);
    button.addEventListener("click", () => showMoreInfo(entityId));
    return button;
  }

  if (domain === "input_boolean" || domain === "switch") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `toggle ${state.state === "on" ? "on" : ""}`;
    button.setAttribute("role", "switch");
    button.setAttribute("aria-checked", String(state.state === "on"));
    button.setAttribute("aria-label", state.attributes?.friendly_name || entityId);
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        await callService(domain, "toggle", entityId);
        await new Promise((resolve) => window.setTimeout(resolve, 250));
        await loadCurrent(true);
      } catch (error) {
        setStatus(t("loadError", { error: error.message }), true);
      } finally {
        button.disabled = false;
      }
    });
    return button;
  }

  if (domain === "input_number" || domain === "number") {
    const input = document.createElement("input");
    input.type = "number";
    input.value = Number.isFinite(toNumber(state.state)) ? state.state : "";
    if (Number.isFinite(toNumber(state.attributes?.min))) input.min = state.attributes.min;
    if (Number.isFinite(toNumber(state.attributes?.max))) input.max = state.attributes.max;
    input.step = state.attributes?.step || "any";
    input.title = state.attributes?.unit_of_measurement || "";
    let saveTimer = null;
    let saving = false;
    let saveQueued = false;
    let lastSavedValue = toNumber(state.state);
    const saveValue = async () => {
      if (saveTimer) {
        window.clearTimeout(saveTimer);
        saveTimer = null;
      }
      const value = toNumber(input.value);
      if (!Number.isFinite(value)) return;
      if (
        Number.isFinite(lastSavedValue)
        && Math.abs(value - lastSavedValue) < Number.EPSILON
      ) return;
      if (saving) {
        saveQueued = true;
        return;
      }
      saving = true;
      input.dataset.saving = "true";
      try {
        await callService(domain, "set_value", entityId, { value });
        lastSavedValue = value;
        setStatus(t("valueSaved", { value: input.value }));
        await loadCurrent(true);
      } catch (error) {
        setStatus(t("loadError", { error: error.message }), true);
      } finally {
        saving = false;
        delete input.dataset.saving;
        if (saveQueued) {
          saveQueued = false;
          window.setTimeout(saveValue, 0);
        }
      }
    };
    input.addEventListener("input", () => {
      if (saveTimer) window.clearTimeout(saveTimer);
      saveTimer = window.setTimeout(saveValue, 500);
    });
    input.addEventListener("change", saveValue);
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      saveValue();
    });
    return input;
  }

  if (domain === "input_select" || domain === "select") {
    const select = document.createElement("select");
    const options = state.attributes?.options || [];
    for (const option of options) {
      const item = document.createElement("option");
      item.value = option;
      item.textContent = displayOption(option);
      item.selected = option === state.state;
      select.append(item);
    }
    select.addEventListener("change", async () => {
      select.disabled = true;
      select.blur();
      try {
        if (
          entityId === "select.immax_ev_charger_charging_mode"
          && ["immediate", "delayed_charge"].includes(select.value)
        ) {
          const result = await runImmaxCommand(
            select.value === "immediate" ? "immaxStart" : "immaxDelay",
          );
          setStatus(result.message, result.warn, 120000);
        } else {
          await callService(domain, "select_option", entityId, { option: select.value });
          await loadCurrent(true);
          setStatus(t("valueSaved", { value: select.value }));
        }
      } catch (error) {
        setStatus(t("loadError", { error: error.message }), true);
      } finally {
        select.disabled = false;
      }
    });
    return select;
  }

  if (domain === "input_datetime") {
    const input = document.createElement("input");
    input.type = "datetime-local";
    input.value = state.state.includes(" ") ? state.state.replace(" ", "T").slice(0, 16) : "";
    input.addEventListener("change", async () => {
      if (!input.value) return;
      input.disabled = true;
      try {
        await callService(domain, "set_datetime", entityId, {
          datetime: input.value.replace("T", " "),
        });
        setStatus(t("valueSaved", { value: input.value.replace("T", " ") }));
        await loadCurrent(true);
      } catch (error) {
        setStatus(t("loadError", { error: error.message }), true);
      } finally {
        input.disabled = false;
      }
    });
    return input;
  }

  const fallback = document.createElement("span");
  fallback.textContent = displayState(state);
  return fallback;
}

function renderPanels() {
  controlPanelsEl.replaceChildren();
  for (const panelConfig of pageConfig.panels) {
    const visibleItems = panelConfig.items.filter(itemIsVisible);
    if (!visibleItems.length) continue;
    const panel = document.createElement("article");
    panel.className = "panel";
    const header = document.createElement("div");
    header.className = "panel-header";
    header.innerHTML = `<div><h2>${escapeHtml(t(panelConfig.title))}</h2></div>`;
    const list = document.createElement("div");
    list.className = "control-list";
    for (const [entityId, labelKey] of visibleItems) {
      const state = stateFor(entityId);
      const row = document.createElement("div");
      row.className = "control-row";
      const label = document.createElement("div");
      label.className = "control-label";
      label.innerHTML = `<strong>${escapeHtml(t(labelKey))}</strong>`;
      label.title = entityId;
      const value = document.createElement("div");
      value.className = "control-value";
      value.append(controlValue(entityId, state));
      row.append(label, value);
      list.append(row);
    }
    panel.append(header, list);
    controlPanelsEl.append(panel);
  }
}

function immaxUsesNordPoolChart() {
  const mode = stateFor(
    "input_select.immax_smart_charging_mode",
  )?.state?.toLowerCase() || "";
  return PAGE === "immax" && mode.includes("nord");
}

function renderChartHeadings() {
  const mainChartConfig = immaxUsesNordPoolChart()
    ? { title: "immaxNordpool", subtitle: "immaxNordpoolNote" }
    : pageConfig.mainChart;
  mainChartTitleEl.textContent = t(mainChartConfig.title);
  mainChartSubtitleEl.textContent = t(mainChartConfig.subtitle);
  secondaryChartTitleEl.textContent = t(pageConfig.secondaryChart.title);
  secondaryChartSubtitleEl.textContent = t(pageConfig.secondaryChart.subtitle);
}

function applyLanguage() {
  document.documentElement.lang = language;
  document.title = t(pageConfig.titleKey);
  pageTitleEl.textContent = t(pageConfig.titleKey);
  pageSubtitleEl.textContent = t(pageConfig.subtitleKey);
  reloadLabelEl.textContent = t("refresh");
  settingsEl.title = t("settings");
  settingsEl.setAttribute("aria-label", t("settings"));
  entitySettingsEl.title = t("entitySettings");
  entitySettingsEl.setAttribute("aria-label", t("entitySettings"));
  clearDateEl.title = t("clearDate");
  clearDateEl.setAttribute("aria-label", t("clearDate"));
  periodEl.setAttribute("aria-label", t("periodLabel"));
  dayDateEl.title = t("specificDate");
  dayDateEl.setAttribute("aria-label", t("specificDate"));
  metricsEl.setAttribute("aria-label", t("summary"));
  actionsEl.setAttribute("aria-label", t("commands"));
  document.getElementById("mainChart").setAttribute(
    "aria-label",
    t("historyChart"),
  );
  document.getElementById("secondaryChart").setAttribute(
    "aria-label",
    t("detailedHistoryChart"),
  );
  renderChartHeadings();
  detailTitleEl.textContent = t(pageConfig.detailTitle);
  detailSubtitleEl.textContent = t(pageConfig.detailSubtitle);
  const selected = periodEl.value;
  const periodLabels = language === "lv"
    ? {
      "24h": "Šodiena (00–24)",
      "48h": "2 kalendāra dienas",
      "7d": "7 kalendāra dienas",
      "30d": "30 kalendāra dienas",
    }
    : {
      "24h": "Today (00–24)",
      "48h": "2 calendar days",
      "7d": "7 calendar days",
      "30d": "30 calendar days",
    };
  for (const option of periodEl.options) option.textContent = periodLabels[option.value];
  periodEl.value = selected;
  renderMetrics();
  renderActions();
  renderPanels();
  renderDetail();
  mainChart.draw();
  secondaryChart.draw();
}

function selectedRange() {
  const now = new Date();
  if (dayDateEl.value) {
    const start = new Date(`${dayDateEl.value}T00:00:00`);
    const end = new Date(start);
    end.setDate(end.getDate() + 1);
    return { start: start.getTime(), end: end.getTime() };
  }

  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  if (PAGE === "charging" && periodEl.value === "48h") {
    const end = new Date(start);
    end.setDate(end.getDate() + 2);
    return { start: start.getTime(), end: end.getTime() };
  }

  const days = {
    "24h": 1,
    "48h": 2,
    "7d": 7,
    "30d": 30,
  }[periodEl.value] || 2;
  start.setDate(start.getDate() - (days - 1));
  const end = new Date(now);
  end.setHours(0, 0, 0, 0);
  end.setDate(end.getDate() + 1);
  return { start: start.getTime(), end: end.getTime() };
}

function normalizeHistory(history) {
  const result = new Map();
  for (const group of history || []) {
    if (!group?.length || !group[0]?.entity_id) continue;
    result.set(group[0].entity_id, group);
  }
  return result;
}

function unitFor(entityId) {
  return stateFor(entityId)?.attributes?.unit_of_measurement || "";
}

function toKw(entityId, value) {
  if (!Number.isFinite(value)) return null;
  const unit = unitFor(entityId).toLowerCase();
  return unit === "w" ? value / 1000 : value;
}

function toCents(entityId, value) {
  if (!Number.isFinite(value)) return null;
  const unit = unitFor(entityId).toLowerCase();
  return unit.includes("eur") ? value * 100 : value;
}

function historyPoints(historyMap, entityId, transform = (value) => value) {
  const points = [];
  for (const state of historyMap.get(entityId) || []) {
    const value = transform(toNumber(state.state));
    const time = stateTime(state);
    if (Number.isFinite(value) && Number.isFinite(time)) points.push({ x: time, y: value });
  }
  const current = stateFor(entityId);
  const currentValue = transform(toNumber(current?.state));
  const currentTime = stateTime(current);
  if (Number.isFinite(currentValue) && Number.isFinite(currentTime)) {
    points.push({ x: currentTime, y: currentValue });
  }
  points.sort((left, right) => left.x - right.x);
  return dedupeAndDownsample(points);
}

function statisticsPoints(statisticsMap, entityId, transform = (value) => value) {
  const points = [];
  for (const row of statisticsMap.get(entityId) || []) {
    const sourceValue = Number.isFinite(row.mean)
      ? row.mean
      : Number.isFinite(row.state)
        ? row.state
        : row.sum;
    const value = transform(toNumber(sourceValue));
    const time = typeof row.start === "number"
      ? row.start
      : new Date(row.start).getTime();
    if (Number.isFinite(value) && Number.isFinite(time)) points.push({ x: time, y: value });
  }
  const current = stateFor(entityId);
  const currentValue = transform(toNumber(current?.state));
  const currentTime = stateTime(current);
  if (Number.isFinite(currentValue) && Number.isFinite(currentTime)) {
    points.push({ x: currentTime, y: currentValue });
  }
  points.sort((left, right) => left.x - right.x);
  return dedupeAndDownsample(points);
}

function pointsFor(historyMap, statisticsMap, entityId, transform = (value) => value) {
  const statistics = statisticsPoints(statisticsMap, entityId, transform);
  return statistics.length > 1
    ? statistics
    : historyPoints(historyMap, entityId, transform);
}

function dedupeAndDownsample(points, maximum = 1600) {
  const deduped = [];
  for (const point of points) {
    if (deduped.at(-1)?.x === point.x) deduped[deduped.length - 1] = point;
    else deduped.push(point);
  }
  if (deduped.length <= maximum) return deduped;
  const result = [];
  const bucketSize = deduped.length / maximum;
  for (let index = 0; index < maximum; index += 1) {
    const start = Math.floor(index * bucketSize);
    const end = Math.max(start + 1, Math.floor((index + 1) * bucketSize));
    const bucket = deduped.slice(start, end);
    result.push({
      x: bucket[Math.floor(bucket.length / 2)].x,
      y: bucket.reduce((sum, point) => sum + point.y, 0) / bucket.length,
    });
  }
  return result;
}

function priceForecastPoints(range) {
  const state = stateFor("sensor.renault_zoe_new_nord_pool_price");
  const raw = [
    ...(state?.attributes?.raw_today || []),
    ...(state?.attributes?.raw_tomorrow || []),
  ];
  const points = [];
  for (const slot of raw) {
    const time = new Date(slot.start).getTime();
    const value = toCents("sensor.renault_zoe_new_nord_pool_price", toNumber(slot.value));
    if (
      Number.isFinite(time)
      && Number.isFinite(value)
      && time >= range.start - 3600000
      && time <= range.end + 3600000
    ) {
      points.push({ x: time, y: value });
    }
  }
  return dedupeAndDownsample(points.sort((left, right) => left.x - right.x));
}

function mergePoints(...groups) {
  return dedupeAndDownsample(
    groups.flat().sort((left, right) => left.x - right.x),
  );
}

function constantPoints(value, range) {
  return Number.isFinite(value)
    ? [{ x: range.start, y: value }, { x: range.end, y: value }]
    : [];
}

function cssColor(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

class TimeChart {
  constructor(canvasId, tooltipId, legendId) {
    this.canvas = document.getElementById(canvasId);
    this.context = this.canvas.getContext("2d");
    this.tooltip = document.getElementById(tooltipId);
    this.legend = document.getElementById(legendId);
    this.series = [];
    this.range = { start: Date.now() - DAY_MS, end: Date.now() };
    this.axis = {};
    this.pointerX = null;
    this.hiddenSeries = new Set();
    this.canvas.addEventListener("pointermove", (event) => this.onPointer(event));
    this.canvas.addEventListener("pointerleave", () => {
      this.pointerX = null;
      this.tooltip.hidden = true;
      this.draw();
    });
    this.canvas.addEventListener("pointerdown", (event) => this.onPointer(event));
    this.resizeObserver = new ResizeObserver(() => this.draw());
    this.resizeObserver.observe(this.canvas);
  }

  setData(series, range, axis = {}) {
    this.series = series
      .filter((item) => item.points.length)
      .map((item, index) => ({ ...item, id: item.id || `series-${index}` }));
    this.range = range;
    this.axis = axis;
    const availableIds = new Set(this.series.map((item) => item.id));
    this.hiddenSeries = new Set(
      [...this.hiddenSeries].filter((id) => availableIds.has(id)),
    );
    this.renderLegend();
    this.draw();
  }

  visibleSeries() {
    return this.series.filter((series) => !this.hiddenSeries.has(series.id));
  }

  renderLegend() {
    this.legend.replaceChildren();
    for (const series of this.series) {
      const hidden = this.hiddenSeries.has(series.id);
      const item = document.createElement("button");
      item.type = "button";
      item.className = `legend-item ${hidden ? "is-hidden" : ""}`;
      item.setAttribute("aria-pressed", String(!hidden));
      item.title = language === "lv"
        ? `${hidden ? "Rādīt" : "Paslēpt"}: ${series.name}`
        : `${hidden ? "Show" : "Hide"}: ${series.name}`;
      item.innerHTML = `
        <span class="legend-swatch" style="background:${escapeHtml(series.color)}"></span>
        <span>${escapeHtml(series.name)}</span>`;
      item.addEventListener("click", () => {
        if (this.hiddenSeries.has(series.id)) this.hiddenSeries.delete(series.id);
        else this.hiddenSeries.add(series.id);
        this.pointerX = null;
        this.tooltip.hidden = true;
        this.renderLegend();
        this.draw();
      });
      this.legend.append(item);
    }
  }

  bounds(axisName) {
    const values = this.visibleSeries()
      .filter((series) => (series.axis || "left") === axisName)
      .flatMap((series) => series.points.map((point) => point.y))
      .filter(Number.isFinite);
    if (!values.length) return { min: 0, max: 1 };
    let min = Math.min(...values);
    let max = Math.max(...values);
    const requested = this.axis[axisName] || {};
    if (Number.isFinite(requested.min)) min = requested.min;
    else min = Math.min(0, min);
    if (Number.isFinite(requested.max)) max = requested.max;
    if (max <= min) max = min + 1;
    const padding = (max - min) * 0.08;
    if (!Number.isFinite(requested.min)) min -= padding;
    if (!Number.isFinite(requested.max)) max += padding;
    return { min, max };
  }

  draw() {
    const rect = this.canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const ratio = Math.min(2, window.devicePixelRatio || 1);
    const width = Math.round(rect.width * ratio);
    const height = Math.round(rect.height * ratio);
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    const context = this.context;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, rect.width, rect.height);

    const margin = {
      left: 58,
      right: this.visibleSeries().some((series) => series.axis === "right") ? 58 : 18,
      top: 14,
      bottom: 42,
    };
    const plot = {
      x: margin.left,
      y: margin.top,
      width: Math.max(10, rect.width - margin.left - margin.right),
      height: Math.max(10, rect.height - margin.top - margin.bottom),
    };
    this.plot = plot;
    const textColor = cssColor("--muted");
    const lineColor = cssColor("--line");
    const leftBounds = this.bounds("left");
    const rightBounds = this.bounds("right");
    this.chartBounds = { left: leftBounds, right: rightBounds };

    context.font = '11px Roboto, "Segoe UI", Arial, sans-serif';
    context.lineWidth = 1;
    context.strokeStyle = lineColor;
    context.fillStyle = textColor;
    context.textBaseline = "middle";
    for (let index = 0; index <= 5; index += 1) {
      const fraction = index / 5;
      const y = plot.y + plot.height * fraction;
      context.beginPath();
      context.moveTo(plot.x, y);
      context.lineTo(plot.x + plot.width, y);
      context.stroke();
      const leftValue = leftBounds.max - fraction * (leftBounds.max - leftBounds.min);
      context.textAlign = "right";
      context.fillText(formatAxis(leftValue), plot.x - 8, y);
      if (this.visibleSeries().some((series) => series.axis === "right")) {
        const rightValue = rightBounds.max - fraction * (rightBounds.max - rightBounds.min);
        context.textAlign = "left";
        context.fillText(formatAxis(rightValue), plot.x + plot.width + 8, y);
      }
    }

    const dateFormatter = new Intl.DateTimeFormat(language === "lv" ? "lv-LV" : "en-GB", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
    context.textAlign = "center";
    context.textBaseline = "top";
    for (let index = 0; index <= 6; index += 1) {
      const fraction = index / 6;
      const x = plot.x + plot.width * fraction;
      context.beginPath();
      context.moveTo(x, plot.y);
      context.lineTo(x, plot.y + plot.height);
      context.stroke();
      const time = this.range.start + fraction * (this.range.end - this.range.start);
      context.fillText(dateFormatter.format(time).replace(", ", " "), x, plot.y + plot.height + 9);
    }

    for (const series of this.visibleSeries()) {
      const bounds = series.axis === "right" ? rightBounds : leftBounds;
      context.beginPath();
      context.strokeStyle = series.color;
      context.lineWidth = series.width || 2;
      context.lineJoin = "round";
      context.lineCap = "round";
      let started = false;
      let previousPoint = null;
      let previousY = null;
      const maximumGap = series.maximumGap
        || Math.max(30 * 60000, (this.range.end - this.range.start) / 200);
      for (const point of series.points) {
        if (point.x < this.range.start || point.x > this.range.end) continue;
        const x = plot.x + (point.x - this.range.start) / (this.range.end - this.range.start) * plot.width;
        const y = plot.y + (bounds.max - point.y) / (bounds.max - bounds.min) * plot.height;
        if (!started || (previousPoint && point.x - previousPoint.x > maximumGap)) {
          context.moveTo(x, y);
          started = true;
        } else if (series.step) {
          context.lineTo(x, previousY);
          context.lineTo(x, y);
        } else {
          context.lineTo(x, y);
        }
        previousPoint = point;
        previousY = y;
      }
      context.stroke();
    }

    if (Number.isFinite(this.pointerX)) this.drawPointer();
    if (!this.visibleSeries().length) {
      context.fillStyle = textColor;
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.font = '14px Roboto, "Segoe UI", Arial, sans-serif';
      context.fillText(t("noHistory"), plot.x + plot.width / 2, plot.y + plot.height / 2);
    }
  }

  nearestPoint(points, time) {
    if (!points.length) return null;
    let low = 0;
    let high = points.length - 1;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (points[middle].x < time) low = middle + 1;
      else high = middle;
    }
    const before = points[Math.max(0, low - 1)];
    const after = points[low];
    return Math.abs(before.x - time) <= Math.abs(after.x - time) ? before : after;
  }

  onPointer(event) {
    if (!this.plot) return;
    const rect = this.canvas.getBoundingClientRect();
    const x = Math.min(
      this.plot.x + this.plot.width,
      Math.max(this.plot.x, event.clientX - rect.left),
    );
    this.pointerX = x;
    const time = this.range.start + (x - this.plot.x) / this.plot.width * (this.range.end - this.range.start);
    const rows = this.visibleSeries()
      .map((series) => ({ series, point: this.nearestPoint(series.points, time) }))
      .filter(({ point }) => point && Math.abs(point.x - time) < (this.range.end - this.range.start) / 12);
    if (!rows.length) {
      this.tooltip.hidden = true;
      this.draw();
      return;
    }
    const tooltipTime = rows[0].point.x;
    const formatter = new Intl.DateTimeFormat(language === "lv" ? "lv-LV" : "en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
    });
    this.tooltip.innerHTML = `
      <div class="tooltip-time">${escapeHtml(formatter.format(tooltipTime))}</div>
      ${rows.map(({ series, point }) => `
        <div class="tooltip-row">
          <span>${escapeHtml(series.name)}</span>
          <strong style="color:${escapeHtml(series.color)}">${escapeHtml(formatTooltip(point.y, series.unit))}</strong>
        </div>`).join("")}`;
    this.tooltip.hidden = false;
    const left = x + 14 + this.tooltip.offsetWidth > rect.width ? x - this.tooltip.offsetWidth - 14 : x + 14;
    this.tooltip.style.left = `${Math.max(4, left)}px`;
    this.tooltip.style.top = "16px";
    this.draw();
  }

  drawPointer() {
    const context = this.context;
    const plot = this.plot;
    const time = this.range.start
      + (this.pointerX - plot.x) / plot.width * (this.range.end - this.range.start);
    context.save();
    context.strokeStyle = cssColor("--line-strong");
    context.lineWidth = 1;
    context.setLineDash([4, 4]);
    context.beginPath();
    context.moveTo(this.pointerX, plot.y);
    context.lineTo(this.pointerX, plot.y + plot.height);
    context.stroke();
    context.setLineDash([]);
    for (const series of this.visibleSeries()) {
      const point = this.nearestPoint(series.points, time);
      if (!point) continue;
      const bounds = series.axis === "right" ? this.chartBounds.right : this.chartBounds.left;
      const x = plot.x + (point.x - this.range.start) / (this.range.end - this.range.start) * plot.width;
      const y = plot.y + (bounds.max - point.y) / (bounds.max - bounds.min) * plot.height;
      context.fillStyle = series.color;
      context.beginPath();
      context.arc(x, y, 3.5, 0, Math.PI * 2);
      context.fill();
    }
    context.restore();
  }
}

function formatAxis(value) {
  const absolute = Math.abs(value);
  if (absolute >= 1000) return `${(value / 1000).toFixed(1)}k`;
  if (absolute >= 100) return value.toFixed(0);
  if (absolute >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

function formatTooltip(value, unit) {
  return `${new Intl.NumberFormat(language === "lv" ? "lv-LV" : "en-GB", {
    maximumFractionDigits: 2,
  }).format(value)}${unit ? ` ${unit}` : ""}`;
}

const mainChart = new TimeChart("mainChart", "mainTooltip", "mainLegend");
const secondaryChart = new TimeChart("secondaryChart", "secondaryTooltip", "secondaryLegend");

async function loadHistory() {
  if (historyLoading) return;
  historyLoading = true;
  activeRange = selectedRange();
  const now = Date.now();
  const historyEnd = Math.min(activeRange.end, now);
  const entityIds = PAGE === "charging"
    ? [
      "sensor.renault_zoe_new_nord_pool_price",
      "sensor.zoe_active_charging_power",
      "sensor.battery",
    ]
    : [
      "sensor.renault_zoe_new_nord_pool_price",
      "sensor.renault_zoe_new_immax_solar_production",
      "sensor.renault_zoe_new_immax_solar_charger_power",
      "sensor.renault_zoe_new_immax_total_site_load",
      "sensor.unibms_soc",
      "sensor.immax_ev_charger_current_a",
      "sensor.immax_ev_charger_current_b",
      "sensor.immax_ev_charger_current_c",
      "sensor.immax_ev_charger_voltage_a",
      "sensor.immax_ev_charger_voltage_b",
      "sensor.immax_ev_charger_voltage_c",
    ];
  try {
    const statisticsEligible = new Set([
      "sensor.battery",
      "sensor.zoe_active_charging_power",
      "sensor.renault_zoe_new_nord_pool_price",
      "sensor.renault_zoe_new_immax_solar_production",
      "sensor.renault_zoe_new_immax_solar_charger_power",
      "sensor.renault_zoe_new_immax_total_site_load",
      "sensor.unibms_soc",
      "sensor.immax_ev_charger_current_a",
      "sensor.immax_ev_charger_current_b",
      "sensor.immax_ev_charger_current_c",
      "sensor.immax_ev_charger_voltage_a",
      "sensor.immax_ev_charger_voltage_b",
      "sensor.immax_ev_charger_voltage_c",
    ]);
    const statisticsIds = entityIds.filter((entityId) => statisticsEligible.has(entityId));
    const statisticsMap = await loadStatistics(statisticsIds, activeRange.start, historyEnd);
    const rawEntityIds = entityIds.filter(
      (entityId) => !statisticsMap.get(entityId)?.length,
    );
    let history = [];
    if (historyEnd > activeRange.start && rawEntityIds.length) {
      const rawHistoryStart = PAGE === "immax"
        ? Math.max(activeRange.start, historyEnd - 7 * DAY_MS)
        : activeRange.start;
      const path = (
        `/api/history/period/${encodeURIComponent(new Date(rawHistoryStart).toISOString())}`
        + `?end_time=${encodeURIComponent(new Date(historyEnd).toISOString())}`
        + `&filter_entity_id=${encodeURIComponent(rawEntityIds.join(","))}`
        + "&minimal_response&no_attributes"
      );
      history = await haFetch(path);
    }
    const historyMap = normalizeHistory(history);
    cachedHistoryMap = historyMap;
    cachedStatisticsMap = statisticsMap;
    if (PAGE === "charging") {
      renderChargingCharts(historyMap, statisticsMap, activeRange);
    } else {
      renderImmaxCharts(historyMap, statisticsMap, activeRange);
    }
    lastHistoryLoad = Date.now();
  } catch (error) {
    console.error(error);
    setStatus(t("loadError", { error: error.message }), true);
    mainChart.setData([], activeRange);
    secondaryChart.setData([], activeRange);
  } finally {
    historyLoading = false;
  }
}

async function loadStatistics(entityIds, start, end) {
  const result = new Map();
  if (!entityIds.length || end <= start) return result;
  const hass = await getParentHass();
  if (!hass?.callWS) return result;
  try {
    const duration = end - start;
    const period = duration > 14 * DAY_MS ? "hour" : "5minute";
    const response = await hass.callWS({
      type: "recorder/statistics_during_period",
      start_time: new Date(start).toISOString(),
      end_time: new Date(end).toISOString(),
      statistic_ids: entityIds,
      period,
      types: ["mean", "state"],
    });
    for (const entityId of entityIds) {
      result.set(entityId, response?.[entityId] || []);
    }
  } catch (error) {
    console.debug("Aggregated statistics are unavailable; using state history", error);
  }
  return result;
}

function renderChargingCharts(historyMap, statisticsMap, range) {
  const priceEntity = "sensor.renault_zoe_new_nord_pool_price";
  const powerEntity = "sensor.zoe_active_charging_power";
  const batteryEntity = "sensor.battery";
  const historicalPrice = pointsFor(
    historyMap,
    statisticsMap,
    priceEntity,
    (value) => toCents(priceEntity, value),
  );
  const forecastPrice = priceForecastPoints(range);
  const price = mergePoints(historicalPrice, forecastPrice);
  const maxPrice = toNumber(stateFor("input_number.zoe_max_energy_price")?.state);
  const power = pointsFor(
    historyMap,
    statisticsMap,
    powerEntity,
    (value) => toKw(powerEntity, value),
  );
  const battery = pointsFor(historyMap, statisticsMap, batteryEntity);
  mainChart.setData([
    { id: "price", name: language === "lv" ? "Nord Pool cena" : "Nord Pool price", points: price, color: cssColor("--accent"), unit: "c/kWh", axis: "left", step: true, maximumGap: 2 * 3600000 },
    { id: "price-cap", name: language === "lv" ? "Maks. cena" : "Max price", points: constantPoints(maxPrice, range), color: cssColor("--red"), unit: "c/kWh", axis: "left", width: 2.5, maximumGap: Number.POSITIVE_INFINITY },
    { id: "zoe-power", name: language === "lv" ? "ZOE jauda" : "ZOE power", points: power, color: cssColor("--orange"), unit: "kW", axis: "right" },
  ], range, { left: {}, right: { min: 0 } });
  secondaryChart.setData([
    { id: "battery", name: language === "lv" ? "Baterija" : "Battery", points: battery, color: cssColor("--green"), unit: "%", axis: "left" },
    { id: "zoe-power", name: language === "lv" ? "Uzlādes jauda" : "Charging power", points: power, color: cssColor("--orange"), unit: "kW", axis: "right" },
  ], range, { left: { min: 0, max: 100 }, right: { min: 0 } });
}

function renderImmaxCharts(historyMap, statisticsMap, range) {
  renderChartHeadings();
  if (immaxUsesNordPoolChart()) {
    const priceEntity = "sensor.renault_zoe_new_nord_pool_price";
    const historicalPrice = pointsFor(
      historyMap,
      statisticsMap,
      priceEntity,
      (value) => toCents(priceEntity, value),
    );
    const price = mergePoints(historicalPrice, priceForecastPoints(range));
    const maxPrice = toNumber(
      stateFor("input_number.immax_max_energy_price")?.state,
    );
    mainChart.setData([
      {
        id: "immax-price",
        name: language === "lv" ? "Nord Pool cena" : "Nord Pool price",
        points: price,
        color: cssColor("--accent"),
        unit: "c/kWh",
        axis: "left",
        step: true,
        maximumGap: 2 * 3600000,
      },
      {
        id: "immax-price-cap",
        name: language === "lv" ? "Cenas setpoints" : "Price setpoint",
        points: constantPoints(maxPrice, range),
        color: cssColor("--red"),
        unit: "c/kWh",
        axis: "left",
        width: 2.5,
        maximumGap: Number.POSITIVE_INFINITY,
      },
    ], range, { left: {} });
  } else {
    const solarEntity = "sensor.renault_zoe_new_immax_solar_production";
    const chargerEntity = "sensor.renault_zoe_new_immax_solar_charger_power";
    const loadEntity = "sensor.renault_zoe_new_immax_total_site_load";
    const socEntity = "sensor.unibms_soc";
    const powerTransform = (entityId) => (value) => toKw(entityId, value);
    mainChart.setData([
      { id: "solar", name: language === "lv" ? "Saule" : "Solar", points: pointsFor(historyMap, statisticsMap, solarEntity, powerTransform(solarEntity)), color: "#e3a516", unit: "kW", axis: "left" },
      { id: "immax-power", name: "IMMAX", points: pointsFor(historyMap, statisticsMap, chargerEntity, powerTransform(chargerEntity)), color: cssColor("--orange"), unit: "kW", axis: "left" },
      { id: "total-load", name: language === "lv" ? "Kopējā slodze" : "Total load", points: pointsFor(historyMap, statisticsMap, loadEntity, powerTransform(loadEntity)), color: cssColor("--blue"), unit: "kW", axis: "left" },
      { id: "site-soc", name: language === "lv" ? "Baterijas SOC" : "Battery SOC", points: pointsFor(historyMap, statisticsMap, socEntity), color: cssColor("--green"), unit: "%", axis: "right" },
    ], range, { left: { min: 0 }, right: { min: 0, max: 100 } });
  }

  const phaseColors = ["#2878b5", "#c96b16", "#27834a"];
  const phaseNames = language === "lv" ? ["Fāze A", "Fāze B", "Fāze C"] : ["Phase A", "Phase B", "Phase C"];
  const currentSeries = ["a", "b", "c"].map((phase, index) => ({
    id: `current-${phase}`,
    name: `${phaseNames[index]} ${t("current")}`,
    points: pointsFor(historyMap, statisticsMap, `sensor.immax_ev_charger_current_${phase}`),
    color: phaseColors[index],
    unit: "A",
    axis: "left",
  }));
  const voltageSeries = ["a", "b", "c"].map((phase, index) => ({
    id: `voltage-${phase}`,
    name: `${phaseNames[index]} ${t("voltage")}`,
    points: pointsFor(historyMap, statisticsMap, `sensor.immax_ev_charger_voltage_${phase}`),
    color: phaseColors[index],
    unit: "V",
    axis: "right",
    width: 1.2,
  }));
  secondaryChart.setData(
    [...currentSeries, ...voltageSeries],
    range,
    { left: { min: 0 }, right: { min: 0 } },
  );
}

function sessionEntity() {
  return [
    "sensor.zoe_charge_sessions_31d_raw",
    "sensor.zoe_charge_sessions_31d",
    "sensor.zoe_charge_sessions_history",
    "sensor.zoe_charge_sessions_history_raw",
  ].map(stateFor).find((state) => Array.isArray(state?.attributes?.sessions));
}

function formatSessionDate(value, includeDate = true) {
  const time = new Date(value);
  if (!Number.isFinite(time.getTime())) return "-";
  return new Intl.DateTimeFormat(language === "lv" ? "lv-LV" : "en-GB", {
    ...(includeDate ? { day: "2-digit", month: "2-digit" } : {}),
    hour: "2-digit",
    minute: "2-digit",
  }).format(time);
}

function sessionStationLabel(session) {
  if (session.station_name) return session.station_name;
  if (["home_nord_pool", "legacy_nord_pool"].includes(session.price_source)) {
    return t("homeNordPool");
  }
  return "-";
}

function sessionPriceSourceLabel(session) {
  if (session.price_source === "elektrum_drive") return t("elektrumDrive");
  if (session.price_source === "elektrum_drive_app") return t("elektrumDriveApp");
  if (session.price_source === "mobilly") return t("mobilly");
  if (session.price_source === "ignitis_on_app") return t("ignitisOnApp");
  if (session.price_source === "ikrautas_app") return t("ikrautasApp");
  if (["home_nord_pool", "legacy_nord_pool"].includes(session.price_source)) {
    return t("homeNordPool");
  }
  return session.price_source || "-";
}

function renderSessions() {
  const state = sessionEntity();
  const monthStart = new Date();
  monthStart.setDate(1);
  monthStart.setHours(0, 0, 0, 0);
  const sessions = (state?.attributes?.sessions || [])
    .filter((session) => new Date(session.end || session.start).getTime() >= monthStart.getTime())
    .sort((left, right) => new Date(right.start) - new Date(left.start));
  if (!sessions.length) {
    detailContentEl.innerHTML = `<div class="empty">${escapeHtml(t("noSessions"))}</div>`;
    return;
  }
  let totalBattery = 0;
  let totalGrid = 0;
  let totalCost = 0;
  let allGridExact = true;
  let allCostExact = true;
  const rows = sessions.map((session) => {
    const battery = toNumber(session.estimated_battery_energy_kwh) || 0;
    const grid = toNumber(session.grid_energy_kwh);
    const cost = toNumber(session.total_cost_eur);
    const station = sessionStationLabel(session);
    const connector = session.connector_code || "";
    const priceSource = sessionPriceSourceLabel(session);
    const exactEnergy = session.provider_reported_energy === true
      || session.energy_source === "provider_meter";
    const exactCost = session.provider_reported_cost === true;
    const exactRate = exactEnergy && exactCost;
    const sourceNote = exactRate ? t("operatorExact") : t("calculatedFallback");
    totalBattery += battery;
    if (Number.isFinite(grid)) {
      totalGrid += grid;
      allGridExact = allGridExact && exactEnergy;
    }
    if (Number.isFinite(cost)) {
      totalCost += cost;
      allCostExact = allCostExact && exactRate;
    }
    const gridMark = exactEnergy ? "" : "~";
    const priceMark = exactRate ? "" : "~";
    return `
      <tr>
        <td>${escapeHtml(formatSessionDate(session.start))}<br>${escapeHtml(formatSessionDate(session.end, false))}</td>
        <td>${escapeHtml(station)}${connector ? `<span class="cell-note">${escapeHtml(connector)}</span>` : ""}</td>
        <td>${escapeHtml(Math.round(toNumber(session.duration_min) || 0))} min</td>
        <td>${escapeHtml(toNumber(session.start_soc) ?? "-")} → ${escapeHtml(toNumber(session.end_soc) ?? "-")}%</td>
        <td>~${battery.toFixed(2)} kWh</td>
        <td>${Number.isFinite(grid) ? `${gridMark}${grid.toFixed(2)} kWh` : "-"}</td>
        <td>${Number.isFinite(toNumber(session.total_rate_c_per_kwh)) ? `${priceMark}${toNumber(session.total_rate_c_per_kwh).toFixed(2)} c/kWh` : "-"}<span class="cell-note">${escapeHtml(priceSource)} · ${escapeHtml(sourceNote)}</span></td>
        <td><strong>${Number.isFinite(cost) ? `${priceMark}${cost.toFixed(2)} EUR` : "-"}</strong></td>
        <td>${escapeHtml(session.status || "-")}</td>
      </tr>`;
  }).join("");
  const totalRate = totalGrid > 0 ? totalCost / totalGrid * 100 : 0;
  detailContentEl.innerHTML = `
    <div class="table-scroll">
      <table>
        <thead><tr>
          <th>${escapeHtml(t("startEnd"))}</th>
          <th>${escapeHtml(t("station"))}</th>
          <th>${escapeHtml(t("duration"))}</th>
          <th>SOC</th>
          <th>${escapeHtml(t("batteryEnergy"))}</th>
          <th>${escapeHtml(t("gridEnergy"))}</th>
          <th>${escapeHtml(t("priceDelivery"))}</th>
          <th>${escapeHtml(t("cost"))}</th>
          <th>${escapeHtml(t("status"))}</th>
        </tr></thead>
        <tbody>${rows}</tbody>
        <tfoot><tr>
          <td><strong>${escapeHtml(t("total"))}</strong></td>
          <td></td><td></td><td></td>
          <td><strong>~${totalBattery.toFixed(2)} kWh</strong></td>
          <td><strong>${allGridExact ? "" : "~"}${totalGrid.toFixed(2)} kWh</strong></td>
          <td><strong>${allCostExact ? "" : "~"}${totalRate.toFixed(2)} c/kWh</strong></td>
          <td><strong>${allCostExact ? "" : "~"}${totalCost.toFixed(2)} EUR</strong></td>
          <td></td>
        </tr></tfoot>
      </table>
    </div>`;
}

function renderImmaxFreshness() {
  const entities = [
    ["sensor.renault_zoe_new_immax_solar_production", "solarProduction"],
    ["sensor.renault_zoe_new_immax_solar_charger_power", "chargingPower"],
    ["sensor.renault_zoe_new_immax_total_site_load", "totalLoad"],
    ["sensor.unibms_soc", "siteBatterySoc"],
    ["sensor.immax_ev_charger_energy", "chargerEnergy"],
    ["sensor.immax_ev_charger_current_a", "phaseA"],
    ["sensor.immax_ev_charger_current_b", "phaseB"],
    ["sensor.immax_ev_charger_current_c", "phaseC"],
  ];
  detailContentEl.innerHTML = `
    <div class="history-list">
      ${entities.map(([entityId, label]) => {
        const state = stateFor(entityId);
        const time = stateTime(state);
        const changed = time
          ? new Intl.DateTimeFormat(language === "lv" ? "lv-LV" : "en-GB", {
            dateStyle: "short",
            timeStyle: "medium",
          }).format(time)
          : t("unavailable");
        return `
          <button class="history-item" type="button" data-history-entity="${escapeHtml(entityId)}">
            <strong>${escapeHtml(t(label))}: ${escapeHtml(displayState(state))}</strong>
            <span>${escapeHtml(changed)}</span>
          </button>`;
      }).join("")}
    </div>`;
  for (const button of detailContentEl.querySelectorAll("[data-history-entity]")) {
    button.addEventListener("click", () => showMoreInfo(button.dataset.historyEntity));
  }
}

function renderDetail() {
  if (PAGE === "charging") renderSessions();
  else renderImmaxFreshness();
}

function applyConfiguredLanguage() {
  const configured = stateFor(
    "sensor.renault_zoe_new_cost_settings",
  )?.attributes?.dashboard_language;
  const nextLanguage = configured === "en" ? "en" : "lv";
  if (nextLanguage === language) return;
  language = nextLanguage;
  applyLanguage();
}

async function loadCurrent(silent = false) {
  if (loading) return;
  if (
    silent
    && document.activeElement
    && ["INPUT", "SELECT"].includes(document.activeElement.tagName)
  ) return;
  loading = true;
  if (!silent) setStatus(t("loading"));
  try {
    const hass = await getParentHass();
    if (hass?.states) {
      currentStates = hass.states;
    } else {
      const states = await haFetch("/api/states");
      currentStates = Object.fromEntries(states.map((state) => [state.entity_id, state]));
    }
    if (PAGE === "charging") {
      const liveSessions = await haFetch(
        "/api/states/sensor.zoe_charge_sessions_31d_raw",
      );
      currentStates = {
        ...currentStates,
        [liveSessions.entity_id]: liveSessions,
      };
    }
    applyConfiguredLanguage();
    renderMetrics();
    renderActions();
    renderPanels();
    renderDetail();
    renderChartHeadings();
    if (PAGE === "immax" && activeRange) {
      renderImmaxCharts(
        cachedHistoryMap,
        cachedStatisticsMap,
        activeRange,
      );
    }
    const time = new Intl.DateTimeFormat(language === "lv" ? "lv-LV" : "en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date());
    if (PAGE === "immax" && !immaxControlAvailable()) {
      setStatus(t("chargerOfflineCommand"), true);
    } else {
      setStatus(t("updated", { time }));
    }
  } catch (error) {
    console.error(error);
    setStatus(t("loadError", { error: error.message }), true);
  } finally {
    loading = false;
  }
}

async function reloadAll() {
  reloadEl.disabled = true;
  try {
    await loadCurrent();
    await loadHistory();
  } finally {
    reloadEl.disabled = false;
  }
}

function navigateSettings(event) {
  if (window.parent === window) return;
  event.preventDefault();
  const path = event.currentTarget.getAttribute("href");
  window.parent.history.pushState(null, "", path);
  window.parent.dispatchEvent(new window.parent.Event("location-changed"));
}

titleIconEl.innerHTML = pageConfig.icon;
if (PAGE === "immax") periodEl.value = "24h";
settingsEl.href = "/config/integrations/integration/zoe_new_extended";
settingsEl.target = "_top";
entitySettingsEl.href = "/config/integrations/integration/zoe_new_extended";
entitySettingsEl.target = "_top";
entitySettingsEl.hidden = PAGE !== "immax";
document.querySelectorAll("a.settings-link").forEach((link) => {
  link.addEventListener("click", navigateSettings);
});
dayDateEl.max = localDateValue(new Date());
applyLanguage();

periodEl.addEventListener("change", () => {
  dayDateEl.value = "";
  clearDateEl.hidden = true;
  loadHistory();
});
dayDateEl.addEventListener("change", () => {
  clearDateEl.hidden = !dayDateEl.value;
  if (dayDateEl.value) loadHistory();
});
clearDateEl.addEventListener("click", () => {
  dayDateEl.value = "";
  clearDateEl.hidden = true;
  loadHistory();
});
reloadEl.addEventListener("click", reloadAll);

window.setInterval(() => {
  if (!document.hidden) loadCurrent(true);
}, REFRESH_CURRENT_MS);
window.setInterval(() => {
  if (!document.hidden && Date.now() - lastHistoryLoad >= REFRESH_HISTORY_MS) {
    loadHistory();
  }
}, 60000);

reloadAll();
