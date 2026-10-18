// Estado da Aplicação no Frontend
const state = {
  currentTab: "dashboard",
  isProcessing: false,
  pollInterval: null,
  rules: [],
  destination: { path: "", isValid: false, message: "" },
  whatsapp: { state: "disconnected", message: "", driverAvailable: false },
};

// Inicialização ao carregar a página
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  loadDashboard();
  loadRules();
  loadDestination();
  checkWhatsAppStatus();
});

// Navegação entre abas
function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-btn");
  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  state.currentTab = tabId;
  document.querySelectorAll(".nav-btn").forEach((b) => {
    b.classList.toggle("active", b.getAttribute("data-tab") === tabId);
  });
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === `tab-${tabId}`);
  });

  // Ações de recarga específicas por aba
  if (tabId === "dashboard") loadDashboard();
  if (tabId === "rules") loadRules();
  if (tabId === "destination") loadDestination();
  if (tabId === "whatsapp") checkWhatsAppStatus();
  if (tabId === "history") loadHistory();
}

// Alertas Globais
function showAlert(message, type = "info") {
  const alertEl = document.getElementById("globalAlert");
  if (!alertEl) return;
  alertEl.textContent = message;
  alertEl.className = `alert alert-${type} mt-3 mb-3`;
  alertEl.classList.remove("hidden");
  setTimeout(() => {
    alertEl.classList.add("hidden");
  }, 6000);
}

/* =========================================================================
   1. PAINEL INICIAL (DASHBOARD)
   ========================================================================= */
async function loadDashboard() {
  try {
    const res = await fetch("/api/dashboard");
    if (!res.ok) throw new Error("Falha ao consultar painel.");
    const data = await res.json();

    // Atualizar Métricas
    document.getElementById("statProcessed").textContent = data.session_stats.processed;
    document.getElementById("statApproved").textContent = data.session_stats.approved;
    document.getElementById("statRejected").textContent = data.session_stats.rejected;
    document.getElementById("statSaved").textContent = data.session_stats.saved;

    // Status da Aplicação
    const appBadge = document.getElementById("appStatusBadge");
    const appText = document.getElementById("appStatusText");
    if (data.app_status === "processando") {
      appBadge.className = "status-badge pending";
      appText.textContent = "Processando Imagens";
    } else {
      appBadge.className = "status-badge online";
      appText.textContent = "Pronto para Uso";
    }

    // Status do WhatsApp
    updateWhatsAppBadges(data.whatsapp);

    // Destino no Dashboard
    document.getElementById("dashDestPath").textContent = data.destination.path || "Não definido";
    const destValidEl = document.getElementById("dashDestValid");
    if (data.destination.is_valid) {
      destValidEl.innerHTML = '<span class="text-success">✅ Válida (Permissão OK)</span>';
    } else {
      destValidEl.innerHTML = '<span class="text-danger">❌ Inválida / Sem Permissão</span>';
    }
    document.getElementById("dashDestMsg").textContent = data.destination.message;

    // Regras Ativas no Dashboard
    document.getElementById("dashActiveRulesCount").textContent = data.rules.active_count;
    const rulesListEl = document.getElementById("dashRulesList");
    if (data.rules.active_rules.length === 0) {
      rulesListEl.innerHTML = '<span class="empty-state-text text-muted text-sm">Nenhuma regra ativa no momento. Adicione regras para filtrar imagens.</span>';
    } else {
      rulesListEl.innerHTML = data.rules.active_rules
        .map((r) => `<span class="badge badge-info">${escapeHtml(r.name)} (${r.criteria_type.toUpperCase()})</span>`)
        .join("");
    }
  } catch (err) {
    console.error("Erro ao carregar dashboard:", err);
  }
}

/* =========================================================================
   2. INTEGRAÇÃO COM WHATSAPP
   ========================================================================= */
function updateWhatsAppBadges(wa) {
  state.whatsapp = wa;
  const waBadge = document.getElementById("waStatusBadge");
  const waText = document.getElementById("waStatusText");
  const dashState = document.getElementById("dashWaState");
  const dashGroups = document.getElementById("dashWaGroups");
  const dashSelected = document.getElementById("dashWaSelected");
  const dashMsg = document.getElementById("dashWaMsg");
  const waHeaderState = document.getElementById("waHeaderState");
  const waDetailMsg = document.getElementById("waDetailMessage");
  const btnConnect = document.getElementById("btnWaConnect");
  const btnDisconnect = document.getElementById("btnWaDisconnect");

  dashGroups.textContent = wa.groups_count || 0;
  dashSelected.textContent = wa.selected_group_id || "Nenhum";
  dashMsg.textContent = wa.message;
  waDetailMsg.textContent = wa.message;

  if (wa.state === "connected") {
    waBadge.className = "status-badge online";
    waText.textContent = "WhatsApp: Conectado";
    dashState.innerHTML = '<span class="text-success">Conectado</span>';
    waHeaderState.className = "badge badge-success";
    waHeaderState.textContent = "Conectado";
    btnConnect.disabled = true;
    btnDisconnect.disabled = false;
  } else if (wa.state === "awaiting_auth") {
    waBadge.className = "status-badge pending";
    waText.textContent = "WhatsApp: Aguardando QR";
    dashState.innerHTML = '<span class="text-warning">Aguardando Leitura de QR</span>';
    waHeaderState.className = "badge badge-warning";
    waHeaderState.textContent = "Aguardando Autenticação";
    btnConnect.disabled = true;
    btnDisconnect.disabled = false;
  } else if (wa.state === "unavailable") {
    waBadge.className = "status-badge offline";
    waText.textContent = "WhatsApp: Indisponível";
    dashState.innerHTML = '<span class="text-warning">Dependência Ausente</span>';
    waHeaderState.className = "badge badge-warning";
    waHeaderState.textContent = "Driver Indisponível";
    btnConnect.disabled = false;
    btnDisconnect.disabled = true;
  } else {
    waBadge.className = "status-badge offline";
    waText.textContent = "WhatsApp: Desconectado";
    dashState.innerHTML = '<span class="text-muted">Desconectado</span>';
    waHeaderState.className = "badge badge-danger";
    waHeaderState.textContent = "Desconectado";
    btnConnect.disabled = false;
    btnDisconnect.disabled = true;
  }
}

async function checkWhatsAppStatus() {
  try {
    const res = await fetch("/api/whatsapp/status");
    if (!res.ok) return;
    const wa = await res.json();
    updateWhatsAppBadges(wa);
  } catch (err) {
    console.error("Erro ao verificar status do WhatsApp:", err);
  }
}

async function connectWhatsApp() {
  try {
    showAlert("Iniciando conexão com o WhatsApp Web...", "info");
    const res = await fetch("/api/whatsapp/connect", { method: "POST" });
    const data = await res.json();
    updateWhatsAppBadges(data);
    showAlert(data.message, data.state === "connected" ? "success" : "info");
  } catch (err) {
    showAlert("Falha ao comunicar com o serviço do WhatsApp: " + err.message, "danger");
  }
}

async function disconnectWhatsApp() {
  try {
    const res = await fetch("/api/whatsapp/disconnect", { method: "POST" });
    const data = await res.json();
    showAlert(data.message, "info");
    checkWhatsAppStatus();
  } catch (err) {
    showAlert("Erro ao desconectar: " + err.message, "danger");
  }
}

async function loadWhatsAppGroups() {
  const container = document.getElementById("waGroupsContainer");
  try {
    const res = await fetch("/api/whatsapp/groups");
    const groups = await res.json();
    if (!groups || groups.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">👥</div>
          <p>Nenhum grupo listado.</p>
          <span class="text-sm text-muted">
            ${state.whatsapp.state === "connected" ? "Nenhum grupo com imagens recentes encontrado." : "Conecte sua conta do WhatsApp para carregar seus grupos reais."}
          </span>
        </div>`;
      return;
    }
    container.innerHTML = groups
      .map(
        (g) => `
      <div class="info-row items-center">
        <div>
          <strong>${escapeHtml(g.name)}</strong>
          <div class="text-xs text-muted">ID: ${escapeHtml(g.id)}</div>
        </div>
        <button class="btn btn-sm btn-secondary" onclick="selectWhatsAppGroup('${g.id}')">Selecionar</button>
      </div>`
      )
      .join("");
  } catch (err) {
    container.innerHTML = `<p class="text-danger text-sm">Erro ao listar grupos: ${escapeHtml(err.message)}</p>`;
  }
}

async function selectWhatsAppGroup(groupId) {
  try {
    const res = await fetch("/api/whatsapp/select-group", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ group_id: groupId }),
    });
    if (res.ok) {
      showAlert(`Grupo selecionado com sucesso.`, "success");
      checkWhatsAppStatus();
    }
  } catch (err) {
    showAlert("Erro ao selecionar grupo: " + err.message, "danger");
  }
}

/* =========================================================================
   3. REGRAS DE IMAGENS (CRUD & TOGGLE)
   ========================================================================= */
async function loadRules() {
  const container = document.getElementById("rulesListContainer");
  try {
    const res = await fetch("/api/rules");
    if (!res.ok) throw new Error("Falha ao carregar regras.");
    const rules = await res.json();
    state.rules = rules;

    if (!rules || rules.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">⚙️</div>
          <p>Nenhuma regra cadastrada.</p>
          <span class="text-sm text-muted">Clique em "Nova Regra" acima para configurar filtros de imagens.</span>
        </div>`;
      return;
    }

    container.innerHTML = rules
      .map((r) => {
        const typeLabels = {
          text: "📝 Textual",
          logo: "🏷️ Logotipo",
          object: "🔍 Objeto",
          combination: "🔀 Combinada",
        };
        const typeLabel = typeLabels[r.criteria_type] || r.criteria_type;
        const configDesc = getRuleConfigSummary(r);

        return `
        <div class="rule-item-card ${r.is_active ? "" : "opacity-50"}">
          <div class="rule-info">
            <h4>
              ${escapeHtml(r.name)}
              <span class="badge ${r.is_active ? "badge-success" : "badge-secondary"}">
                ${r.is_active ? "Ativa" : "Desativada"}
              </span>
              <span class="badge badge-info">${typeLabel}</span>
              <span class="badge">${r.logical_operator}</span>
            </h4>
            <div class="rule-meta">
              <span>${configDesc}</span> •
              <span>Confiança Mínima: <strong>${(r.confidence_threshold * 100).toFixed(0)}%</strong></span>
            </div>
          </div>
          <div class="rule-actions">
            <button class="btn btn-sm ${r.is_active ? "btn-secondary" : "btn-primary"}" onclick="toggleRule('${r.id}')">
              ${r.is_active ? "Desativar" : "Ativar"}
            </button>
            <button class="btn btn-sm btn-secondary" onclick="openEditRuleModal('${r.id}')">✏️ Editar</button>
            <button class="btn btn-sm btn-danger" onclick="deleteRule('${r.id}')">🗑️ Excluir</button>
          </div>
        </div>`;
      })
      .join("");
  } catch (err) {
    container.innerHTML = `<p class="text-danger">Erro ao carregar regras: ${escapeHtml(err.message)}</p>`;
  }
}

function getRuleConfigSummary(rule) {
  const cfg = rule.specific_config || {};
  if (rule.criteria_type === "text") {
    const kws = cfg.keywords || [];
    return `Palavras (${cfg.match_mode || "any"}): [${kws.map(escapeHtml).join(", ")}]`;
  } else if (rule.criteria_type === "logo") {
    return `Logotipo de referência: ${escapeHtml(cfg.reference_logo_path || "Não configurado")}`;
  } else if (rule.criteria_type === "object") {
    return `Objeto visual descrito: "${escapeHtml(cfg.object_description || "")}"`;
  }
  return "Combinação de múltiplos critérios";
}

function openNewRuleModal() {
  document.getElementById("ruleModalTitle").textContent = "Nova Regra de Imagem";
  document.getElementById("ruleId").value = "";
  document.getElementById("ruleName").value = "";
  document.getElementById("ruleCriteriaType").value = "text";
  document.getElementById("ruleLogicalOp").value = "OR";
  document.getElementById("ruleConfidence").value = 0.5;
  document.getElementById("ruleConfidenceVal").textContent = "50%";
  document.getElementById("ruleKeywords").value = "";
  document.getElementById("ruleMatchMode").value = "any";
  document.getElementById("ruleCaseSensitive").checked = false;
  document.getElementById("ruleLogoPath").value = "";
  document.getElementById("ruleObjectDesc").value = "";
  document.getElementById("ruleIsActive").checked = true;
  handleCriteriaTypeChange();
  document.getElementById("ruleModal").classList.remove("hidden");
}

function openEditRuleModal(ruleId) {
  const rule = state.rules.find((r) => r.id === ruleId);
  if (!rule) return;
  document.getElementById("ruleModalTitle").textContent = "Editar Regra de Imagem";
  document.getElementById("ruleId").value = rule.id;
  document.getElementById("ruleName").value = rule.name;
  document.getElementById("ruleCriteriaType").value = rule.criteria_type;
  document.getElementById("ruleLogicalOp").value = rule.logical_operator;
  document.getElementById("ruleConfidence").value = rule.confidence_threshold;
  document.getElementById("ruleConfidenceVal").textContent = (rule.confidence_threshold * 100).toFixed(0) + "%";
  document.getElementById("ruleIsActive").checked = rule.is_active;

  const cfg = rule.specific_config || {};
  document.getElementById("ruleKeywords").value = (cfg.keywords || []).join(", ");
  document.getElementById("ruleMatchMode").value = cfg.match_mode || "any";
  document.getElementById("ruleCaseSensitive").checked = !!cfg.case_sensitive;
  document.getElementById("ruleLogoPath").value = cfg.reference_logo_path || "";
  document.getElementById("ruleObjectDesc").value = cfg.object_description || "";

  handleCriteriaTypeChange();
  document.getElementById("ruleModal").classList.remove("hidden");
}

function closeRuleModal() {
  document.getElementById("ruleModal").classList.add("hidden");
}

function handleCriteriaTypeChange() {
  const type = document.getElementById("ruleCriteriaType").value;
  document.getElementById("cfgTextPanel").classList.toggle("hidden", type !== "text");
  document.getElementById("cfgLogoPanel").classList.toggle("hidden", type !== "logo");
  document.getElementById("cfgObjectPanel").classList.toggle("hidden", type !== "object");
}

async function handleSaveRule(event) {
  event.preventDefault();
  const ruleId = document.getElementById("ruleId").value;
  const name = document.getElementById("ruleName").value.trim();
  const criteriaType = document.getElementById("ruleCriteriaType").value;
  const logicalOp = document.getElementById("ruleLogicalOp").value;
  const confidence = parseFloat(document.getElementById("ruleConfidence").value);
  const isActive = document.getElementById("ruleIsActive").checked;

  let specificConfig = {};
  if (criteriaType === "text") {
    const rawKws = document.getElementById("ruleKeywords").value;
    const kws = rawKws.split(",").map((s) => s.trim()).filter(Boolean);
    specificConfig = {
      keywords: kws,
      match_mode: document.getElementById("ruleMatchMode").value,
      case_sensitive: document.getElementById("ruleCaseSensitive").checked,
    };
  } else if (criteriaType === "logo") {
    specificConfig = {
      reference_logo_path: document.getElementById("ruleLogoPath").value.trim(),
    };
  } else if (criteriaType === "object") {
    specificConfig = {
      object_description: document.getElementById("ruleObjectDesc").value.trim(),
    };
  }

  const payload = {
    name,
    criteria_type: criteriaType,
    specific_config: specificConfig,
    is_active: isActive,
    logical_operator: logicalOp,
    confidence_threshold: confidence,
  };

  try {
    let res;
    if (ruleId) {
      res = await fetch(`/api/rules/${ruleId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      res = await fetch("/api/rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Erro ao salvar regra.");
    }

    closeRuleModal();
    loadRules();
    loadDashboard();
    showAlert(ruleId ? "Regra atualizada com sucesso." : "Nova regra criada com sucesso.", "success");
  } catch (err) {
    alert("Erro: " + err.message);
  }
}

async function toggleRule(ruleId) {
  try {
    const res = await fetch(`/api/rules/${ruleId}/toggle`, { method: "PATCH" });
    if (!res.ok) throw new Error("Erro ao alternar estado da regra.");
    loadRules();
    loadDashboard();
  } catch (err) {
    showAlert("Falha: " + err.message, "danger");
  }
}

async function deleteRule(ruleId) {
  if (!confirm("Deseja realmente excluir esta regra?")) return;
  try {
    const res = await fetch(`/api/rules/${ruleId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Erro ao excluir regra.");
    loadRules();
    loadDashboard();
    showAlert("Regra excluída.", "info");
  } catch (err) {
    showAlert("Falha ao excluir: " + err.message, "danger");
  }
}

/* =========================================================================
   4. CONFIGURAÇÃO DA PASTA DE DESTINO
   ========================================================================= */
async function loadDestination() {
  try {
    const res = await fetch("/api/destination");
    const data = await res.json();
    state.destination = data;
    document.getElementById("destInputPath").value = data.path;
    showDestinationValidation(data.is_valid, data.message);
  } catch (err) {
    console.error("Erro ao carregar destino:", err);
  }
}

async function testDestinationPath() {
  const path = document.getElementById("destInputPath").value.trim();
  if (!path) {
    showDestinationValidation(false, "Informe um caminho para testar.");
    return;
  }
  try {
    const res = await fetch("/api/destination/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    const data = await res.json();
    showDestinationValidation(data.is_valid, data.message);
  } catch (err) {
    showDestinationValidation(false, "Erro ao validar caminho: " + err.message);
  }
}

async function handleSaveDestination(event) {
  event.preventDefault();
  const path = document.getElementById("destInputPath").value.trim();
  try {
    const res = await fetch("/api/destination", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Erro ao salvar.");
    showDestinationValidation(true, data.message);
    showAlert("Pasta de destino salva e validada com sucesso.", "success");
    loadDashboard();
  } catch (err) {
    showDestinationValidation(false, err.message);
  }
}

function resetToDefaultDestination() {
  document.getElementById("destInputPath").value = "";
  handleSaveDestination(new Event("submit"));
}

function showDestinationValidation(isValid, message) {
  const box = document.getElementById("destValidationResult");
  box.classList.remove("hidden");
  if (isValid) {
    box.className = "notice-box text-sm";
    box.innerHTML = `<strong>✅ Sucesso:</strong> ${escapeHtml(message)}`;
  } else {
    box.className = "notice-box text-sm border-danger";
    box.innerHTML = `<strong class="text-danger">❌ Problema identificado:</strong> ${escapeHtml(message)}`;
  }
}

/* =========================================================================
   5. PRÉVIA E PROCESSAMENTO
   ========================================================================= */
function handleSourceChange() {
  const source = document.getElementById("sourceSelect").value;
  document.getElementById("sampleUploadArea").classList.toggle("hidden", source !== "sample");
}

async function runPreview() {
  const sourceMode = document.getElementById("sourceSelect").value;
  showAlert("Gerando prévia da avaliação das imagens...", "info");
  try {
    const res = await fetch("/api/processing/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_mode: sourceMode }),
    });
    if (!res.ok) throw new Error("Falha ao gerar prévia.");
    const items = await res.json();
    renderResults(items);
    showAlert(`Prévia gerada com sucesso (${items.length} imagens avaliadas).`, "success");
  } catch (err) {
    showAlert("Erro na prévia: " + err.message, "danger");
  }
}

async function startProcessing() {
  const sourceMode = document.getElementById("sourceSelect").value;
  try {
    const res = await fetch("/api/processing/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_mode: sourceMode }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Erro ao iniciar processamento.");
    }

    document.getElementById("processingProgressArea").classList.remove("hidden");
    document.getElementById("btnStartProcessing").classList.add("hidden");
    document.getElementById("btnCancelProcessing").classList.remove("hidden");
    showAlert("Processamento iniciado em segundo plano.", "info");

    startProgressPolling();
  } catch (err) {
    showAlert("Erro: " + err.message, "danger");
  }
}

async function cancelProcessing() {
  try {
    const res = await fetch("/api/processing/cancel", { method: "POST" });
    const data = await res.json();
    showAlert(data.message, "warning");
  } catch (err) {
    showAlert("Erro ao cancelar: " + err.message, "danger");
  }
}

function startProgressPolling() {
  if (state.pollInterval) clearInterval(state.pollInterval);
  state.pollInterval = setInterval(async () => {
    try {
      const res = await fetch("/api/processing/status");
      const prog = await res.json();

      document.getElementById("progressMessage").textContent = prog.message;
      document.getElementById("progProcessed").textContent = prog.processed;
      document.getElementById("progTotal").textContent = prog.total;
      document.getElementById("progApproved").textContent = prog.approved;
      document.getElementById("progSaved").textContent = prog.saved;
      document.getElementById("progRejected").textContent = prog.rejected;

      const percent = prog.total > 0 ? Math.round((prog.processed / prog.total) * 100) : 0;
      document.getElementById("progressBar").style.width = `${percent}%`;
      document.getElementById("progressPercent").textContent = `${percent}%`;

      if (prog.status === "completed" || prog.status === "cancelled" || prog.status === "error") {
        clearInterval(state.pollInterval);
        state.pollInterval = null;
        document.getElementById("btnStartProcessing").classList.remove("hidden");
        document.getElementById("btnCancelProcessing").classList.add("hidden");

        // Carregar resultados finais e atualizar métricas
        loadFinalResults();
        loadDashboard();
      }
    } catch (err) {
      console.error("Erro no polling de progresso:", err);
    }
  }, 1000);
}

async function loadFinalResults() {
  try {
    const res = await fetch("/api/processing/results");
    const items = await res.json();
    renderResults(items);
  } catch (err) {
    console.error("Erro ao carregar resultados finais:", err);
  }
}

function renderResults(results) {
  const grid = document.getElementById("resultsGrid");
  document.getElementById("resultsCount").textContent = results.length;

  if (!results || results.length === 0) {
    grid.innerHTML = `
      <div class="empty-state col-span-full">
        <div class="empty-icon">🖼️</div>
        <p>Nenhuma imagem encontrada na origem selecionada.</p>
        <span class="text-sm text-muted">Adicione imagens à pasta de amostras ou selecione um grupo válido do WhatsApp.</span>
      </div>`;
    return;
  }

  grid.innerHTML = results
    .map((r) => {
      const isApproved = r.evaluation.approved;
      const statusBadge = isApproved
        ? '<span class="badge badge-success result-badge">Aprovada</span>'
        : '<span class="badge badge-warning result-badge">Rejeitada</span>';

      const thumbImg = r.item.thumbnail_url
        ? `<img src="${r.item.thumbnail_url}" alt="${escapeHtml(r.item.filename)}" class="result-thumb">`
        : '<div class="text-xs text-muted">Sem miniatura</div>';

      const savedNotice = r.saved
        ? `<div class="result-saved-path">💾 Salvo em: ${escapeHtml(r.saved_path)}</div>`
        : r.is_duplicate
        ? `<div class="result-saved-path text-warning">⚠️ Imagem idêntica já salva anteriormente</div>`
        : r.error_message
        ? `<div class="result-saved-path text-danger">⚠️ ${escapeHtml(r.error_message)}</div>`
        : "";

      return `
      <div class="result-card ${isApproved ? "approved" : "rejected"}">
        <div class="result-thumb-box">
          ${thumbImg}
          ${statusBadge}
        </div>
        <div class="result-body">
          <div>
            <div class="result-filename">${escapeHtml(r.item.filename)}</div>
            <div class="result-source">Origem: ${escapeHtml(r.item.source_group)} ${r.item.message_date ? "• " + r.item.message_date : ""}</div>
            ${r.item.caption ? `<div class="text-xs text-muted mb-2"><em>"${escapeHtml(r.item.caption)}"</em></div>` : ""}
          </div>
          <div>
            <div class="result-justification">
              <strong>Motivo:</strong> ${escapeHtml(r.evaluation.justification)}
            </div>
            ${savedNotice}
          </div>
        </div>
      </div>`;
    })
    .join("");
}

async function uploadSampleFile(event) {
  const file = event.target.files[0];
  if (!file) return;

  const caption = prompt("Legenda opcional para a imagem de teste (para testar regras textuais):", "");
  const formData = new FormData();
  formData.append("file", file);
  formData.append("caption", caption || "");

  showAlert("Enviando imagem para a pasta de amostras...", "info");
  try {
    const res = await fetch("/api/processing/samples/upload", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Erro no envio.");
    showAlert(data.message, "success");
    runPreview();
  } catch (err) {
    showAlert("Falha no upload: " + err.message, "danger");
  }
}

/* =========================================================================
   6. HISTÓRICO DE EXECUÇÕES
   ========================================================================= */
async function loadHistory() {
  const tbody = document.getElementById("historyTableBody");
  try {
    const res = await fetch("/api/processing/history");
    const records = await res.json();
    if (!records || records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">Nenhum registro de execução encontrado.</td></tr>`;
      return;
    }

    tbody.innerHTML = records
      .map(
        (rec) => `
      <tr>
        <td>${escapeHtml(rec.created_at.replace("T", " ").substring(0, 19))}</td>
        <td><strong>${escapeHtml(rec.source_group)}</strong></td>
        <td>${rec.analyzed_count}</td>
        <td class="text-success">${rec.approved_count}</td>
        <td class="text-warning">${rec.rejected_count}</td>
        <td class="text-info">${rec.saved_count}</td>
        <td class="${rec.errors_count > 0 ? "text-danger" : ""}">${rec.errors_count}</td>
        <td class="text-xs text-muted">${escapeHtml(rec.details)}</td>
      </tr>`
      )
      .join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-danger">Erro ao carregar histórico: ${escapeHtml(err.message)}</td></tr>`;
  }
}

// Utilitário de escape de HTML
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
