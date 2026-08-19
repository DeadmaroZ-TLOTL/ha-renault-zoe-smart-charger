(function () {
  "use strict";

  const STORAGE_KEY = "renault-trips-date-range-v1";

  function localDateValue(date) {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  }

  function readSelection(fallbackPreset) {
    try {
      const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null");
      if (saved && typeof saved === "object") {
        return {
          preset: String(saved.preset || fallbackPreset),
          startDate: /^\d{4}-\d{2}-\d{2}$/.test(saved.startDate || "")
            ? saved.startDate
            : "",
          endDate: /^\d{4}-\d{2}-\d{2}$/.test(saved.endDate || "")
            ? saved.endDate
            : "",
        };
      }
    } catch {
      // Ignore a malformed value left by an older dashboard release.
    }
    return { preset: fallbackPreset, startDate: "", endDate: "" };
  }

  function attach(options) {
    const periodEl = options.periodEl;
    const startEl = options.startEl;
    const endEl = options.endEl;
    const clearEl = options.clearEl;
    const fallbackPreset = String(options.defaultPreset || periodEl.value || "7");
    const onChange = typeof options.onChange === "function"
      ? options.onChange
      : function () {};
    let language = options.language === "en" ? "en" : "lv";

    const maxDate = localDateValue(new Date());
    startEl.max = maxDate;
    endEl.max = maxDate;

    function supportedPreset(value) {
      return Array.from(periodEl.options).some((option) => option.value === value);
    }

    function writeSelection() {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
        preset: periodEl.value,
        startDate: startEl.value,
        endDate: endEl.value,
      }));
    }

    function syncVisualState() {
      const custom = Boolean(startEl.value || endEl.value);
      periodEl.disabled = custom;
      startEl.classList.toggle("active", custom);
      endEl.classList.toggle("active", custom);
      clearEl.hidden = !custom;
    }

    function applySelection(selection) {
      periodEl.value = supportedPreset(selection.preset)
        ? selection.preset
        : fallbackPreset;
      startEl.value = selection.startDate || "";
      endEl.value = selection.endDate || "";
      if (startEl.value && !endEl.value) endEl.value = startEl.value;
      if (endEl.value && !startEl.value) startEl.value = endEl.value;
      if (startEl.value > endEl.value) endEl.value = startEl.value;
      syncVisualState();
    }

    function normalizeCustom(changedElement) {
      if (startEl.value && !endEl.value) endEl.value = startEl.value;
      if (endEl.value && !startEl.value) startEl.value = endEl.value;
      if (startEl.value && endEl.value && startEl.value > endEl.value) {
        if (changedElement === startEl) endEl.value = startEl.value;
        else startEl.value = endEl.value;
      }
    }

    function clearSelection() {
      if (!startEl.value && !endEl.value) return;
      startEl.value = "";
      endEl.value = "";
      syncVisualState();
      writeSelection();
      onChange();
    }

    function range(now = new Date(), allStart = 0) {
      if (startEl.value && endEl.value) {
        const start = new Date(`${startEl.value}T00:00:00`);
        const end = new Date(`${endEl.value}T00:00:00`);
        end.setDate(end.getDate() + 1);
        return { start: start.getTime(), end: end.getTime(), custom: true };
      }
      if (periodEl.value === "all") {
        return { start: allStart, end: now.getTime(), custom: false };
      }
      if (periodEl.value === "current_month") {
        const start = new Date(now.getFullYear(), now.getMonth(), 1);
        const end = new Date(now);
        end.setHours(0, 0, 0, 0);
        end.setDate(end.getDate() + 1);
        return { start: start.getTime(), end: end.getTime(), custom: false };
      }
      const days = Math.max(1, Number(periodEl.value) || 7);
      const start = new Date(now);
      start.setHours(0, 0, 0, 0);
      start.setDate(start.getDate() - (days - 1));
      const end = new Date(now);
      end.setHours(0, 0, 0, 0);
      end.setDate(end.getDate() + 1);
      return { start: start.getTime(), end: end.getTime(), custom: false };
    }

    function setLanguage(nextLanguage) {
      language = nextLanguage === "en" ? "en" : "lv";
      const text = language === "en"
        ? { start: "From date", end: "To date", clear: "Clear date range" }
        : { start: "No datuma", end: "Līdz datumam", clear: "Notīrīt datumu periodu" };
      startEl.title = text.start;
      startEl.setAttribute("aria-label", text.start);
      endEl.title = text.end;
      endEl.setAttribute("aria-label", text.end);
      clearEl.title = text.clear;
      clearEl.setAttribute("aria-label", text.clear);
      document.querySelectorAll("[data-range-label=start]").forEach((element) => {
        element.textContent = language === "en" ? "From" : "No";
      });
      document.querySelectorAll("[data-range-label=end]").forEach((element) => {
        element.textContent = language === "en" ? "To" : "Līdz";
      });
    }

    applySelection(readSelection(fallbackPreset));
    setLanguage(language);

    periodEl.addEventListener("change", () => {
      startEl.value = "";
      endEl.value = "";
      syncVisualState();
      writeSelection();
      onChange();
    });
    for (const input of [startEl, endEl]) {
      input.addEventListener("change", () => {
        normalizeCustom(input);
        syncVisualState();
        writeSelection();
        onChange();
      });
    }
    clearEl.addEventListener("pointerdown", (event) => {
      if (event.button === 0) clearSelection();
    });
    clearEl.addEventListener("click", clearSelection);
    window.addEventListener("storage", (event) => {
      if (event.key !== STORAGE_KEY) return;
      applySelection(readSelection(fallbackPreset));
      onChange();
    });

    return {
      range,
      clear: clearSelection,
      setLanguage,
      sync: syncVisualState,
      get selection() {
        return {
          preset: periodEl.value,
          startDate: startEl.value,
          endDate: endEl.value,
        };
      },
    };
  }

  window.RenaultDateRange = { attach, localDateValue, storageKey: STORAGE_KEY };
})();
