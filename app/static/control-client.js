/**
 * Contrôle exclusif : identifiant client, sync UI, modales approbation / attente.
 * Requiert locales.js. clock-page / meteo-page ajoutent X-Client-Id via getAppClientId.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "appClientId";
  const FORCE_DELAY_MS = 30000;

  let lastControl = null;
  let lastApprovePromptedPending = null;
  let forceEnableTimer = null;
  let forceHintInterval = null;
  let feedbackClearTimer = null;

  function getAppClientId() {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  }

  function tc(key) {
    const loc = document.documentElement.lang || "fr";
    const T = window.APP_I18N || {};
    const table = T[loc] || T.fr || {};
    return table[key] ?? T.fr?.[key] ?? key;
  }

  function controlApiFetch(path, options) {
    const opt = options || {};
    const headers = new Headers(opt.headers || {});
    headers.set("X-Client-Id", getAppClientId());
    headers.set("X-App-Locale", document.documentElement.lang || "fr");
    if (opt.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    return fetch(path, { ...opt, headers });
  }

  function clearForceHintInterval() {
    if (forceHintInterval) {
      clearInterval(forceHintInterval);
      forceHintInterval = null;
    }
  }

  function clearForceTimer() {
    if (forceEnableTimer) {
      clearTimeout(forceEnableTimer);
      forceEnableTimer = null;
    }
  }

  function clearAllForceDelayUi() {
    clearForceTimer();
    clearForceHintInterval();
    const dlg = document.getElementById("controlWaitDialog");
    if (dlg) delete dlg.dataset.forceDeadline;
  }

  function updateForceHintFromDeadline() {
    const dlg = document.getElementById("controlWaitDialog");
    const hint = document.getElementById("controlForceHint");
    const btnForce = document.getElementById("btnControlForce");
    if (!dlg || !hint) return;
    const raw = dlg.dataset.forceDeadline;
    if (!raw) {
      hint.textContent = "";
      return;
    }
    const deadline = Number(raw);
    const s = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
    if (btnForce && !btnForce.disabled) {
      hint.textContent = tc("controlForceReady");
      return;
    }
    hint.textContent =
      s > 0
        ? tc("controlForceCountdown").replace("{n}", String(s))
        : tc("controlForceReady");
  }

  /** À appeler quand la boîte d’attente est affichée (après showModal). */
  function armForceDelayForWaitDialog() {
    const dlg = document.getElementById("controlWaitDialog");
    const btnForce = document.getElementById("btnControlForce");
    if (!dlg || !btnForce) return;
    clearAllForceDelayUi();
    btnForce.disabled = true;
    const deadline = Date.now() + FORCE_DELAY_MS;
    dlg.dataset.forceDeadline = String(deadline);
    updateForceHintFromDeadline();
    forceHintInterval = setInterval(updateForceHintFromDeadline, 250);
    forceEnableTimer = setTimeout(() => {
      forceEnableTimer = null;
      clearForceHintInterval();
      btnForce.disabled = false;
      updateForceHintFromDeadline();
    }, FORCE_DELAY_MS);
  }

  function showControlFeedback(message) {
    const el = document.getElementById("controlFeedback");
    if (!el) return;
    el.textContent = message;
    el.removeAttribute("hidden");
    if (feedbackClearTimer) clearTimeout(feedbackClearTimer);
    feedbackClearTimer = setTimeout(() => {
      feedbackClearTimer = null;
      el.textContent = "";
      el.setAttribute("hidden", "");
    }, 12000);
  }

  function openWaitDialog() {
    const dlg = document.getElementById("controlWaitDialog");
    if (!dlg) return;
    if (typeof dlg.showModal === "function") dlg.showModal();
    armForceDelayForWaitDialog();
  }

  function closeWaitDialog() {
    const dlg = document.getElementById("controlWaitDialog");
    clearAllForceDelayUi();
    const btnForce = document.getElementById("btnControlForce");
    if (btnForce) btnForce.disabled = true;
    const hint = document.getElementById("controlForceHint");
    if (hint) hint.textContent = "";
    if (dlg && dlg.open) dlg.close();
  }

  function applyControlState(control) {
    if (!control) return;
    const prevControl = lastControl;
    lastControl = control;
    const me = getAppClientId();
    const ctrl = control.controllerClientId;
    const pend = control.pendingRequesterId;
    const youControl = ctrl != null && ctrl === me;
    const pendingYou = pend === me;
    const prevPendingMe =
      prevControl && prevControl.pendingRequesterId === me;

    const main = document.getElementById("appMain");
    if (main) {
      if (youControl) {
        main.removeAttribute("inert");
        main.classList.remove("app-readonly");
      } else {
        main.setAttribute("inert", "");
        main.classList.add("app-readonly");
      }
    }

    const status = document.getElementById("controlStatusLabel");
    const take = document.getElementById("btnTakeControl");
    const waitDlg = document.getElementById("controlWaitDialog");
    const waitOpen = waitDlg && waitDlg.open;
    const btnForce = document.getElementById("btnControlForce");

    if (status) {
      status.textContent = tc(youControl ? "controlStatusYou" : "controlStatusReadonly");
    }
    if (take) {
      take.hidden = youControl || (pendingYou && waitOpen);
      take.textContent = tc("btnTakeControl");
    }

    const requestDenied = prevPendingMe && !pend && !youControl;
    if (requestDenied) {
      showControlFeedback(tc("controlRequestDenied"));
    }

    if (waitOpen && (youControl || !pend)) {
      closeWaitDialog();
    }

    const apprDlg = document.getElementById("controlApproveDialog");
    if (apprDlg && apprDlg.open && (!pend || !youControl)) {
      apprDlg.close();
    }
    if (youControl && pend && pend !== me) {
      if (lastApprovePromptedPending !== pend) {
        lastApprovePromptedPending = pend;
        const pEl = document.getElementById("controlApproveText");
        if (pEl) pEl.textContent = tc("controlApproveText");
        if (apprDlg && typeof apprDlg.showModal === "function") apprDlg.showModal();
      }
    } else if (!pend) {
      lastApprovePromptedPending = null;
    }

    const waitOpenAfter = waitDlg && waitDlg.open;
    if (
      waitOpenAfter &&
      pend === me &&
      btnForce &&
      btnForce.disabled &&
      !forceEnableTimer
    ) {
      armForceDelayForWaitDialog();
    }
  }

  function refreshControlLabels() {
    const tW = document.getElementById("controlWaitTitle");
    const pW = document.getElementById("controlWaitText");
    const bf = document.getElementById("btnControlForce");
    const bc = document.getElementById("btnControlWaitCancel");
    if (tW) tW.textContent = tc("controlWaitTitle");
    if (pW) pW.textContent = tc("controlWaitText");
    if (bf) bf.textContent = tc("btnControlForce");
    if (bc) bc.textContent = tc("btnControlWaitCancel");
    const dlg = document.getElementById("controlWaitDialog");
    if (dlg && dlg.open && dlg.dataset.forceDeadline) {
      updateForceHintFromDeadline();
    }
    const tA = document.getElementById("controlApproveTitle");
    const pA = document.getElementById("controlApproveText");
    const ba = document.getElementById("btnControlApprove");
    const bd = document.getElementById("btnControlDeny");
    if (tA) tA.textContent = tc("controlApproveTitle");
    if (pA) pA.textContent = tc("controlApproveText");
    if (ba) ba.textContent = tc("btnControlApprove");
    if (bd) bd.textContent = tc("btnControlDeny");
    const take = document.getElementById("btnTakeControl");
    if (take) take.textContent = tc("btnTakeControl");
    if (lastControl) applyControlState(lastControl);
  }

  async function onTakeControl() {
    try {
      const r = await controlApiFetch("/api/control/request", { method: "POST" });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        console.warn("control/request", j.detail || r.statusText);
        return;
      }
      if (j.control) applyControlState(j.control);
      if (j.status === "pending") openWaitDialog();
      else closeWaitDialog();
    } catch (e) {
      console.warn(e);
    }
  }

  async function onApprove() {
    const pend = lastControl && lastControl.pendingRequesterId;
    if (!pend) return;
    try {
      const r = await controlApiFetch("/api/control/approve", {
        method: "POST",
        body: JSON.stringify({ requesterClientId: pend }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        console.warn("control/approve", j.detail || r.statusText);
        return;
      }
      if (j.control) applyControlState(j.control);
      const dlg = document.getElementById("controlApproveDialog");
      if (dlg && dlg.open) dlg.close();
    } catch (e) {
      console.warn(e);
    }
  }

  async function onDeny() {
    const pend = lastControl && lastControl.pendingRequesterId;
    if (!pend) return;
    try {
      const r = await controlApiFetch("/api/control/deny", {
        method: "POST",
        body: JSON.stringify({ requesterClientId: pend }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        console.warn("control/deny", j.detail || r.statusText);
        return;
      }
      if (j.control) applyControlState(j.control);
      const dlg = document.getElementById("controlApproveDialog");
      if (dlg && dlg.open) dlg.close();
    } catch (e) {
      console.warn(e);
    }
  }

  async function onForce() {
    try {
      const r = await controlApiFetch("/api/control/force", { method: "POST" });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        console.warn("control/force", j.detail || r.statusText);
        return;
      }
      if (j.control) applyControlState(j.control);
      closeWaitDialog();
    } catch (e) {
      console.warn(e);
    }
  }

  function initControlUi() {
    refreshControlLabels();
    const take = document.getElementById("btnTakeControl");
    if (take) take.addEventListener("click", onTakeControl);
    const appr = document.getElementById("btnControlApprove");
    const deny = document.getElementById("btnControlDeny");
    const force = document.getElementById("btnControlForce");
    const cancel = document.getElementById("btnControlWaitCancel");
    if (appr) appr.addEventListener("click", onApprove);
    if (deny) deny.addEventListener("click", onDeny);
    if (force) force.addEventListener("click", onForce);
    if (cancel) cancel.addEventListener("click", () => closeWaitDialog());

    fetch("/api/control")
      .then((r) => r.json())
      .then((c) => applyControlState(c))
      .catch(() => {
        applyControlState({
          controllerClientId: null,
          pendingRequesterId: null,
          pendingSince: null,
        });
      });
  }

  window.getAppClientId = getAppClientId;
  window.applyControlState = applyControlState;
  window.refreshControlLabels = refreshControlLabels;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initControlUi);
  } else {
    initControlUi();
  }
})();
