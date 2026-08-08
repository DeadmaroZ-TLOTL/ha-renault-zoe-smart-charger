"use strict";

(() => {
  const SETTINGS_ENTITY = "sensor.renault_zoe_new_cost_settings";
  const VIEW_LABELS = {
    "renault-zoe": { en: "Charging", lv: "Uzlāde" },
    default: { en: "Trips", lv: "Braucieni" },
    mileage: { en: "Mileage", lv: "Nobraukums" },
    cenas: { en: "Costs", lv: "Cenas" },
    info: { en: "Info", lv: "Info" },
    stations: { en: "Stations", lv: "Stacijas" },
    immax: { en: "IMMAX", lv: "IMMAX" },
  };
  const KNOWN_LABELS = new Set(
    Object.values(VIEW_LABELS).flatMap((labels) => Object.values(labels)),
  );
  let lastRedirect = "";

  function parentHass() {
    try {
      return window.parent?.document?.querySelector("home-assistant")?.hass
        || window.parent?.document?.querySelector("hc-main")?.hass
        || null;
    } catch (_error) {
      return null;
    }
  }

  function allRoots(root) {
    const roots = [root];
    for (let index = 0; index < roots.length; index += 1) {
      for (const element of roots[index].querySelectorAll("*")) {
        if (element.shadowRoot) roots.push(element.shadowRoot);
      }
    }
    return roots;
  }

  function viewPath(element) {
    const anchor = element.matches?.("a[href]")
      ? element
      : element.querySelector?.("a[href]");
    const href = anchor?.getAttribute("href") || element.getAttribute?.("href") || "";
    const match = href.match(/\/renault-trips\/([^/?#]+)/);
    if (match) return match[1];

    const text = element.textContent?.trim() || "";
    return Object.entries(VIEW_LABELS).find(([, labels]) => (
      Object.values(labels).includes(text)
    ))?.[0] || "";
  }

  function tabContainer(element) {
    let current = element;
    while (current) {
      if (
        current.matches?.('[role="tab"], ha-tab, mwc-tab')
        || current.tagName?.toLowerCase() === "a"
      ) {
        return current;
      }
      const root = current.getRootNode?.();
      current = current.parentElement || root?.host || null;
    }
    return element;
  }

  function replaceLabel(element, label) {
    const ownerDocument = element.ownerDocument || document;
    const walker = ownerDocument.createTreeWalker(
      element,
      NodeFilter.SHOW_TEXT,
    );
    let node = walker.nextNode();
    while (node) {
      const value = node.nodeValue?.trim() || "";
      if (KNOWN_LABELS.has(value)) {
        node.nodeValue = node.nodeValue.replace(value, label);
        return;
      }
      node = walker.nextNode();
    }
  }

  function updateTabs() {
    if (window.parent === window) return;
    const hass = parentHass();
    if (!hass) return;

    const settings = hass.states?.[SETTINGS_ENTITY]?.attributes || {};
    const language = settings.dashboard_language === "en" ? "en" : "lv";
    const immaxEnabled = settings.immax_feature_enabled !== false
      && settings.immax_feature_enabled !== "false";
    const seen = new Set();

    for (const root of allRoots(window.parent.document)) {
      for (const element of root.querySelectorAll(
        '[role="tab"], ha-tab, mwc-tab, a[href*="/renault-trips/"]',
      )) {
        const path = viewPath(element);
        if (!VIEW_LABELS[path]) continue;
        const tab = tabContainer(element);
        if (seen.has(tab)) continue;
        seen.add(tab);

        replaceLabel(tab, VIEW_LABELS[path][language]);
        if (path === "immax") {
          tab.hidden = !immaxEnabled;
          tab.style.display = immaxEnabled ? "" : "none";
          tab.setAttribute("aria-hidden", String(!immaxEnabled));
        }
      }
    }

    const currentPath = window.parent.location.pathname;
    if (
      !immaxEnabled
      && currentPath.endsWith("/renault-trips/immax")
      && lastRedirect !== currentPath
    ) {
      lastRedirect = currentPath;
      window.parent.history.replaceState(null, "", "/renault-trips/info");
      window.parent.dispatchEvent(new window.parent.Event("location-changed"));
    }
  }

  updateTabs();
  window.setInterval(updateTabs, 2000);
})();
