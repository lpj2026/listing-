"use strict";

const BASE = (window.location.pathname.startsWith("/listing") ? "/listing" : "");

async function apiPost(path, payload) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok || data.code !== 1) throw new Error(data.message || "Request failed");
  return data;
}

function showToast(msg) {
  const t = document.querySelector("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 2600);
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

// ── Mode Switching ───────────────────────────────────────────

let currentMode = "generate";
document.querySelectorAll(".mode-tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    currentMode = btn.dataset.mode;
    document.querySelectorAll(".mode-tab").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelector("#mode-generate").classList.toggle("hidden", currentMode !== "generate");
    document.querySelector("#mode-score").classList.toggle("hidden", currentMode !== "score");
  });
});

// ── Generator ────────────────────────────────────────────────

document.querySelector("#runGenerate").addEventListener("click", async () => {
  const name = document.querySelector("#genName").value.trim();
  if (!name) { showToast("请填写产品名称"); return; }

  const positioning = [];
  document.querySelectorAll('input[name="positioning"]:checked').forEach((cb) => positioning.push(cb.value));

  const payload = {
    product_name: name,
    category: document.querySelector("#genCategory").value,
    price: parseFloat(document.querySelector("#genPrice").value) || null,
    material: document.querySelector("#genMaterial").value.trim(),
    process: document.querySelector("#genProcess").value.trim(),
    spec1_name: document.querySelector("#genSpec1Name").value.trim(),
    spec1_value: document.querySelector("#genSpec1Value").value.trim(),
    spec2_name: document.querySelector("#genSpec2Name").value.trim(),
    spec2_value: document.querySelector("#genSpec2Value").value.trim(),
    differentiator: document.querySelector("#genDiff").value.trim(),
    audience: document.querySelector("#genAudience").value.trim(),
    competitor_asin: document.querySelector("#genAsin").value.trim(),
    positioning,
  };

  const btn = document.querySelector("#runGenerate");
  const status = document.querySelector("#genStatus");
  btn.disabled = true;
  status.textContent = "AI 正在分析产品并生成多套方案...";
  status.classList.remove("hidden");

  try {
    const result = await apiPost("/api/listing/generate", payload);
    renderPlans(result.data);
    status.textContent = "";
    status.classList.add("hidden");
  } catch (e) {
    showToast(e.message);
    status.textContent = "";
    status.classList.add("hidden");
  } finally {
    btn.disabled = false;
  }
});

function renderPlans(data) {
  const container = document.querySelector("#plansContainer");
  container.classList.remove("hidden");
  const plans = data.plans || [];
  if (!plans.length) { container.innerHTML = '<div class="card"><p>未生成任何方案</p></div>'; return; }

  const strategyIcons = { "专业性能型": "⚙️", "高性价比实用型": "💰", "性价比实用型": "💰", "高端品质型": "👑", "环保健康型": "🌿" };

  container.innerHTML = plans.map((plan, i) => `
    <div class="plan-card">
      <div class="plan-header">
        <span class="plan-num">${String.fromCharCode(65 + i)}</span>
        <span class="plan-strategy">${strategyIcons[plan.strategy] || "📋"} ${escapeHtml(plan.strategy || "方案 " + (i + 1))}</span>
      </div>
      ${plan.reasoning ? `<div class="plan-reasoning"><strong>策略逻辑：</strong>${escapeHtml(plan.reasoning)}</div>` : ""}
      <div class="plan-meta">
        ${plan.buyer_profile ? `<span><strong>目标买家：</strong>${escapeHtml(plan.buyer_profile)}</span>` : ""}
        ${plan.expected_benefit ? `<span><strong>预期效果：</strong>${escapeHtml(plan.expected_benefit)}</span>` : ""}
      </div>
      <div class="plan-body">
        <div class="plan-field">
          <div class="plan-field-label">标题</div>
          <div class="plan-field-value">${escapeHtml(plan.title || "")}</div>
        </div>
        ${(plan.bullets || []).map((b, j) => `
          <div class="plan-field">
            <div class="plan-field-label">Bullet Point ${j + 1}</div>
            <div class="plan-field-value">${escapeHtml(b || "")}</div>
          </div>
        `).join("")}
        <div class="plan-field">
          <div class="plan-field-label">产品描述</div>
          <div class="plan-field-value">${escapeHtml(plan.description || "")}</div>
        </div>
        <div class="plan-field">
          <div class="plan-field-label">Search Terms</div>
          <div class="plan-field-value">${escapeHtml(plan.search_terms || "")}</div>
        </div>
      </div>
      <div class="plan-actions">
        <button class="btn primary btn-sm apply-plan" data-plan='${JSON.stringify({title: plan.title, bullets: plan.bullets, description: plan.description, search_terms: plan.search_terms}).replace(/'/g, "&#39;")}'>选用此方案 → 填入产品表单</button>
      </div>
    </div>
  `).join("");

  // Bind apply buttons
  container.querySelectorAll(".apply-plan").forEach((btn) => {
    btn.addEventListener("click", () => {
      const plan = JSON.parse(btn.dataset.plan);
      localStorage.setItem("listing_apply", JSON.stringify(plan));
      showToast("方案已暂存，切换到产品页将自动提示填入");
      setTimeout(() => { window.location.href = "create-product"; }, 800);
    });
  });
}

// ── Scorer ───────────────────────────────────────────────────

document.querySelector("#runScore").addEventListener("click", async () => {
  const title = document.querySelector("#scoreTitle").value.trim();
  if (!title) { showToast("请填写标题"); return; }

  const payload = {
    title,
    bullets: [
      document.querySelector("#scoreB1").value.trim(),
      document.querySelector("#scoreB2").value.trim(),
      document.querySelector("#scoreB3").value.trim(),
      document.querySelector("#scoreB4").value.trim(),
      document.querySelector("#scoreB5").value.trim(),
    ].filter(Boolean),
    description: document.querySelector("#scoreDesc").value.trim(),
    search_terms: document.querySelector("#scoreST").value.trim(),
    image_count: parseInt(document.querySelector("#scoreImgs").value) || 0,
    price: parseFloat(document.querySelector("#scoreCat").value) || null,
    category: document.querySelector("#scoreCat").value.trim(),
  };

  const btn = document.querySelector("#runScore");
  const status = document.querySelector("#scoreStatus");
  btn.disabled = true;
  status.textContent = "AI 正在逐项诊断...";
  status.classList.remove("hidden");

  try {
    const result = await apiPost("/api/listing/score", payload);
    renderDiagnosis(result.data);
    status.textContent = "";
    status.classList.add("hidden");
  } catch (e) {
    showToast(e.message);
    status.textContent = "";
    status.classList.add("hidden");
  } finally {
    btn.disabled = false;
  }
});

function renderDiagnosis(data) {
  const container = document.querySelector("#diagnosisContainer");
  container.classList.remove("hidden");

  const scoreColor = data.overall_score >= 85 ? "#389e0d" : data.overall_score >= 70 ? "#2185d0" : data.overall_score >= 55 ? "#d48806" : "#cf1322";

  const dimLabels = { title: "标题质量", bullets: "Bullet Points", description: "描述质量", keywords: "关键词与搜索", compliance: "合规与展示" };

  const dimsHtml = Object.entries(data.dimensions || {}).map(([key, dim]) => {
    const pct = Math.round((dim.score / dim.max) * 100);
    const barColor = pct >= 80 ? "#389e0d" : pct >= 60 ? "#d48806" : "#cf1322";
    const positivesHtml = (dim.positives || []).length
      ? `<div class="dim-positives">${(dim.positives || []).join("；")}</div>` : "";
    const issuesHtml = (dim.issues || []).map((issue) => `
      <div class="dim-issue">
        <div class="issue-title">${escapeHtml(issue.issue || "")}</div>
        <div class="issue-detail"><span class="issue-detail-label">为什么重要</span><span class="issue-detail-value">${escapeHtml(issue.why_matters || "")}</span></div>
        <div class="issue-detail"><span class="issue-detail-label">如何改进</span><span class="issue-detail-value">${escapeHtml(issue.how_to_fix || "")}</span></div>
        <div class="issue-detail"><span class="issue-detail-label">预计效果</span><span class="issue-detail-value">${escapeHtml(issue.expected_gain || "")}</span></div>
      </div>
    `).join("");
    return `<div class="dim-card">
      <div class="dim-header">
        <span class="dim-name">${dimLabels[key] || key}</span>
        <span class="dim-score-badge" style="background:${barColor}20;color:${barColor}">${dim.score}/${dim.max} (${pct}%)</span>
      </div>
      ${positivesHtml}
      <div class="dim-issues">${issuesHtml}</div>
    </div>`;
  }).join("");

  const priorityHtml = (data.top_priority || []).length
    ? `<div class="diag-priority"><h3>⚡ 优先处理</h3><ol>${data.top_priority.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ol></div>` : "";

  // Save current listing data for optimize
  container._listingData = {
    title: document.querySelector("#scoreTitle").value.trim(),
    bullets: [1,2,3,4,5].map(i => document.querySelector("#scoreB" + i)?.value?.trim() || "").filter(Boolean),
    description: document.querySelector("#scoreDesc").value.trim(),
    search_terms: document.querySelector("#scoreST").value.trim(),
    category: document.querySelector("#scoreCat").value.trim(),
  };
  container._scoreResult = data;

  container.innerHTML = `
    <div class="diag-header" style="border-color:${scoreColor}">
      <div class="diag-score" style="color:${scoreColor}">${data.overall_score}<span style="font-size:16px;color:#999">/100</span></div>
      <div class="diag-grade" style="color:${scoreColor}">${escapeHtml(data.overall_grade || "")}</div>
      <div class="diag-summary">${escapeHtml(data.overall_summary || "")}</div>
    </div>
    ${priorityHtml}
    ${dimsHtml}
    <div class="optimize-bar">
      <button class="btn primary btn-lg" id="runOptimize">根据诊断结果生成优化方案</button>
      <p class="section-desc" style="margin-top:8px">AI 将针对每个问题给出为什么优化、优化能带来什么好处、以及优化后的文案</p>
    </div>
    <div id="optimizeResult" class="hidden"></div>
  `;

  // Bind optimize button
  document.querySelector("#runOptimize")?.addEventListener("click", async () => {
    const btn = document.querySelector("#runOptimize");
    btn.disabled = true;
    btn.textContent = "AI 正在生成针对性优化方案...";
    try {
      const result = await apiPost("/api/listing/optimize", {
        listing_data: container._listingData,
        scoring_result: container._scoreResult,
      });
      renderOptimizations(result.data);
    } catch (e) {
      showToast(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "根据诊断结果生成优化方案";
    }
  });
}

function renderOptimizations(data) {
  const container = document.querySelector("#optimizeResult");
  container.classList.remove("hidden");

  const optsHtml = (data.optimizations || []).map((opt, i) => `
    <div class="opt-card">
      <div class="opt-header">
        <span class="opt-num">#${i + 1}</span>
        <span class="opt-target">${escapeHtml(opt.target || "")}</span>
      </div>
      <div class="opt-issue">当前问题：${escapeHtml(opt.issue_summary || "")}</div>
      <div class="opt-detail">
        <div class="opt-detail-row"><strong>为什么优化：</strong>${escapeHtml(opt.why_optimize || "")}</div>
        <div class="opt-detail-row"><strong>预期效果：</strong>${escapeHtml(opt.expected_benefit || "")}</div>
      </div>
      ${opt.optimized_content ? `<div class="opt-content"><strong>优化后文案：</strong><div>${escapeHtml(opt.optimized_content)}</div></div>` : ""}
    </div>
  `).join("");

  const listing = data.optimized_listing || {};
  const applyHtml = listing.title ? `
    <div class="opt-apply-card">
      <h3>优化后的完整 Listing</h3>
      <div class="plan-field"><div class="plan-field-label">标题</div><div class="plan-field-value">${escapeHtml(listing.title || "")}</div></div>
      ${(listing.bullets || []).map((b, j) => `<div class="plan-field"><div class="plan-field-label">Bullet ${j + 1}</div><div class="plan-field-value">${escapeHtml(b || "")}</div></div>`).join("")}
      <div class="plan-field"><div class="plan-field-label">描述</div><div class="plan-field-value">${escapeHtml(listing.description || "")}</div></div>
      <div class="plan-field"><div class="plan-field-label">Search Terms</div><div class="plan-field-value">${escapeHtml(listing.search_terms || "")}</div></div>
      <button class="btn primary apply-optimized" data-listing='${JSON.stringify(listing).replace(/'/g, "&#39;")}'>选用优化方案 → 填入产品表单</button>
    </div>
  ` : "";

  container.innerHTML = `
    ${data.overall_strategy ? `<div class="opt-strategy"><strong>整体优化策略：</strong>${escapeHtml(data.overall_strategy)}</div>` : ""}
    <h3 style="margin:16px 0 10px;font-size:15px">逐项优化建议</h3>
    ${optsHtml}
    ${applyHtml}
  `;

  container.querySelector(".apply-optimized")?.addEventListener("click", () => {
    const listing = JSON.parse(container.querySelector(".apply-optimized").dataset.listing);
    localStorage.setItem("listing_apply", JSON.stringify(listing));
    showToast("优化方案已暂存，切换到产品页将自动填入");
    setTimeout(() => { window.location.href = "create-product"; }, 800);
  });
}

// ── Import from product page ─────────────────────────────────

(function checkImport() {
  const raw = localStorage.getItem("listing_import_data");
  if (!raw) return;
  let data;
  try { data = JSON.parse(raw); } catch (e) { return; }
  if (!data || !Object.keys(data).length) return;

  localStorage.removeItem("listing_import_data");

  // Build a summary of what was imported
  const fields = [];
  if (data.item_name) fields.push("标题");
  if (data.product_type) fields.push("产品类型");
  if (data.brand) fields.push("品牌");
  if (data.manufacturer) fields.push("制造商");
  for (let i = 1; i <= 5; i++) if (data["bullet_point_" + i]) { fields.push("Bullet Points"); break; }
  if (data.product_description) fields.push("描述");
  if (data.generic_keyword) fields.push("Search Terms");

  // Auto-fill scorer form
  if (data.item_name) document.querySelector("#scoreTitle").value = data.item_name;
  for (let i = 1; i <= 5; i++) {
    const el = document.querySelector("#scoreB" + i);
    if (el && data["bullet_point_" + i]) el.value = data["bullet_point_" + i];
  }
  if (data.product_description) document.querySelector("#scoreDesc").value = data.product_description;
  if (data.generic_keyword) document.querySelector("#scoreST").value = data.generic_keyword;
  if (data.product_type) document.querySelector("#scoreCat").value = data.product_type;

  // Also pre-fill generator
  if (data.item_name) document.querySelector("#genName").value = data.item_name;
  if (data.product_type) document.querySelector("#genCategory").value = data.product_type;
  if (data.generic_keyword) document.querySelector("#genDiff").value = "关键词: " + data.generic_keyword;

  // Switch to scorer and auto-run
  const scoreTab = document.querySelector('.mode-tab[data-mode="score"]');
  if (scoreTab) scoreTab.click();

  showToast("已导入 " + fields.length + " 项产品数据，点击「AI 详细诊断」开始评分");

  // Add import summary banner
  const banner = document.createElement("div");
  banner.className = "import-banner";
  banner.innerHTML = "<strong>来自产品页导入</strong> 已自动填入评分表单（" + fields.join("、") + "）。评分后可切换到「生成文案」获取针对性优化方案。";
  const card = document.querySelector("#mode-score .card");
  if (card) card.insertBefore(banner, card.firstChild);
})();

