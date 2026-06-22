"use strict";

const BASE = (window.location.pathname.startsWith("/listing") ? "/listing" : "");
let imagesLinked = false;
let mskuLinked = false;
let importedProductContext = {};

function createProductHref() {
  const path = window.location.pathname || "";
  if (path.startsWith("/listing")) return "/listing/create-product";
  return "create-product";
}

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

// ── Scorer ───────────────────────────────────────────────────

function getScorePayload() {
  const priceRaw = document.querySelector("#scorePrice")?.value?.trim();
  const price = priceRaw ? parseFloat(priceRaw) : null;
  const imgsRaw = document.querySelector("#scoreImgs")?.value?.trim();
  let image_count = null;
  if (imgsRaw !== "" && imgsRaw != null) {
    const n = parseInt(imgsRaw, 10);
    if (Number.isFinite(n) && n >= 0) image_count = n;
  }
  return {
    title: document.querySelector("#scoreTitle").value.trim(),
    bullets: [
      document.querySelector("#scoreB1").value.trim(),
      document.querySelector("#scoreB2").value.trim(),
      document.querySelector("#scoreB3").value.trim(),
      document.querySelector("#scoreB4").value.trim(),
      document.querySelector("#scoreB5").value.trim(),
    ].filter(Boolean),
    description: document.querySelector("#scoreDesc").value.trim(),
    search_terms: document.querySelector("#scoreST").value.trim(),
    image_count,
    images_linked: imagesLinked,
    msku_linked: mskuLinked,
    price: Number.isFinite(price) ? price : null,
    product_type: document.querySelector("#scoreCat").value.trim(),
    category: document.querySelector("#scoreCat").value.trim(),
    category_path: document.querySelector("#scoreCatPath")?.value?.trim() || "",
    brand: document.querySelector("#scoreBrand")?.value?.trim() || "",
    manufacturer: document.querySelector("#scoreManufacturer")?.value?.trim()
      || document.querySelector("#scoreBrand")?.value?.trim() || "",
    msku: document.querySelector("#scoreMsku")?.value?.trim() || "",
    seller_sku: document.querySelector("#scoreMsku")?.value?.trim() || "",
    parent_sku: document.querySelector("#scoreMsku")?.value?.trim() || "",
    ai_confirm: document.querySelector("#scoreAiConfirm")?.checked || false,
    ...importedProductContext,
  };
}

document.querySelector("#runScore").addEventListener("click", async () => {
  const payload = getScorePayload();
  if (!payload.title) { showToast("请填写标题"); return; }

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
  const dimWeights = { title: 25, bullets: 25, description: 20, keywords: 15, compliance: 15 };

  const dimsHtml = Object.entries(data.dimensions || {}).map(([key, dim]) => {
    const max = dim.max || dimWeights[key] || 20;
    const pct = Math.round((dim.score / max) * 100);
    const barColor = pct >= 80 ? "#389e0d" : pct >= 60 ? "#d48806" : "#cf1322";
    const weightTag = dim.weight_pct ? ` · 权重 ${dim.weight_pct}%` : "";
    const positivesHtml = (dim.positives || []).length
      ? `<div class="dim-positives">${(dim.positives || []).join("；")}</div>` : "";
    const issuesHtml = (dim.issues || []).map((issue) => {
      const src = issue.source || "ai";
      const srcClass = src === "rule" ? "src-rule" : src === "publish" ? "src-publish" : "src-ai";
      const srcLabel = src === "rule" ? "规则" : src === "publish" ? "刊登" : "AI";
      return `
      <div class="dim-issue">
        <div class="issue-title"><span class="issue-src ${srcClass}">${srcLabel}</span>${escapeHtml(issue.issue || "")}</div>
        ${issue.why_matters ? `<div class="issue-detail"><span class="issue-detail-label">为什么重要</span><span class="issue-detail-value">${escapeHtml(issue.why_matters)}</span></div>` : ""}
        <div class="issue-detail"><span class="issue-detail-label">如何改进</span><span class="issue-detail-value">${escapeHtml(issue.how_to_fix || "")}</span></div>
        ${issue.expected_gain ? `<div class="issue-detail"><span class="issue-detail-label">预计效果</span><span class="issue-detail-value">${escapeHtml(issue.expected_gain)}</span></div>` : ""}
      </div>`;
    }).join("");
    return `<div class="dim-card">
      <div class="dim-header">
        <span class="dim-name">${dimLabels[key] || key}${weightTag}</span>
        <span class="dim-score-badge" style="background:${barColor}20;color:${barColor}">${dim.score}/${max} (${pct}%)</span>
      </div>
      ${dim.rule_score != null ? `<div class="dim-subscore">规则 ${dim.rule_score} + AI ${dim.ai_score}</div>` : ""}
      ${positivesHtml}
      <div class="dim-issues">${issuesHtml}</div>
    </div>`;
  }).join("");

  const priorityHtml = (data.top_priority || []).length
    ? `<div class="diag-priority"><h3>⚡ 优先处理</h3><ol>${data.top_priority.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ol></div>` : "";

  const breakdownHtml = data.rule_score != null
    ? `<div class="diag-breakdown">加权分 · 规则 ${data.rule_score} + AI ${data.ai_score ?? "?"} = ${data.overall_score}/100 · ${data.rule_checks ? data.rule_checks.filter((c) => c.passed).length : "?"}/${data.rule_checks?.length || "?"} 项规则通过${data.ai_scoring_mode === "per_dimension" ? " · 分维 AI" : ""}${data.rule_cached ? " · 规则缓存" : ""}${data.ai_confirm ? " · AI 二次确认" : ""}</div>` : "";

  const pub = data.publish_readiness;
  const publishHtml = pub
    ? `<div class="publish-ready-card ${pub.ready ? "ready" : "warn"}">
        <h3>刊登就绪度 <span class="rule-checks-meta">${pub.checks_passed}/${pub.checks_total} · ${pub.score}/100${pub.ready ? " · 可尝试刊登" : ""}</span></h3>
        <div class="publish-checks">
          ${(pub.checks || []).map((c) => `
            <div class="rule-check-item ${c.passed ? "pass" : "fail"}">
              <span class="rule-check-icon">${c.passed ? "✓" : "✗"}</span>
              <span class="rule-check-msg">${escapeHtml(c.message || c.id || "")}</span>
            </div>`).join("")}
        </div>
      </div>`
    : "";

  const imageSkipHtml = data.image_score_skipped
    ? `<div class="diag-image-skip">未关联产品图，图片合规项已跳过 — 合规分仅供参考。建议从产品页导入或填写图片数量。</div>`
    : "";

  const ruleDimLabels = { title: "标题", bullets: "Bullets", description: "描述", keywords: "关键词", compliance: "合规" };
  const ruleChecksHtml = (data.rule_checks || []).length
    ? `<div class="rule-checks-card">
        <h3>Amazon 规则校验 <span class="rule-checks-meta">${(data.rule_checks.filter((c) => c.passed).length)}/${data.rule_checks.length} 通过</span></h3>
        <div class="rule-checks-grid">
          ${Object.keys(ruleDimLabels).map((dim) => {
            const items = data.rule_checks.filter((c) => c.dimension === dim);
            if (!items.length) return "";
            return `<div class="rule-check-group">
              <div class="rule-check-dim">${ruleDimLabels[dim]}</div>
              ${items.map((c) => `
                <div class="rule-check-item ${c.passed ? "pass" : "fail"}${c.skipped ? " skipped" : ""}">
                  <span class="rule-check-icon">${c.skipped ? "○" : c.passed ? "✓" : "✗"}</span>
                  <span class="rule-check-msg">${escapeHtml(c.message || c.id || "")}</span>
                  <span class="rule-check-pts">${c.points}/${c.max_points}</span>
                </div>`).join("")}
            </div>`;
          }).join("")}
        </div>
      </div>` : "";

  container._listingData = getScorePayload();
  container._scoreResult = data;

  container.innerHTML = `
    <div class="diag-header" style="border-color:${scoreColor}">
      <div class="diag-score" style="color:${scoreColor}">${data.overall_score}<span style="font-size:16px;color:#999">/100</span></div>
      <div>
        <div class="diag-grade" style="color:${scoreColor}">${escapeHtml(data.overall_grade || "")}</div>
        ${breakdownHtml}
      </div>
      <div class="diag-summary">${escapeHtml(data.overall_summary || "")}</div>
    </div>
    ${imageSkipHtml}
    ${publishHtml}
    ${priorityHtml}
    ${ruleChecksHtml}
    ${dimsHtml}
    <div class="optimize-bar">
      <button class="btn primary btn-lg" id="runOptimize">根据诊断结果生成优化方案</button>
      <p class="section-desc" style="margin-top:8px">AI 将针对每个问题给出优化文案，并自动复评验证提升效果</p>
    </div>
    <div id="optimizeResult" class="hidden"></div>
  `;

  document.querySelector("#runOptimize")?.addEventListener("click", async () => {
    const btn = document.querySelector("#runOptimize");
    btn.disabled = true;
    btn.textContent = "AI 正在优化并复评...";
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

function renderDimDelta(beforeDims, afterDims) {
  const labels = { title: "标题", bullets: "Bullets", description: "描述", keywords: "关键词", compliance: "合规" };
  return Object.keys(labels).map((key) => {
    const b = (beforeDims[key] || {}).score ?? 0;
    const a = (afterDims[key] || {}).score ?? 0;
    const delta = a - b;
    const deltaText = delta > 0 ? `+${delta}` : delta === 0 ? "—" : String(delta);
    const deltaColor = delta > 0 ? "#389e0d" : delta < 0 ? "#cf1322" : "#999";
    return `<div class="dim-delta-row">
      <span>${labels[key]}</span>
      <span>${b} → ${a}</span>
      <span style="color:${deltaColor};font-weight:600">${deltaText}</span>
    </div>`;
  }).join("");
}

function renderOptimizations(data) {
  const container = document.querySelector("#optimizeResult");
  container.classList.remove("hidden");

  const sc = data.score_comparison || {};
  const rescore = data.rescore || {};
  const delta = sc.score_delta ?? ((sc.verified_new_score || 0) - (sc.original_score || 0));
  const deltaColor = delta > 0 ? "#389e0d" : delta < 0 ? "#cf1322" : "#999";

  const compHtml = sc.original_score != null ? `
    <div class="score-compare verified">
      <div class="score-compare-badge">✓ 复评 verified</div>
      <div class="score-compare-item before">
        <div class="score-compare-num">${sc.original_score}</div>
        <div class="score-compare-label">优化前 · ${escapeHtml(sc.original_grade || "")}</div>
      </div>
      <div class="score-compare-arrow">→</div>
      <div class="score-compare-item after">
        <div class="score-compare-num">${sc.verified_new_score ?? sc.estimated_new_score ?? "?"}</div>
        <div class="score-compare-label">复评后 · ${escapeHtml(sc.verified_grade || rescore.overall_grade || "")}</div>
      </div>
      <div class="score-delta" style="color:${deltaColor}">${delta > 0 ? "+" : ""}${delta} 分</div>
      ${sc.why_improved ? `<div class="score-compare-reason">${escapeHtml(sc.why_improved)}</div>` : ""}
    </div>
    ${rescore.dimensions ? `
      <div class="rescore-delta-card">
        <h3>各维度复评对比</h3>
        ${renderDimDelta((document.querySelector("#diagnosisContainer")._scoreResult || {}).dimensions || {}, rescore.dimensions)}
      </div>` : ""}
  ` : "";

  const optsHtml = (data.optimizations || []).map((opt, i) => `
    <div class="opt-card">
      <div class="opt-header">
        <span class="opt-num">#${i + 1}</span>
        <span class="opt-target">${escapeHtml(opt.target || "")}</span>
      </div>
      <div class="opt-issue">问题：${escapeHtml(opt.issue_summary || "")}</div>
      ${opt.original_text ? `<div class="opt-original"><strong>优化前：</strong>${escapeHtml(opt.original_text)}</div>` : ""}
      <div class="opt-detail">
        <div class="opt-detail-row"><strong>为什么优化：</strong>${escapeHtml(opt.why_optimize || "")}</div>
        <div class="opt-detail-row"><strong>预期效果：</strong>${escapeHtml(opt.expected_benefit || "")}</div>
      </div>
      ${opt.optimized_content ? `<div class="opt-content"><strong>优化后：</strong><div>${escapeHtml(opt.optimized_content)}</div></div>` : ""}
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
    ${compHtml}
    ${data.overall_strategy ? `<div class="opt-strategy"><strong>整体优化策略：</strong>${escapeHtml(data.overall_strategy)}</div>` : ""}
    <h3 style="margin:16px 0 10px;font-size:15px">逐项优化建议</h3>
    ${optsHtml}
    ${applyHtml}
  `;

  container.querySelector(".apply-optimized")?.addEventListener("click", () => {
    const listing = JSON.parse(container.querySelector(".apply-optimized").dataset.listing);
    localStorage.setItem("listing_apply", JSON.stringify(listing));
    showToast("优化方案已暂存，切换到产品页将自动填入");
    setTimeout(() => { window.location.href = createProductHref(); }, 800);
  });
}

// ── Import from product page ─────────────────────────────────

function parseImageCount(data) {
  if (data.image_count != null && data.image_count !== "") {
    const n = parseInt(data.image_count, 10);
    if (Number.isFinite(n) && n >= 0) return n;
  }
  if (data.product_images) {
    try {
      const imgs = typeof data.product_images === "string"
        ? JSON.parse(data.product_images)
        : data.product_images;
      if (Array.isArray(imgs)) return imgs.filter(Boolean).length;
    } catch (e) { /* ignore */ }
  }
  return 0;
}

function resolveParentSku(data) {
  return String(data.parent_sku || data.seller_sku || data.msku || "").trim();
}

function applyImportData(data) {
  const filled = [];
  const missing = [];

  const set = (id, value, label) => {
    const el = document.querySelector(id);
    if (!el) return;
    const text = value != null ? String(value).trim() : "";
    if (text) {
      el.value = text;
      if (label) filled.push(label);
    } else if (label) {
      missing.push(label);
    }
  };

  set("#scoreTitle", data.item_name, "标题");
  for (let i = 1; i <= 5; i++) {
    const val = data["bullet_point_" + i];
    const el = document.querySelector("#scoreB" + i);
    if (el && val && String(val).trim()) {
      el.value = String(val).trim();
      if (i === 1) filled.push("Bullets");
    }
  }
  set("#scoreDesc", data.product_description, "描述");
  set("#scoreST", data.generic_keyword, "Search Terms");
  set("#scoreCat", data.product_type, "Product Type");
  set("#scoreCatPath", data.category_path, "Category Path");
  set("#scoreBrand", data.brand, "品牌");
  set("#scoreManufacturer", data.manufacturer || data.brand, "制造商");

  const parentSku = resolveParentSku(data);
  const mskuEl = document.querySelector("#scoreMsku");
  if (mskuEl) {
    if (parentSku) {
      mskuEl.value = parentSku;
      filled.push("Parent SKU");
      mskuLinked = true;
      mskuEl.readOnly = true;
      mskuEl.classList.add("readonly-field");
      const hint = document.querySelector("#scoreMskuHint");
      if (hint) hint.textContent = `已从产品页导入 Parent SKU（锁定）`;
    } else {
      mskuEl.value = "";
      mskuEl.readOnly = false;
      mskuEl.classList.remove("readonly-field");
      missing.push("Parent SKU");
    }
  }

  const priceEl = document.querySelector("#scorePrice");
  if (priceEl && data.price != null && String(data.price).trim() !== "") {
    priceEl.value = data.price;
    filled.push("售价");
  } else {
    missing.push("售价");
  }

  const imgCount = parseImageCount(data);
  const imgsEl = document.querySelector("#scoreImgs");
  if (imgsEl) {
    if (imgCount > 0) {
      imgsEl.value = String(imgCount);
      filled.push(`图片(${imgCount}张)`);
      imagesLinked = true;
      imgsEl.readOnly = true;
      imgsEl.classList.add("readonly-field");
      const hint = document.querySelector("#scoreImgsHint");
      if (hint) hint.textContent = `已从产品页导入 ${imgCount} 张图片（锁定）`;
    } else {
      imgsEl.value = "";
      imgsEl.readOnly = false;
      imgsEl.classList.remove("readonly-field");
      missing.push("图片");
    }
  }

  if (data.category_path) filled.push("分类路径");

  const SKIP_CTX = new Set([
    "item_name", "product_description", "generic_keyword", "product_type",
    "category_path", "brand", "manufacturer", "price", "product_images",
    "image_count", "parent_sku", "seller_sku", "msku", "msku_linked",
    "bullet_point_1", "bullet_point_2", "bullet_point_3", "bullet_point_4", "bullet_point_5",
  ]);
  importedProductContext = {};
  for (const [key, val] of Object.entries(data)) {
    if (SKIP_CTX.has(key) || val == null || String(val).trim() === "") continue;
    importedProductContext[key] = String(val).trim();
  }

  return { filled, missing };
}

function showImportBanner(filled, missing) {
  const slot = document.querySelector("#importBannerSlot");
  if (!slot) return;
  const filledHtml = filled.length
    ? `<span class="import-tag ok">已导入 ${filled.join("、")}</span>`
    : "";
  const missingHtml = missing.length
    ? `<span class="import-tag warn">未填写 ${missing.join("、")}，可在下方补充</span>`
    : "";
  slot.innerHTML = `<div class="import-banner"><strong>来自产品页导入</strong> ${filledHtml} ${missingHtml}</div>`;
}

(function checkImport() {
  const raw = localStorage.getItem("listing_import_data");
  if (!raw) return;
  let data;
  try { data = JSON.parse(raw); } catch (e) { return; }
  if (!data || !Object.keys(data).length) return;

  localStorage.removeItem("listing_import_data");

  const { filled, missing } = applyImportData(data);
  showImportBanner(filled, missing);

  showToast(`已导入 ${filled.length} 项，${missing.length ? "请补充 " + missing.join("、") : "可开始诊断"}`);
})();
