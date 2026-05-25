const state = {
  accounts: [],
  variants: [],
  images: [],
  status: null,
  busy: false,
  actionOutput: "",
  checkRows: [],
  checkFilter: "all",
  groups: {},
  campaigns: [],
  logs: [],
  uiLanguage: "tr",
  streamHandlers: new Map()
};

const I18N = {
  tr: {
    "nav.dashboard": "Dashboard",
    "nav.campaigns": "Kampanyalar",
    "nav.accounts": "Hesaplar",
    "nav.health": "Sağlık Kontrolü",
    "nav.operations": "Operasyonlar",
    "nav.settings": "Ayarlar",
    "nav.logs": "Loglar",
    "button.refresh": "Yenile",
    "button.selectAll": "Tümünü seç",
    "button.clear": "Temizle",
    "button.selectGroup": "Grubu seç",
    "button.images": "Görseller",
    "button.preview": "Önizleme üret",
    "button.check": "Kontrol",
    "button.publish": "Seçilileri yayınla",
    "button.selectFailed": "Hatalıları seç",
    "button.deleteFailed": "Hatalıları sil",
    "button.runCheck": "Kontrolü başlat",
    "dashboard.eyebrow": "SMM Kontrol Merkezi",
    "dashboard.title": "Kampanya performansı ve hesap sağlığı",
    "dashboard.subtitle": "Hesap havuzunu, son operasyonları ve kampanya sonuçlarını tek ekrandan izle.",
    "dashboard.newCampaign": "Yeni kampanya",
    "dashboard.runHealth": "Sağlık kontrolü",
    "dashboard.quickActions": "Hızlı Aksiyonlar",
    "dashboard.liveReady": "Canlı hazır",
    "dashboard.recentCampaigns": "Son Kampanyalar",
    "loading.boot": "Sistem hazırlanıyor...",
    "loading.accounts": "Hesaplar yükleniyor...",
    "loading.campaigns": "Kampanya geçmişi alınıyor...",
    "loading.logs": "Loglar hazırlanıyor...",
    "loading.oauth": "OAuth proxy durumu kontrol ediliyor...",
    "loading.ready": "Panel açılıyor...",
    "metric.accounts": "Hesaplar",
    "metric.health": "Sağlıklı",
    "metric.proxy": "Proxy",
    "metric.success": "Son başarı",
    "quick.tweet": "Tweet kampanyası",
    "quick.reply": "Yanıt kampanyası",
    "quick.like": "Beğeni boost",
    "quick.retweet": "Retweet boost",
    "quick.follow": "Takip hedefi",
    "quick.check": "Hesap kontrolü",
    "campaign.draft": "Kampanya Taslağı",
    "campaign.publishOutput": "Yayın Çıktısı",
    "label.mode": "Mod",
    "label.workers": "Workers",
    "label.replyTo": "Yanıt tweet ID",
    "label.aiModel": "AI model",
    "operations.bulk": "Toplu Operasyonlar",
    "operations.surface": "Kampanya araçları",
    "operations.console": "Operasyon Konsolu",
    "operations.useProxy": "Bu operasyonda proxy kullan",
    "filter.all": "Tümü",
    "filter.active": "Aktif",
    "filter.failed": "Hatalı",
    "filter.auth": "Auth hataları",
    "filter.timeout": "Timeout",
    "accounts.totalHint": "Toplam kayıt",
    "accounts.ready": "Hazır",
    "accounts.readyHint": "Credential yüklü",
    "accounts.missing": "Eksik",
    "accounts.missingHint": "Credential gerekli",
    "accounts.failed": "hatalı",
    "settings.language": "Dil",
    "settings.enabled": "Açık",
    "settings.disabled": "Kapalı",
    "settings.notSet": "Tanımlı değil",
    "status.ready": "Hazır",
    "status.missing": "Eksik",
    "status.checking": "Kontrol ediliyor",
    "status.queued": "Kuyrukta",
    "status.notChecked": "Kontrol edilmedi",
    "status.notSelected": "Seçilmedi",
    "status.noResult": "Sonuç yok",
    "empty.logs": "Henüz log yok.",
    "empty.action": "Henüz operasyon çalışmadı.",
    "empty.import": "Henüz import çalışmadı.",
    "campaign.unknown": "Kampanya",
    "unit.proxy": "proxy"
  },
  en: {
    "nav.dashboard": "Dashboard",
    "nav.campaigns": "Campaigns",
    "nav.accounts": "Accounts",
    "nav.health": "Health Check",
    "nav.operations": "Operations",
    "nav.settings": "Settings",
    "nav.logs": "Logs",
    "button.refresh": "Refresh",
    "button.selectAll": "Select all",
    "button.clear": "Clear",
    "button.selectGroup": "Select group",
    "button.images": "Images",
    "button.preview": "Generate preview",
    "button.check": "Check",
    "button.publish": "Publish selected",
    "button.selectFailed": "Select failed",
    "button.deleteFailed": "Delete failed",
    "button.runCheck": "Run check",
    "dashboard.eyebrow": "SMM Control Center",
    "dashboard.title": "Campaign performance and account health",
    "dashboard.subtitle": "Track your account pool, recent operations and campaign outcomes from one place.",
    "dashboard.newCampaign": "New campaign",
    "dashboard.runHealth": "Run health check",
    "dashboard.quickActions": "Quick Actions",
    "dashboard.liveReady": "Live ready",
    "dashboard.recentCampaigns": "Recent Campaigns",
    "loading.boot": "Preparing system...",
    "loading.accounts": "Loading accounts...",
    "loading.campaigns": "Loading campaign history...",
    "loading.logs": "Preparing logs...",
    "loading.oauth": "Checking OAuth proxy status...",
    "loading.ready": "Opening panel...",
    "metric.accounts": "Accounts",
    "metric.health": "Healthy",
    "metric.proxy": "Proxy",
    "metric.success": "Last success",
    "quick.tweet": "Tweet campaign",
    "quick.reply": "Reply campaign",
    "quick.like": "Like boost",
    "quick.retweet": "Retweet boost",
    "quick.follow": "Follow target",
    "quick.check": "Check accounts",
    "campaign.draft": "Campaign Draft",
    "campaign.publishOutput": "Publish Output",
    "label.mode": "Mode",
    "label.workers": "Workers",
    "label.replyTo": "Reply to tweet ID",
    "label.aiModel": "AI model",
    "operations.bulk": "Bulk Operations",
    "operations.surface": "Campaign tools",
    "operations.console": "Operation Console",
    "operations.useProxy": "Use proxy for this operation",
    "filter.all": "All",
    "filter.active": "Active",
    "filter.failed": "Failed",
    "filter.auth": "Auth errors",
    "filter.timeout": "Timeout",
    "accounts.totalHint": "Total records",
    "accounts.ready": "Ready",
    "accounts.readyHint": "Credentials loaded",
    "accounts.missing": "Missing",
    "accounts.missingHint": "Need credentials",
    "accounts.failed": "failed",
    "settings.language": "Language",
    "settings.enabled": "Enabled",
    "settings.disabled": "Disabled",
    "settings.notSet": "Not set",
    "status.ready": "Ready",
    "status.missing": "Missing",
    "status.checking": "Checking",
    "status.queued": "Queued",
    "status.notChecked": "Not checked",
    "status.notSelected": "Not selected",
    "status.noResult": "No result",
    "empty.logs": "No logs yet.",
    "empty.action": "No action run yet.",
    "empty.import": "No import run yet.",
    "campaign.unknown": "Campaign",
    "unit.proxy": "proxy"
  }
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function t(key) {
  return I18N[state.uiLanguage]?.[key] || I18N.tr[key] || key;
}

function applyI18n() {
  document.documentElement.lang = state.uiLanguage;
  $$("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
}

function isActiveCheckStatus(status) {
  return ["AKTİF", "AKTİF+YAZMA✓"].includes(String(status || ""));
}

function isNeutralCheckStatus(status) {
  return [
    "Ready",
    "Pending",
    "Checking",
    "Hazır",
    "Kontrol ediliyor",
    "Kuyrukta",
    "AKTİF",
    "AKTİF+YAZMA✓"
  ].includes(String(status || ""));
}

function isRunningCheckStatus(status) {
  return ["Checking", "Kontrol ediliyor", "Kuyrukta"].includes(String(status || ""));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(node._timer);
  node._timer = setTimeout(() => node.classList.remove("show"), 3200);
}

async function api(command, payload = {}) {
  setBusy(true);
  try {
    const data = await window.tweeterAPI.call(command, payload);
    $("#bridgeDot").classList.add("ok");
    $("#bridgeStatus").textContent = "Ready";
    return data;
  } catch (error) {
    $("#bridgeDot").classList.remove("ok");
    $("#bridgeStatus").textContent = "Error";
    toast(error.message);
    throw error;
  } finally {
    setBusy(false);
  }
}

async function stream(command, payload, hooks = {}) {
  setBusy(true);
  return new Promise(async (resolve, reject) => {
    let streamId = null;
    try {
      streamId = await window.tweeterAPI.stream(command, payload || {});
      state.streamHandlers.set(streamId, {
        hooks,
        resolve(value) {
          state.streamHandlers.delete(streamId);
          setBusy(false);
          resolve(value);
        },
        reject(error) {
          state.streamHandlers.delete(streamId);
          setBusy(false);
          reject(error);
        },
        result: null,
        closed: false,
        failed: false
      });
    } catch (error) {
      setBusy(false);
      reject(error);
    }
  });
}

function handleStreamEvent(id, event) {
  const handler = state.streamHandlers.get(id);
  if (!handler) return;

  if (event.type === "line") {
    const line = stripAnsi(event.line || "");
    handler.hooks.onLine?.(line, event);
    return;
  }
  if (event.type === "progress") {
    handler.hooks.onProgress?.(event);
    return;
  }
  if (event.type === "done") {
    handler.result = event.data || {};
    handler.hooks.onDone?.(handler.result);
    if (handler.closed) handler.resolve(handler.result);
    return;
  }
  if (event.type === "error") {
    handler.failed = true;
    const error = new Error(event.error || "Stream failed");
    handler.hooks.onError?.(error);
    handler.reject(error);
    return;
  }
  if (event.type === "closed") {
    handler.closed = true;
    if (handler.failed) return;
    if (handler.result) {
      handler.resolve(handler.result);
    } else {
      handler.resolve({});
    }
  }
}

function setBusy(value) {
  state.busy = value;
  [
    "#previewBtn",
    "#checkBtn",
    "#accountsCheckBtn",
    "#refreshBtn",
    "#runActionBtn",
    "#runCheckPageBtn",
    "#addAccountBtn",
    "#bulkAddAccountsBtn",
    "#clearBulkInputBtn",
    "#postBtn",
    "#saveSettingsBtn",
    "#clearApiKeyBtn",
    "#startOauthBtn",
    "#stopOauthBtn",
    "#saveProxyBtn",
    "#selectAllAccountsBtn",
    "#clearAccountSelectionBtn"
  ].forEach((selector) => {
    const node = $(selector);
    if (node) node.disabled = value;
  });
}

function selectedIndices(selector = ".account-check") {
  return $$(`${selector}:checked`).map((node) => Number(node.value));
}

function setView(name) {
  $$(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === name);
  });
  $$(".view").forEach((view) => view.classList.remove("active"));
  $(`#${name}View`).classList.add("active");

  const titles = {
    dashboard: ["Dashboard", "Campaign control center for multi-account growth workflows.", "Dashboard", "Çoklu hesap büyüme kampanyaları için kontrol merkezi."],
    compose: ["Campaigns", "Create AI-assisted tweet campaigns and publish with live tracking.", "Kampanyalar", "AI destekli tweet kampanyaları oluştur ve canlı izle."],
    actions: ["Operations", "Run bulk SMM operations with selected accounts.", "Operasyonlar", "Seçili hesaplarla toplu SMM operasyonları çalıştır."],
    check: ["Health Check", "Watch account verification state and review results.", "Sağlık Kontrolü", "Hesap doğrulama durumunu ve sonuçları canlı izle."],
    accounts: ["Accounts", "Add, import, group and inspect account credentials.", "Hesaplar", "Hesap ekle, içe aktar, grupla ve durumlarını incele."],
    settings: ["Settings", "Runtime paths, AI endpoint and proxy configuration.", "Ayarlar", "Runtime, AI endpoint ve proxy yapılandırması."],
    logs: ["Logs", "Recent actions and API responses.", "Loglar", "Son aksiyonlar ve API yanıtları."]
  };
  const item = titles[name] || titles.dashboard;
  $("#viewTitle").textContent = state.uiLanguage === "en" ? item[0] : item[2];
  $("#viewSubtitle").textContent = state.uiLanguage === "en" ? item[1] : item[3];
}

function renderAccounts() {
  $("#accountCountBadge").textContent = `${state.accounts.length} accounts`;
  $("#accountList").innerHTML = renderAccountChecks("account-check");
  $("#actionAccountList").innerHTML = renderAccountChecks("action-account-check");
  $("#checkAccountList").innerHTML = renderCheckRows();
  updateActionSelectionCount();
  renderAccountMetrics();
  renderDashboard();

  $("#accountTable").innerHTML = `
    <div class="table-row table-head">
      <span></span><span>#</span><span>Username</span><span>Status</span><span>Credentials</span>
    </div>
    ${state.accounts
      .map((account) => `
        <div class="table-row">
          <input class="account-table-check" type="checkbox" value="${account.index}">
          <span>${account.index}</span>
          <strong>@${escapeHtml(account.username)}</strong>
          <span class="status-pill ${account.hasCredentials ? "" : "bad"}">
            ${account.hasCredentials ? t("status.ready") : t("status.missing")}
          </span>
          <span>${escapeHtml(account.authTokenPreview)} / ${escapeHtml(account.ct0Preview)}</span>
        </div>`)
      .join("")}`;
}

function renderAccountMetrics() {
  const ready = state.accounts.filter((account) => account.hasCredentials).length;
  const missing = state.accounts.length - ready;
  const healthy = state.checkRows.filter((row) => isActiveCheckStatus(row.status)).length;
  const failed = state.checkRows.filter((row) => row.checked && row.status && !isNeutralCheckStatus(row.status)).length;
  const pairs = [
    ["#accountMetricTotal", state.accounts.length],
    ["#accountMetricReady", ready],
    ["#accountMetricMissing", missing],
    ["#accountMetricHealthy", healthy],
  ];
  pairs.forEach(([selector, value]) => {
    const node = $(selector);
    if (node) node.textContent = value;
  });
  const failedNode = $("#accountMetricFailed");
  if (failedNode) failedNode.textContent = `${failed} ${t("accounts.failed")}`;
}

function renderAccountChecks(className) {
  return state.accounts
    .map((account) => {
      const checked = account.hasCredentials ? "checked" : "";
      const disabled = account.hasCredentials ? "" : "disabled";
      return `
        <label class="account-row">
          <input class="${className}" type="checkbox" value="${account.index}" ${checked} ${disabled}>
          <span>
            <strong>@${escapeHtml(account.username)}</strong>
            <span>${account.hasCredentials ? "credentials loaded" : "missing credentials"}</span>
          </span>
        </label>`;
    })
    .join("");
}

function renderCheckRows() {
  const rows = state.checkRows.length
    ? state.checkRows
    : state.accounts.map((account) => ({
        index: account.index,
        username: account.username,
        status: t("status.ready"),
        detail: t("status.notChecked"),
        checked: account.hasCredentials,
        ok: true
      }));

  const filteredRows = rows.filter((row) => {
    const status = String(row.status || "");
    const detail = String(row.detail || "").toLowerCase();
    if (state.checkFilter === "active") return isActiveCheckStatus(status);
    if (state.checkFilter === "failed") return row.checked && !isNeutralCheckStatus(status);
    if (state.checkFilter === "auth") return /401|auth|token|authenticate|TOKEN/i.test(`${status} ${detail}`);
    if (state.checkFilter === "timeout") return /timeout|zaman/i.test(`${status} ${detail}`);
    return true;
  });

  return filteredRows
    .map((row) => {
      const disabled = state.accounts[row.index - 1]?.hasCredentials ? "" : "disabled";
      const checked = row.checked ? "checked" : "";
      const bad = row.status && !isNeutralCheckStatus(row.status);
      return `
        <div class="check-row ${isRunningCheckStatus(row.status) ? "running" : ""} ${bad ? "bad" : ""}">
          <input class="check-account-check" type="checkbox" value="${row.index}" ${checked} ${disabled}>
          <strong>@${escapeHtml(row.username)}</strong>
          <span class="status-pill ${bad ? "bad" : ""}">${escapeHtml(row.status || "")}</span>
          <span class="muted">${escapeHtml(row.detail || "")}</span>
        </div>`;
    })
    .join("");
}

function renderSettings() {
  const settings = state.status?.settings || {};
  $("#settingsAiUrl").textContent = settings.aiBaseUrl || "";
  $("#settingsAiProvider").textContent = settings.aiProvider === "api-key" ? "OpenAI API key" : "OAuth proxy";
  $("#settingsApiKey").textContent = settings.hasAiApiKey ? settings.aiApiKeyPreview : t("settings.notSet");
  $("#settingsCli").textContent = settings.twitterCli || "";
  $("#settingsProxy").textContent = `${settings.proxyEnabled ? t("settings.enabled") : t("settings.disabled")} / ${settings.proxyCount || 0} ${t("unit.proxy")}`;
  $("#aiModelInput").value = settings.aiModel || "gpt-5.4-mini";
  $("#aiProviderSelect").value = settings.aiProvider || "oauth";
  $("#settingsAiBaseUrlInput").value = settings.aiBaseUrl || "http://127.0.0.1:10531/v1";
  $("#settingsAiModelInput").value = settings.aiModel || "gpt-5.4-mini";
  $("#settingsAiTimeoutInput").value = settings.aiTimeout || 60;
  $("#uiLanguageSelect").value = settings.uiLanguage || state.uiLanguage || "tr";
  syncLanguageInputs();
  $("#proxyEnabledInput").checked = Boolean(settings.proxyEnabled);
  const actionProxy = $("#actionProxyInput");
  if (actionProxy) actionProxy.checked = Boolean(settings.proxyEnabled);
  $("#settingsAiApiKeyInput").placeholder = settings.hasAiApiKey
    ? `Saved: ${settings.aiApiKeyPreview}`
    : "Only for API key mode";
  $("#workersInput").value = settings.workers || 6;
  $("#proxyInput").placeholder = settings.proxyPreview?.length
    ? settings.proxyPreview.join("\n")
    : "http://user:pass@host:port";
}

function renderGroups() {
  const groups = state.groups || { All: [] };
  const options = Object.keys(groups)
    .sort((a, b) => a.localeCompare(b))
    .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
    .join("");
  ["#groupSelect", "#actionGroupSelect"].forEach((selector) => {
    const node = $(selector);
    if (node) node.innerHTML = options || `<option value="All">All</option>`;
  });
}

function usernamesForGroup(name) {
  if (!name || name === "All") return state.accounts.map((account) => account.username.toLowerCase());
  return (state.groups?.[name] || []).map((username) => username.toLowerCase());
}

function selectGroupAccounts(checkboxClass, groupName) {
  const names = new Set(usernamesForGroup(groupName));
  $$(`.${checkboxClass}`).forEach((checkbox) => {
    const account = state.accounts[Number(checkbox.value) - 1];
    checkbox.checked = !!account && names.has(account.username.toLowerCase());
  });
  updateActionSelectionCount();
}

function renderVariants() {
  const list = $("#variantList");
  if (!state.variants.length) {
    list.className = "variant-list empty";
    list.textContent = "Generate a preview to review account-specific text.";
    $("#postBtn").disabled = true;
    return;
  }

  list.className = "variant-list";
  list.innerHTML = state.variants
    .map((row, index) => {
      const ok = row.ok && row.text;
      const len = row.text?.length || 0;
      const publishStatus = row.publishStatus || (ok ? "ready" : "error");
      const detail = row.publishDetail || (ok ? "Ready to publish" : row.error || "AI error");
      return `
        <div class="variant-row ${ok ? "" : "error"} ${publishStatus === "posting" ? "running" : ""}" data-index="${index}">
          <input class="variant-check" type="checkbox" ${ok ? "checked" : "disabled"}>
          <div>
            <strong>@${escapeHtml(row.username)}</strong>
            <span class="status-pill ${statusClass(publishStatus)}">${escapeHtml(statusLabel(publishStatus))}</span>
            <span class="muted row-detail">${escapeHtml(detail)}</span>
          </div>
          <textarea class="variant-text" ${ok ? "" : "disabled"}>${escapeHtml(row.text || "")}</textarea>
          <div class="length ${len > 260 ? "warn" : ""}">${len}/280</div>
        </div>`;
    })
    .join("");
  $("#postBtn").disabled = state.busy || !state.variants.some((row) => row.ok && row.text);

  $$(".variant-text").forEach((textarea) => {
    textarea.addEventListener("input", syncVariantsFromDom);
  });
  $$(".variant-check").forEach((checkbox) => {
    checkbox.addEventListener("change", syncVariantsFromDom);
  });
}

function statusLabel(status) {
  return {
    ready: "Ready",
    queued: "Queued",
    posting: "Posting",
    success: "Sent",
    error: "Error",
    skipped: "Skipped"
  }[status] || status || "Ready";
}

function statusClass(status) {
  if (status === "error") return "bad";
  if (status === "posting" || status === "queued") return "info";
  if (status === "skipped") return "muted-pill";
  return "";
}

function setVariantPublishState(username, status, detail = "") {
  const clean = String(username || "").replace(/^@/, "").toLowerCase();
  state.variants = state.variants.map((row) => (
    row.username.toLowerCase() === clean
      ? { ...row, publishStatus: status, publishDetail: detail || statusLabel(status) }
      : row
  ));
  renderVariants();
}

function syncVariantsFromDom() {
  $$(".variant-row").forEach((row) => {
    const index = Number(row.dataset.index);
    const text = row.querySelector(".variant-text")?.value || "";
    const enabled = row.querySelector(".variant-check")?.checked || false;
    state.variants[index].text = text;
    state.variants[index].enabled = enabled;
    const length = row.querySelector(".length");
    length.textContent = `${text.length}/280`;
    length.classList.toggle("warn", text.length > 260);
  });
}

function renderLogs(logs) {
  state.logs = logs || [];
  const list = $("#logList");
  if (!logs.length) {
    list.innerHTML = `<div class="variant-list empty">${t("empty.logs")}</div>`;
    return;
  }
  list.innerHTML = logs
    .map((log) => `
      <div class="log-row">
        <span>${escapeHtml(log.timestamp || "")}</span>
        <strong>@${escapeHtml(log.username || "")}</strong>
        <span class="status-pill ${log.success ? "" : "bad"}">${log.action || ""}</span>
        <span>${escapeHtml(log.target || log.stderr || "")}</span>
      </div>`)
    .join("");
}

function renderCampaignList(selector, badgeSelector = null) {
  const list = $(selector);
  if (!list) return;
  if (badgeSelector && $(badgeSelector)) $(badgeSelector).textContent = state.campaigns.length;
  if (!state.campaigns.length) {
    list.className = "campaign-list empty";
    list.textContent = state.uiLanguage === "en" ? "No campaign history yet." : "Henüz kampanya geçmişi yok.";
    return;
  }
  list.className = "campaign-list";
  list.innerHTML = state.campaigns.slice(0, 8).map((campaign) => {
    const total = Number(campaign.accountCount || 0);
    const success = Number(campaign.successCount || 0);
    const failed = Number(campaign.failCount || 0);
    const rate = total ? Math.round((success / total) * 100) : 0;
    return `
      <div class="campaign-row">
        <div>
          <strong>${escapeHtml(campaign.title || campaign.type || t("campaign.unknown"))}</strong>
          <span class="muted">${escapeHtml(campaign.target || "-")} · ${escapeHtml(campaign.finishedAt || campaign.startedAt || "")}</span>
        </div>
        <span class="status-pill ${campaign.status === "completed" ? "" : "info"}">${escapeHtml(campaign.status || "")}</span>
        <span class="campaign-score">${success}/${total || success + failed} · ${rate}%</span>
      </div>`;
  }).join("");
}

function renderDashboard() {
  const ready = state.accounts.filter((account) => account.hasCredentials).length;
  const healthy = state.checkRows.filter((row) => isActiveCheckStatus(row.status)).length;
  const failed = state.checkRows.filter((row) => row.checked && row.status && !isNeutralCheckStatus(row.status)).length;
  const settings = state.status?.settings || {};
  const last = state.campaigns[0];
  const lastTotal = Number(last?.accountCount || 0);
  const lastSuccess = Number(last?.successCount || 0);
  const lastRate = lastTotal ? `${Math.round((lastSuccess / lastTotal) * 100)}%` : "-";

  const values = {
    "#metricTotalAccounts": state.accounts.length,
    "#metricCredentialState": `${ready} ${state.uiLanguage === "en" ? "ready" : "hazır"}`,
    "#metricHealthyAccounts": healthy,
    "#metricFailedAccounts": `${failed} ${t("accounts.failed")}`,
    "#metricProxyState": settings.proxyEnabled ? (state.uiLanguage === "en" ? "On" : "Açık") : (state.uiLanguage === "en" ? "Off" : "Kapalı"),
    "#metricProxyCount": `${settings.proxyCount || 0} ${t("unit.proxy")}`,
    "#metricSuccessRate": lastRate,
    "#metricLastCampaign": last ? (last.title || last.type || t("campaign.unknown")) : (state.uiLanguage === "en" ? "No campaign yet" : "Henüz kampanya yok"),
  };
  Object.entries(values).forEach(([selector, value]) => {
    const node = $(selector);
    if (node) node.textContent = value;
  });
  renderCampaignList("#dashboardCampaignList", "#campaignCountBadge");
  renderCampaignList("#operationsCampaignList", "#operationsCampaignBadge");
}

function setLoading(messageKey) {
  const node = $("#loadingText");
  if (node) node.textContent = t(messageKey);
}

function hideLoading() {
  const node = $("#loadingScreen");
  if (!node) return;
  node.classList.add("hidden");
  window.setTimeout(() => {
    node.remove();
  }, 320);
}

function failLoading(error) {
  const node = $("#loadingScreen");
  const text = $("#loadingText");
  if (node) node.classList.add("failed");
  if (text) text.textContent = error?.message || String(error || "Startup failed");
}

async function loadStatus() {
  const status = await api("status");
  state.status = status;
  state.accounts = status.accounts || [];
  state.groups = status.groups || { All: [] };
  state.uiLanguage = status.settings?.uiLanguage || "tr";
  applyI18n();
  syncLanguageInputs();
  renderAccounts();
  renderSettings();
  renderGroups();
  setView($(".nav-item.active")?.dataset.view || "dashboard");
}

async function loadLogs() {
  const data = await api("logs", { limit: 100 });
  renderLogs(data.logs || []);
  renderDashboard();
}

async function loadCampaigns() {
  const data = await api("campaignHistory", { limit: 50 });
  state.campaigns = data.campaigns || [];
  renderDashboard();
}

function syncLanguageInputs() {
  ["#topLanguageSelect", "#uiLanguageSelect"].forEach((selector) => {
    const node = $(selector);
    if (node) node.value = state.uiLanguage;
  });
}

async function saveLanguage(language) {
  const settings = state.status?.settings || {};
  const data = await api("saveSettings", {
    aiProvider: settings.aiProvider || "oauth",
    aiBaseUrl: settings.aiBaseUrl || "http://127.0.0.1:10531/v1",
    aiModel: settings.aiModel || "gpt-5.4-mini",
    aiTimeout: Number(settings.aiTimeout || 60),
    proxyEnabled: Boolean(settings.proxyEnabled),
    uiLanguage: language
  });
  state.status.settings = data.settings || state.status.settings;
  state.uiLanguage = state.status.settings.uiLanguage || "tr";
  applyI18n();
  syncLanguageInputs();
  renderSettings();
  renderAccounts();
  renderDashboard();
  setView($(".nav-item.active")?.dataset.view || "dashboard");
}

async function generatePreview() {
  const mode = $("#modeSelect").value;
  const indices = selectedIndices();
  const payload = {
    indices,
    workers: Number($("#workersInput").value || 6),
    aiModel: $("#aiModelInput").value.trim(),
    aiBaseUrl: state.status?.settings?.aiBaseUrl,
    text: $("#promptInput").value.trim(),
    instruction: $("#promptInput").value.trim()
  };
  if (!payload.text) {
    toast("Metin veya yönerge gir.");
    return;
  }
  if (!indices.length) {
    toast("En az bir hesap seç.");
    return;
  }

  const data = await api(mode === "rewrite" ? "previewRewrite" : "previewInstruction", payload);
  state.variants = (data.variants || []).map((row) => ({
    ...row,
    enabled: row.ok,
    publishStatus: row.ok ? "ready" : "error",
    publishDetail: row.ok ? "AI preview ready" : row.error || "AI error"
  }));
  renderVariants();
  $("#publishOutput").textContent = "Preview hazır. Publish selected ile gönderim başlatılabilir.";
  $("#publishSummary").textContent = t("status.ready");
  toast("AI preview hazır.");
}

async function publishVariants() {
  syncVariantsFromDom();
  const enabledRows = state.variants.filter((row) => row.enabled && row.ok && row.text);
  if (!enabledRows.length) {
    toast("Gönderilecek satır yok.");
    return;
  }
  if (enabledRows.some((row) => row.text.length > 280)) {
    toast("280 karakteri aşan satırlar var.");
    return;
  }
  const ok = confirm(`${enabledRows.length} hesaptan gönderim yapılacak. Devam edilsin mi?`);
  if (!ok) return;

  const enabledNames = new Set(enabledRows.map((row) => row.username.toLowerCase()));
  state.variants = state.variants.map((row) => (
    enabledNames.has(row.username.toLowerCase())
      ? { ...row, publishStatus: "queued", publishDetail: "Kuyrukta" }
      : row
  ));
  renderVariants();
  $("#publishOutput").textContent = "Gönderim hazırlanıyor...";
  $("#publishSummary").textContent = `0/${enabledRows.length}`;

  let completed = 0;
  const seenDone = new Set();
  const data = await stream("postVariants", {
    variants: enabledRows,
    replyTo: $("#replyToInput").value.trim(),
    images: state.images,
    retry: 2
  }, {
    onLine(line) {
      appendPublishOutput(line);
    },
    onProgress(event) {
      setVariantPublishState(event.username, event.status, event.detail);
      if (["success", "error", "skipped"].includes(event.status) && !seenDone.has(event.username)) {
        seenDone.add(event.username);
        completed += 1;
        $("#publishSummary").textContent = `${completed}/${enabledRows.length}`;
      }
    },
    onError(error) {
      appendPublishOutput(`HATA: ${error.message}`);
      $("#publishSummary").textContent = "Error";
    }
  });
  const success = (data.results || []).filter((row) => row.success).length;
  (data.results || []).forEach((row) => {
    setVariantPublishState(row.username, row.success ? "success" : row.skipped ? "skipped" : "error", row.error || (row.success ? "Başarılı" : "Başarısız"));
  });
  $("#publishSummary").textContent = `${success}/${enabledRows.length} ${state.uiLanguage === "en" ? "sent" : "gönderildi"}`;
  toast(`${success}/${enabledRows.length} gönderim başarılı.`);
  state.campaigns = data.campaigns || state.campaigns;
  renderDashboard();
  renderLogs(data.logs || []);
  await loadLogs();
}

function appendPublishOutput(line) {
  const node = $("#publishOutput");
  node.textContent += `\n${stripAnsi(line)}`;
  node.scrollTop = node.scrollHeight;
}

async function runCheck() {
  await runCheckPage(selectedIndices(), false);
}

async function runCheckPage(indices = selectedIndices(".check-account-check"), switchView = true) {
  if (!indices.length) {
    toast("Check için en az bir hesap seç.");
    return;
  }
  state.checkRows = state.accounts.map((account) => ({
    index: account.index,
    username: account.username,
    checked: indices.includes(account.index),
    status: indices.includes(account.index) ? t("status.checking") : t("status.ready"),
    detail: indices.includes(account.index) ? t("status.queued") : t("status.notSelected"),
    ok: true
  }));
  $("#checkSummary").textContent = `${indices.length} checking`;
  $("#checkAccountList").innerHTML = renderCheckRows();
  $("#checkOutput").textContent = "Kontrol başladı...\nSeçili hesaplar işleniyor.";
  if (switchView) setView("check");

  const data = await stream("check", {
    indices,
    workers: Number($("#checkWorkersInput").value || $("#workersInput").value || 6),
    deep: $("#checkDeepInput")?.checked || false
  }, {
    onLine(line) {
      appendCheckOutput(line);
      updateCheckRowFromLine(line);
    },
    onError(error) {
      appendCheckOutput(`HATA: ${error.message}`);
    }
  });
  const byName = new Map((data.accounts || []).map((row) => [row.username, row]));
  state.checkRows = state.accounts.map((account) => {
    const result = byName.get(account.username);
    return {
      index: account.index,
      username: account.username,
      checked: indices.includes(account.index),
      status: result ? result.label : indices.includes(account.index) ? t("status.noResult") : t("status.ready"),
      detail: result ? result.error || result.uid || result.screenName || "" : t("status.notSelected"),
      ok: result ? result.ok : true
    };
  });
  $("#checkAccountList").innerHTML = renderCheckRows();
  if (data.output) $("#checkOutput").textContent = stripAnsi(data.output || "");
  $("#checkSummary").textContent = `${(data.accounts || []).length} checked`;
  state.campaigns = data.campaigns || state.campaigns;
  renderDashboard();
  $("#accountTable").innerHTML = `
    <div class="table-row table-head">
      <span></span><span>#</span><span>Username</span><span>Status</span><span>Detail</span>
    </div>
    ${(data.accounts || [])
      .map((account, index) => {
        const original = state.accounts.find((row) => row.username.toLowerCase() === account.username.toLowerCase());
        const value = original?.index || index + 1;
        return `
        <div class="table-row">
          <input class="account-table-check" type="checkbox" value="${value}">
          <span>${index + 1}</span>
          <strong>@${escapeHtml(account.username)}</strong>
          <span class="status-pill ${account.ok ? "" : "bad"}">${escapeHtml(account.label || "")}</span>
          <span>${escapeHtml(account.error || account.uid || account.screenName || "")}</span>
        </div>`;
      })
      .join("")}`;
  toast("Hesap kontrolü tamamlandı.");
}

function appendCheckOutput(line) {
  const node = $("#checkOutput");
  node.textContent += `\n${line}`;
  node.scrollTop = node.scrollHeight;
}

function updateCheckRowFromLine(line) {
  const clean = stripAnsi(line);
  const match = clean.match(/@([A-Za-z0-9_]+).*?\[([^\]]+)\](.*)/);
  if (!match) return;
  const username = match[1];
  const label = match[2];
  const detail = match[3].trim();
  state.checkRows = state.checkRows.map((row) => (
    row.username.toLowerCase() === username.toLowerCase()
      ? { ...row, status: label, detail, ok: isActiveCheckStatus(label) }
      : row
  ));
  $("#checkAccountList").innerHTML = renderCheckRows();
}

function stripAnsi(value) {
  return String(value || "").replace(/\x1b\[[0-9;]*m/g, "");
}

function updateActionSelectionCount() {
  const count = selectedIndices(".action-account-check").length;
  const node = $("#actionAccountCount");
  if (node) node.textContent = `${count} selected`;
}

async function runAction() {
  const action = $("#actionSelect").value;
  const indices = selectedIndices(".action-account-check");
  const destructive = ["boost", "follow-boost", "view", "protect", "unprotect", "purge"].includes(action);
  if (!indices.length && action !== "fix-usernames") {
    toast("Aksiyon için hesap seç.");
    return;
  }
  if (destructive) {
    const ok = confirm(`${action} gerçek aksiyon çalıştıracak. Devam edilsin mi?`);
    if (!ok) return;
  }
  $("#actionOutput").textContent = `${action} çalışıyor...\nSeçili hesap: ${indices.length}`;
  const payload = {
    action,
    indices,
    workers: Number($("#actionWorkersInput").value || 10),
    tweetId: $("#actionTweetIdInput").value.trim(),
    username: $("#actionUsernameInput").value.trim(),
    text: $("#actionTextInput").value.trim(),
    instruction: $("#actionTextInput").value.trim(),
    replyText: $("#actionReplyTextInput").value.trim(),
    repeat: Number($("#actionRepeatInput").value || 1),
    aiRewrite: $("#actionAiRewriteInput").checked,
    useProxy: $("#actionProxyInput").checked,
    deep: $("#actionDeepInput").checked,
    skipFollow: $("#actionSkipFollowInput").checked,
    delayMin: 0,
    delayMax: 0,
    aiModel: $("#aiModelInput").value.trim(),
    aiBaseUrl: state.status?.settings?.aiBaseUrl
  };
  const data = await stream("action", payload, {
    onLine(line) {
      appendActionOutput(line);
    },
    onError(error) {
      appendActionOutput(`HATA: ${error.message}`);
    }
  });
  if (data.output) $("#actionOutput").textContent = stripAnsi(data.output);
  state.campaigns = data.campaigns || state.campaigns;
  renderDashboard();
  renderLogs(data.logs || []);
  toast(`${action} tamamlandı.`);
}

function appendActionOutput(line) {
  const node = $("#actionOutput");
  node.textContent += `\n${stripAnsi(line)}`;
  node.scrollTop = node.scrollHeight;
}

async function addAccount(single = true) {
  const payload = single
    ? {
        manual: {
          username: $("#newUsernameInput").value.trim(),
          password: $("#newPasswordInput").value.trim(),
          telephone: $("#newPhoneInput").value.trim(),
          authToken: $("#newAuthTokenInput").value.trim(),
          ct0: $("#newCt0Input").value.trim()
        }
      }
    : { raw: $("#bulkAccountsInput").value };
  const data = await api("addAccounts", payload);
  state.accounts = data.accounts || state.accounts;
  renderAccounts();
  renderImportResult(data);
  toast(`${(data.added || []).length} hesap eklendi, ${(data.skipped || []).length} atlandı.`);
  if ((data.added || []).length && single) {
    ["#newUsernameInput", "#newPasswordInput", "#newPhoneInput", "#newAuthTokenInput", "#newCt0Input"].forEach((selector) => {
      $(selector).value = "";
    });
  }
  if ((data.added || []).length && !single) {
    $("#bulkAccountsInput").value = "";
  }
}

function renderImportResult(data) {
  const node = $("#bulkImportResult");
  if (!node) return;
  const added = data.added || [];
  const skipped = data.skipped || [];
  const addedText = added.length ? `Eklenen: ${added.map((row) => `@${row.username}`).join(", ")}` : "Eklenen hesap yok.";
  const skippedText = skipped.length
    ? `Atlanan: ${skipped.map((row) => row.username ? `@${row.username} (${row.reason})` : `satır ${row.line} (${row.reason})`).join(", ")}`
    : "Atlanan satır yok.";
  node.innerHTML = `<strong>${added.length} eklendi, ${skipped.length} atlandı.</strong><br>${escapeHtml(addedText)}<br>${escapeHtml(skippedText)}`;
}

async function deleteAccounts(usernames, indices = []) {
  if (!usernames.length && !indices.length) {
    toast("Silinecek hesap seçilmedi.");
    return;
  }
  const label = usernames.length ? usernames.map((name) => `@${name}`).join(", ") : `${indices.length} selected`;
  if (!confirm(`${label} silinsin mi? Bu işlem accounts.txt dosyasını günceller.`)) return;
  const data = await api("deleteAccounts", { usernames, indices });
  state.accounts = data.accounts || state.accounts;
  state.groups = data.groups || state.groups;
  state.checkRows = state.checkRows.filter((row) => !(data.removed || []).some((name) => name.toLowerCase() === row.username.toLowerCase()));
  renderAccounts();
  renderGroups();
  toast(`${(data.removed || []).length} hesap silindi.`);
}

function failedCheckUsernames() {
  return state.checkRows
    .filter((row) => row.checked && !isNeutralCheckStatus(row.status))
    .map((row) => row.username);
}

async function createGroup() {
  const name = $("#newGroupInput").value.trim();
  if (!name) {
    toast("Grup adı gir.");
    return;
  }
  const data = await api("groups", { op: "create", name });
  state.groups = data.groups || state.groups;
  renderGroups();
  toast(`${name} grubu oluşturuldu.`);
}

async function assignSelectedToGroup() {
  const name = $("#groupSelect").value;
  const indices = selectedIndices(".account-table-check");
  if (!name || name === "All") {
    toast("Özel bir grup seç veya oluştur.");
    return;
  }
  if (!indices.length) {
    toast("Gruba eklenecek hesapları tablodan seç.");
    return;
  }
  const data = await api("groups", { op: "assign", name, indices });
  state.groups = data.groups || state.groups;
  renderGroups();
  toast(`${indices.length} hesap ${name} grubuna eklendi.`);
}

function bindEvents() {
  $$(".nav-item").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
  $$(".quick-action, .quick-tile").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.viewTarget) setView(button.dataset.viewTarget);
      if (button.dataset.actionTarget) {
        setView("actions");
        $("#actionSelect").value = button.dataset.actionTarget;
      }
    });
  });
  $$(".filter-chip").forEach((button) => {
    button.addEventListener("click", () => {
      state.checkFilter = button.dataset.checkFilter || "all";
      $$(".filter-chip").forEach((item) => item.classList.toggle("active", item === button));
      $("#checkAccountList").innerHTML = renderCheckRows();
    });
  });
  $("#refreshBtn").addEventListener("click", loadStatus);
  $("#topLanguageSelect").addEventListener("change", async () => {
    await saveLanguage($("#topLanguageSelect").value);
    toast(state.uiLanguage === "en" ? "Language updated." : "Dil güncellendi.");
  });
  $("#uiLanguageSelect").addEventListener("change", async () => {
    await saveLanguage($("#uiLanguageSelect").value);
    toast(state.uiLanguage === "en" ? "Language updated." : "Dil güncellendi.");
  });
  $("#reloadLogsBtn").addEventListener("click", loadLogs);
  $("#previewBtn").addEventListener("click", generatePreview);
  $("#postBtn").addEventListener("click", publishVariants);
  $("#checkBtn").addEventListener("click", runCheck);
  $("#accountsCheckBtn").addEventListener("click", () => setView("check"));
  $("#runActionBtn").addEventListener("click", runAction);
  $("#clearActionOutputBtn").addEventListener("click", () => {
    $("#actionOutput").textContent = t("empty.action");
  });
  $("#runCheckPageBtn").addEventListener("click", () => runCheckPage());
  $("#checkSelectAllBtn").addEventListener("click", () => {
    $$(".check-account-check:not(:disabled)").forEach((node) => {
      node.checked = true;
    });
  });
  $("#checkClearBtn").addEventListener("click", () => {
    $$(".check-account-check").forEach((node) => {
      node.checked = false;
    });
  });
  $("#checkSelectFailedBtn").addEventListener("click", () => {
    const failed = new Set(failedCheckUsernames().map((name) => name.toLowerCase()));
    $$(".check-account-check").forEach((node) => {
      const account = state.accounts[Number(node.value) - 1];
      node.checked = account ? failed.has(account.username.toLowerCase()) : false;
    });
  });
  $("#deleteFailedBtn").addEventListener("click", () => deleteAccounts(failedCheckUsernames()));
  $("#addAccountBtn").addEventListener("click", () => addAccount(true));
  $("#bulkAddAccountsBtn").addEventListener("click", () => addAccount(false));
  $("#clearBulkInputBtn").addEventListener("click", () => {
    $("#bulkAccountsInput").value = "";
    $("#bulkImportResult").textContent = t("empty.import");
  });
  $("#createGroupBtn").addEventListener("click", createGroup);
  $("#assignGroupBtn").addEventListener("click", assignSelectedToGroup);
  $("#deleteSelectedAccountsBtn").addEventListener("click", () => {
    deleteAccounts([], selectedIndices(".account-table-check"));
  });
  $("#selectAllAccountsBtn").addEventListener("click", () => {
    $$(".account-table-check").forEach((node) => {
      node.checked = true;
    });
  });
  $("#clearAccountSelectionBtn").addEventListener("click", () => {
    $$(".account-table-check").forEach((node) => {
      node.checked = false;
    });
  });
  $("#selectAllBtn").addEventListener("click", () => {
    $$(".account-check:not(:disabled)").forEach((node) => {
      node.checked = true;
    });
  });
  $("#clearSelectionBtn").addEventListener("click", () => {
    $$(".account-check").forEach((node) => {
      node.checked = false;
    });
  });
  $("#selectGroupBtn").addEventListener("click", () => {
    selectGroupAccounts("account-check", $("#groupSelect").value || "All");
  });
  $("#actionSelectGroupBtn").addEventListener("click", () => {
    selectGroupAccounts("action-account-check", $("#actionGroupSelect").value || "All");
  });
  document.addEventListener("change", (event) => {
    if (event.target.classList?.contains("action-account-check")) updateActionSelectionCount();
  });
  $("#modeSelect").addEventListener("change", () => {
    const instruction = $("#modeSelect").value === "instruction";
    $("#promptLabel").textContent = instruction ? "Instruction" : "Base tweet";
    $("#promptInput").placeholder = instruction
      ? "Example: short product update, natural tone, no hashtags"
      : "Write the base tweet to rewrite per account";
  });
  $("#chooseImagesBtn").addEventListener("click", async () => {
    state.images = await window.tweeterAPI.chooseImages();
    $("#imageSummary").textContent = state.images.length
      ? `${state.images.length} image selected`
      : "";
  });
  $("#saveProxyBtn").addEventListener("click", async () => {
    const data = await api("saveProxies", {
      proxies: $("#proxyInput").value,
      proxyEnabled: $("#proxyEnabledInput").checked
    });
    toast(`${data.proxyEnabled ? "Proxy açık" : "Proxy kapalı"} / ${data.proxyCount} proxy kaydedildi.`);
    await loadStatus();
  });
  $("#saveSettingsBtn").addEventListener("click", async () => {
    const data = await api("saveSettings", {
      aiProvider: $("#aiProviderSelect").value,
      aiBaseUrl: $("#settingsAiBaseUrlInput").value.trim(),
      aiModel: $("#settingsAiModelInput").value.trim(),
      aiTimeout: Number($("#settingsAiTimeoutInput").value || 60),
      aiApiKey: $("#settingsAiApiKeyInput").value.trim(),
      proxyEnabled: $("#proxyEnabledInput").checked,
      uiLanguage: $("#uiLanguageSelect").value
    });
    state.status.settings = data.settings || state.status.settings;
    state.uiLanguage = state.status.settings.uiLanguage || "tr";
    $("#settingsAiApiKeyInput").value = "";
    applyI18n();
    syncLanguageInputs();
    renderSettings();
    renderAccounts();
    renderDashboard();
    syncLanguageInputs();
    setView($(".nav-item.active")?.dataset.view || "dashboard");
    toast("AI ayarları kaydedildi.");
  });
  $("#clearApiKeyBtn").addEventListener("click", async () => {
    const data = await api("saveSettings", {
      aiProvider: $("#aiProviderSelect").value,
      aiBaseUrl: $("#settingsAiBaseUrlInput").value.trim(),
      aiModel: $("#settingsAiModelInput").value.trim(),
      aiTimeout: Number($("#settingsAiTimeoutInput").value || 60),
      proxyEnabled: $("#proxyEnabledInput").checked,
      uiLanguage: $("#uiLanguageSelect").value,
      clearAiApiKey: true
    });
    state.status.settings = data.settings || state.status.settings;
    state.uiLanguage = state.status.settings.uiLanguage || "tr";
    applyI18n();
    syncLanguageInputs();
    renderSettings();
    renderAccounts();
    renderDashboard();
    toast("API key silindi.");
  });
  $("#startOauthBtn").addEventListener("click", async () => {
    const data = await window.tweeterAPI.startOauthProxy();
    renderOauthStatus(data);
    toast("OAuth proxy başlatıldı.");
  });
  $("#stopOauthBtn").addEventListener("click", async () => {
    const data = await window.tweeterAPI.stopOauthProxy();
    renderOauthStatus(data);
    toast("OAuth proxy durduruldu.");
  });
}

function renderOauthStatus(data) {
  const log = (data.log || []).join("");
  $("#oauthOutput").textContent = `${data.running ? "Running" : "Stopped"}\n${log || "No output yet."}`;
  $("#oauthOutput").scrollTop = $("#oauthOutput").scrollHeight;
}

async function boot() {
  window.tweeterAPI.onStreamEvent(handleStreamEvent);
  bindEvents();
  setLoading("loading.accounts");
  await loadStatus();
  setLoading("loading.campaigns");
  await loadCampaigns();
  setLoading("loading.logs");
  await loadLogs();
  setLoading("loading.oauth");
  renderOauthStatus(await window.tweeterAPI.oauthStatus());
  setLoading("loading.ready");
  window.setTimeout(hideLoading, 220);
}

boot().catch((error) => {
  console.error(error);
  failLoading(error);
  toast(error.message);
});
