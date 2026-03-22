(function () {
  "use strict";

  const LOCALE_STORAGE_KEY = "appLocale";

  function readStoredLocale() {
    const T = window.APP_I18N || {};
    const raw = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (raw && T[raw]) return raw;
    const nav = (navigator.language || "fr").slice(0, 2).toLowerCase();
    if (T[nav]) return nav;
    return "fr";
  }

  let locale = readStoredLocale();
  document.documentElement.lang = locale;

  function t(key, params) {
    const T = window.APP_I18N || {};
    const table = T[locale] || T.fr || {};
    let s = table[key] ?? T.fr?.[key] ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        s = s.split(`{${k}}`).join(String(v));
      }
    }
    return s;
  }

  function apiFetch(input, init = {}) {
    const opt = { ...init };
    opt.headers = new Headers(init.headers || {});
    opt.headers.set("X-App-Locale", locale);
    if (typeof window.getAppClientId === "function") {
      opt.headers.set("X-Client-Id", window.getAppClientId());
    }
    return fetch(input, opt);
  }

  function normalizePath(p) {
    if (p == null || p === "") return "/";
    const s = String(p).replace(/\/$/, "") || "/";
    return s;
  }

  /**
   * Sauf si force=true : ne pas renvoyer quelqu'un de /meteo vers / via init/GET
   * (sinon activeRoute serveur "/" expulse tout le monde de la température en boucle).
   * nav_updated (autre client) utilise force=true.
   */
  function followNavIfNeeded(activeRoute, opts) {
    const force = opts && opts.force === true;
    const cur = normalizePath(window.location.pathname);
    const target = normalizePath(activeRoute);
    if (cur === target) return;
    if (!force && cur === "/meteo" && target === "/") return;
    window.location.assign(activeRoute);
  }

  function wireNavLinks() {
    document.querySelectorAll("a[data-sync-nav]").forEach((a) => {
      a.addEventListener("click", async (e) => {
        e.preventDefault();
        const route = a.getAttribute("data-sync-nav");
        try {
          await apiFetch("/api/nav", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ activeRoute: route }),
          });
        } catch (_) {}
        window.location.assign(route);
      });
    });
  }

  let lastChartPayload = null;

  function updateLangButtons() {
    document.querySelectorAll("[data-set-lang]").forEach((btn) => {
      const on = btn.getAttribute("data-set-lang") === locale;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", String(on));
    });
  }

  const geoQuery = document.getElementById("geoQuery");
  const btnGeoSearch = document.getElementById("btnGeoSearch");
  const geoResults = document.getElementById("geoResults");
  const selectedPlaceLabel = document.getElementById("selectedPlaceLabel");
  const dateStart = document.getElementById("dateStart");
  const dateEnd = document.getElementById("dateEnd");
  const resSelect = document.getElementById("resSelect");
  const btnLoadChart = document.getElementById("btnLoadChart");
  const tempPlot = document.getElementById("tempPlot");
  const tempPlotHint = document.getElementById("tempPlotHint");
  const tempError = document.getElementById("tempError");
  const tempWarn = document.getElementById("tempWarn");

  let selectedPlace = null;
  let geoHits = [];
  const MAX_HOURLY_WARN_DAYS = 31;

  const plotlyConfig = {
    responsive: true,
    scrollZoom: true,
    displayModeBar: true,
    displaylogo: false,
    showAxisDragHandles: true,
    showAxisRangeEntryBoxes: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
  };

  function plotlyBaseLayout(titleText) {
    return {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "#0f1419",
      font: { color: "#e7ecf3", family: "Outfit, system-ui, sans-serif", size: 12 },
      title: { text: titleText, font: { size: 15 } },
      xaxis: {
        type: "date",
        gridcolor: "#2d3a4d",
        zerolinecolor: "#2d3a4d",
        linecolor: "#2d3a4d",
        tickfont: { color: "#8b9cb3" },
      },
      yaxis: {
        title: t("yAxisC"),
        gridcolor: "#2d3a4d",
        zerolinecolor: "#2d3a4d",
        linecolor: "#2d3a4d",
        tickfont: { color: "#8b9cb3" },
      },
      legend: {
        font: { color: "#8b9cb3" },
        bgcolor: "rgba(0,0,0,0)",
      },
      margin: { t: 56, r: 24, b: 72, l: 56 },
      hovermode: "x unified",
      dragmode: "zoom",
    };
  }

  function buildPlotlyFigure(res, data, placeLabel) {
    const titleText = t("plotTitle", { label: placeLabel });
    if (res === "hour") {
      const times = data.hourly?.time || [];
      const temps = data.hourly?.temperature_2m || [];
      const traces = [
        {
          x: times,
          y: temps,
          type: "scatter",
          mode: "lines",
          name: t("traceTemp"),
          line: { color: "#3d9cf5", width: 2, shape: "spline" },
          fill: "tozeroy",
          fillcolor: "rgba(61, 156, 245, 0.12)",
          hovertemplate: t("hoverHour"),
        },
      ];
      return { traces, layout: plotlyBaseLayout(titleText) };
    }
    const times = data.daily?.time || [];
    const tmax = data.daily?.temperature_2m_max || [];
    const tmin = data.daily?.temperature_2m_min || [];
    const traces = [
      {
        x: times,
        y: tmax,
        type: "scatter",
        mode: "lines+markers",
        name: t("traceMax"),
        line: { color: "#f87171", width: 2, shape: "spline" },
        marker: { size: 5, color: "#f87171" },
        hovertemplate: t("hoverMaxLine"),
      },
      {
        x: times,
        y: tmin,
        type: "scatter",
        mode: "lines+markers",
        name: t("traceMin"),
        line: { color: "#3d9cf5", width: 2, shape: "spline" },
        marker: { size: 5, color: "#3d9cf5" },
        hovertemplate: t("hoverMinLine"),
      },
    ];
    return { traces, layout: plotlyBaseLayout(titleText) };
  }

  async function redrawPlotFromCache() {
    if (!lastChartPayload || typeof Plotly === "undefined") return;
    const { res, data, placeLabel } = lastChartPayload;
    const { traces, layout } = buildPlotlyFigure(res, data, placeLabel);
    if (tempPlot.querySelector(".js-plotly-plot")) {
      await Plotly.react(tempPlot, traces, layout, plotlyConfig);
    }
  }

  function applyLocale() {
    document.documentElement.lang = locale;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
    });
    document.querySelectorAll("[data-i18n-aria-label]").forEach((el) => {
      el.setAttribute("aria-label", t(el.getAttribute("data-i18n-aria-label")));
    });
    const g = document.getElementById("langSwitchGroup");
    if (g) g.setAttribute("aria-label", t("langGroupAria"));
    const langAria = { de: "langDE", fr: "langFR", it: "langIT", en: "langEN" };
    document.querySelectorAll("[data-set-lang]").forEach((btn) => {
      const code = btn.getAttribute("data-set-lang");
      btn.setAttribute("aria-label", t(langAria[code] || "langEN"));
    });
    const navEl = document.getElementById("appNav");
    if (navEl) navEl.setAttribute("aria-label", t("tablistAria"));
    const tc = document.getElementById("tempControls");
    if (tc) tc.setAttribute("aria-label", t("tempSectionAria"));
    const oh = resSelect.querySelector('option[value="hour"]');
    if (oh) oh.textContent = t("resHour");
    const od = resSelect.querySelector('option[value="day"]');
    if (od) od.textContent = t("resDay");
    if (tempPlotHint) tempPlotHint.textContent = t("tempPlotHint");
    tempPlot.setAttribute("aria-label", t("tempPlotAria"));
    const hintEl = document.getElementById("tempHintPara");
    if (hintEl) {
      hintEl.innerHTML = `${escapeHtml(t("tempHint1"))} <a href="https://open-meteo.com" target="_blank" rel="noopener noreferrer" style="color: var(--accent);">Open-Meteo</a>. ${escapeHtml(t("tempHint2"))}`;
    }
    updateLangButtons();
    document.title = t("appTitle");
    if (typeof window.refreshControlLabels === "function") window.refreshControlLabels();
    if (typeof Plotly !== "undefined" && lastChartPayload && tempPlot.querySelector(".js-plotly-plot")) {
      redrawPlotFromCache();
    }
  }

  function setLanguage(code) {
    if (!window.APP_I18N?.[code]) return;
    locale = code;
    localStorage.setItem(LOCALE_STORAGE_KEY, code);
    applyLocale();
  }

  document.querySelectorAll("[data-set-lang]").forEach((btn) => {
    btn.addEventListener("click", () => setLanguage(btn.getAttribute("data-set-lang")));
  });

  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${proto}//${window.location.host}/ws`;
  let ws;

  const appVersionEl = document.getElementById("appVersion");
  const btnAbout = document.getElementById("btnAbout");
  const aboutDialog = document.getElementById("aboutDialog");
  const aboutBody = document.getElementById("aboutBody");
  const aboutClose = document.getElementById("aboutClose");

  async function loadAppVersion() {
    try {
      const r = await apiFetch("/api/version");
      const d = await r.json();
      appVersionEl.textContent = d.version ? `v${d.version}` : "";
    } catch {
      appVersionEl.textContent = "";
    }
  }

  function fmtAboutCell(v) {
    if (v == null || v === "") return t("aboutMissing");
    return String(v);
  }

  function renderAboutRows(data) {
    const rows = [
      [t("aboutApp"), fmtAboutCell(data.app)],
      [t("aboutFrontend"), fmtAboutCell(data.frontend)],
      [t("aboutBackendPython"), fmtAboutCell(data.backend?.python)],
      [t("aboutBackendFastapi"), fmtAboutCell(data.backend?.fastapi)],
      [t("aboutBackendUvicorn"), fmtAboutCell(data.backend?.uvicorn)],
      [
        t("aboutDocker"),
        data.docker != null && data.docker !== ""
          ? String(data.docker)
          : t("aboutDockerUnset"),
      ],
    ];
    const c = data.components || {};
    if (c.plotly) rows.push([t("aboutPlotly"), fmtAboutCell(c.plotly)]);
    if (c.open_meteo) rows.push([t("aboutOpenMeteo"), fmtAboutCell(c.open_meteo)]);
    if (c.fonts) rows.push([t("aboutFonts"), fmtAboutCell(c.fonts)]);
    aboutBody.innerHTML = rows
      .map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(v)}</td></tr>`)
      .join("");
  }

  btnAbout.addEventListener("click", async () => {
    try {
      const r = await apiFetch("/api/about");
      const d = await r.json();
      renderAboutRows(d);
      aboutDialog.showModal();
    } catch (e) {
      alert(`${t("errAboutLoad")} ${e}`);
    }
  });

  aboutClose.addEventListener("click", () => aboutDialog.close());

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function countDaysInclusive(startStr, endStr) {
    const a = new Date(`${startStr}T12:00:00`);
    const b = new Date(`${endStr}T12:00:00`);
    return Math.floor((b - a) / 86400000) + 1;
  }

  function updateSelectedPlaceLabel() {
    if (!selectedPlace) {
      selectedPlaceLabel.innerHTML = "";
      return;
    }
    selectedPlaceLabel.innerHTML = `${escapeHtml(t("selectedPlace"))} <strong>${escapeHtml(
      selectedPlace.label
    )}</strong> (${selectedPlace.lat.toFixed(4)}°, ${selectedPlace.lon.toFixed(4)}°)`;
  }

  function buildMeteoPayloadFromDom() {
    return {
      dateStart: dateStart.value,
      dateEnd: dateEnd.value,
      resolution: resSelect.value === "hour" ? "hour" : "day",
      geoQuery: geoQuery.value || "",
      place: selectedPlace
        ? { lat: selectedPlace.lat, lon: selectedPlace.lon, label: selectedPlace.label }
        : null,
    };
  }

  function normalizeMeteoPayload(raw) {
    const resolution = raw.resolution === "hour" ? "hour" : "day";
    let place = null;
    if (raw.place && typeof raw.place.lat === "number" && typeof raw.place.lon === "number") {
      place = {
        lat: raw.place.lat,
        lon: raw.place.lon,
        label: raw.place.label ?? "",
      };
    }
    return {
      dateStart: raw.dateStart ?? "",
      dateEnd: raw.dateEnd ?? "",
      resolution,
      geoQuery: raw.geoQuery ?? "",
      place,
    };
  }

  function serverMeteoIsBlank(m) {
    if (!m || typeof m !== "object") return true;
    const p = normalizeMeteoPayload(m);
    if (p.place) return false;
    if (p.dateStart && p.dateEnd) return false;
    if ((p.geoQuery || "").trim()) return false;
    return true;
  }

  function meteoStateEqualsServer(serverM) {
    const a = normalizeMeteoPayload(serverM);
    const b = normalizeMeteoPayload(buildMeteoPayloadFromDom());
    if (
      a.dateStart !== b.dateStart ||
      a.dateEnd !== b.dateEnd ||
      a.resolution !== b.resolution ||
      a.geoQuery !== b.geoQuery
    ) {
      return false;
    }
    if (!a.place && !b.place) return true;
    if (!a.place || !b.place) return false;
    return (
      a.place.lat === b.place.lat &&
      a.place.lon === b.place.lon &&
      a.place.label === b.place.label
    );
  }

  function chartNeedsInitialLoad() {
    if (typeof Plotly === "undefined") return false;
    if (!selectedPlace || !dateStart.value || !dateEnd.value) return false;
    return !tempPlot.querySelector(".js-plotly-plot");
  }

  function applyMeteoFromServer(m) {
    if (!m) return;
    const ds = m.dateStart ?? "";
    const de = m.dateEnd ?? "";
    if (ds && de) {
      dateStart.value = ds;
      dateEnd.value = de;
    } else if (ds) dateStart.value = ds;
    else if (de) dateEnd.value = de;
    resSelect.value = m.resolution === "hour" ? "hour" : "day";
    if (m.geoQuery != null) geoQuery.value = m.geoQuery;
    if (m.place && typeof m.place.lat === "number" && typeof m.place.lon === "number") {
      selectedPlace = {
        lat: m.place.lat,
        lon: m.place.lon,
        label: m.place.label || "",
      };
    } else {
      selectedPlace = null;
    }
    geoResults.hidden = true;
    geoResults.innerHTML = "";
    updateSelectedPlaceLabel();
  }

  async function maybeReloadMeteoChart() {
    if (typeof Plotly === "undefined") return;
    if (!selectedPlace || !dateStart.value || !dateEnd.value) return;
    await loadTemperatureChart();
  }

  let meteoUiPushTimer = null;
  function schedulePushMeteoUi() {
    if (meteoUiPushTimer) clearTimeout(meteoUiPushTimer);
    meteoUiPushTimer = setTimeout(async () => {
      meteoUiPushTimer = null;
      try {
        const r = await apiFetch("/api/meteo/ui", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(buildMeteoPayloadFromDom()),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          console.warn("PUT /api/meteo/ui", err.detail || r.statusText);
        }
      } catch (e) {
        console.warn("PUT /api/meteo/ui", e);
      }
    }, 400);
  }

  async function runGeoSearch() {
    tempError.textContent = "";
    const q = (geoQuery.value || "").trim();
    if (!q) {
      tempError.textContent = t("errGeoEmpty");
      return;
    }
    btnGeoSearch.disabled = true;
    try {
      const url = new URL("https://geocoding-api.open-meteo.com/v1/search");
      url.searchParams.set("name", q);
      url.searchParams.set("count", "8");
      const r = await fetch(url);
      if (!r.ok) throw new Error(t("errGeoUnavailable"));
      const data = await r.json();
      geoHits = data.results || [];
      geoResults.innerHTML = "";
      if (!geoHits.length) {
        geoResults.hidden = true;
        tempError.textContent = t("errNoPlaces");
        selectedPlace = null;
        updateSelectedPlaceLabel();
        schedulePushMeteoUi();
        return;
      }
      geoResults.hidden = false;
      geoHits.forEach((hit, i) => {
        const li = document.createElement("li");
        const b = document.createElement("button");
        b.type = "button";
        const parts = [hit.name, hit.admin1, hit.country].filter(Boolean);
        b.textContent = `${parts.join(", ")} (${hit.latitude.toFixed(2)}°, ${hit.longitude.toFixed(2)}°)`;
        b.addEventListener("click", () => selectGeoHit(i));
        li.appendChild(b);
        geoResults.appendChild(li);
      });
    } catch (e) {
      tempError.textContent = e instanceof Error ? e.message : String(e);
      geoResults.hidden = true;
    } finally {
      btnGeoSearch.disabled = false;
    }
  }

  function selectGeoHit(i) {
    const hit = geoHits[i];
    if (!hit) return;
    selectedPlace = {
      lat: hit.latitude,
      lon: hit.longitude,
      label: [hit.name, hit.country].filter(Boolean).join(", "),
    };
    geoResults.querySelectorAll("button").forEach((btn, j) => {
      btn.classList.toggle("selected", j === i);
    });
    updateSelectedPlaceLabel();
    tempError.textContent = "";
    schedulePushMeteoUi();
  }

  async function loadTemperatureChart() {
    tempError.textContent = "";
    tempWarn.hidden = true;
    tempWarn.textContent = "";

    if (typeof Plotly === "undefined") {
      tempError.textContent = t("errPlotly");
      return;
    }
    if (!selectedPlace) {
      tempError.textContent = t("errSelectPlace");
      return;
    }
    const start = dateStart.value;
    const end = dateEnd.value;
    if (!start || !end) {
      tempError.textContent = t("errDatesRequired");
      return;
    }
    if (start > end) {
      tempError.textContent = t("errDateOrder");
      return;
    }
    const res = resSelect.value;
    const dayCount = countDaysInclusive(start, end);
    if (res === "hour" && dayCount > MAX_HOURLY_WARN_DAYS) {
      tempWarn.hidden = false;
      tempWarn.textContent = t("warnHourlyRange", { days: dayCount });
    }

    btnLoadChart.disabled = true;
    try {
      const url = new URL("https://archive-api.open-meteo.com/v1/archive");
      url.searchParams.set("latitude", String(selectedPlace.lat));
      url.searchParams.set("longitude", String(selectedPlace.lon));
      url.searchParams.set("start_date", start);
      url.searchParams.set("end_date", end);
      url.searchParams.set("timezone", "auto");
      if (res === "hour") {
        url.searchParams.set("hourly", "temperature_2m");
      } else {
        url.searchParams.set("daily", "temperature_2m_max,temperature_2m_min");
      }
      const r = await fetch(url);
      if (!r.ok) throw new Error(t("errWeatherApi"));
      const data = await r.json();
      if (data.error === true) {
        throw new Error(data.reason || t("errOpenMeteoDefault"));
      }

      if (tempPlot.querySelector(".js-plotly-plot")) {
        Plotly.purge(tempPlot);
      }
      tempPlotHint.hidden = true;

      if (res === "hour") {
        const times = data.hourly?.time || [];
        if (!times.length) {
          tempError.textContent = t("errHourlyEmpty");
          return;
        }
      } else {
        const times = data.daily?.time || [];
        if (!times.length) {
          tempError.textContent = t("errDailyEmpty");
          return;
        }
      }

      const { traces, layout } = buildPlotlyFigure(res, data, selectedPlace.label);
      await Plotly.newPlot(tempPlot, traces, layout, plotlyConfig);
      lastChartPayload = {
        res,
        data,
        placeLabel: selectedPlace.label,
      };
      tempPlotHint.hidden = false;
    } catch (e) {
      tempError.textContent = e instanceof Error ? e.message : String(e);
    } finally {
      btnLoadChart.disabled = false;
    }
  }

  btnGeoSearch.addEventListener("click", runGeoSearch);
  geoQuery.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runGeoSearch();
  });
  geoQuery.addEventListener("blur", () => schedulePushMeteoUi());
  btnLoadChart.addEventListener("click", loadTemperatureChart);
  dateStart.addEventListener("change", () => schedulePushMeteoUi());
  dateEnd.addEventListener("change", () => schedulePushMeteoUi());
  resSelect.addEventListener("change", () => schedulePushMeteoUi());

  function initDefaultDates() {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 14);
    const pad = (n) => String(n).padStart(2, "0");
    const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    dateEnd.value = ymd(end);
    dateStart.value = ymd(start);
  }
  initDefaultDates();

  function connectWs() {
    ws = new WebSocket(wsUrl);
    ws.onclose = () => setTimeout(connectWs, 2000);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "init") {
        if (msg.control && typeof window.applyControlState === "function") {
          window.applyControlState(msg.control);
        }
        if (msg.activeRoute) followNavIfNeeded(msg.activeRoute);
        if (msg.meteo && !serverMeteoIsBlank(msg.meteo)) {
          const same = meteoStateEqualsServer(msg.meteo);
          if (!same) applyMeteoFromServer(msg.meteo);
          if (!same || chartNeedsInitialLoad()) void maybeReloadMeteoChart();
        }
      } else if (msg.type === "meteo_updated" && msg.meteo) {
        const same = meteoStateEqualsServer(msg.meteo);
        if (!same) applyMeteoFromServer(msg.meteo);
        if (!same || chartNeedsInitialLoad()) void maybeReloadMeteoChart();
      } else if (msg.type === "control_updated" && msg.control) {
        if (typeof window.applyControlState === "function") window.applyControlState(msg.control);
      } else if (msg.type === "nav_updated" && msg.activeRoute) {
        followNavIfNeeded(msg.activeRoute, { force: true });
      }
    };
  }

  wireNavLinks();
  (async function alignRouteFromServer() {
    try {
      const r = await apiFetch("/api/nav");
      if (r.ok) {
        const d = await r.json();
        if (d.activeRoute) followNavIfNeeded(d.activeRoute);
      }
    } catch (_) {}
  })();

  applyLocale();
  loadAppVersion();
  connectWs();
})();
