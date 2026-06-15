const form = document.querySelector("#productForm");
const accountSelect = document.querySelector("#accountSelect");
const siteSelect = document.querySelector("#siteSelect");
const storeIdInput = document.querySelector("#storeId");
const marketplaceIdInput = document.querySelector("#marketplaceId");
const storeFullNameInput = document.querySelector("#storeFullName");
const categoryDisplay = document.querySelector("#categoryDisplay");
const categoryIdInput = document.querySelector("#categoryId");
const categoryPathInput = document.querySelector("#categoryPath");
const productTypeInput = document.querySelector("#productType");
const browseNodeAttributesInput = document.querySelector("#browseNodeAttributes");
const categoryMeta = document.querySelector("#categoryMeta");
const categoryModal = document.querySelector("#categoryModal");
const categoryColumns = document.querySelector("#categoryColumns");
const categoryBreadcrumb = document.querySelector("#categoryBreadcrumb");
const categoryRecommend = document.querySelector("#categoryRecommend");
const categorySourceTip = document.querySelector("#categorySourceTip");
const categorySearchInput = document.querySelector("#categorySearchInput");
const categorySearchResults = document.querySelector("#categorySearchResults");
const confirmCategoryPicker = document.querySelector("#confirmCategoryPicker");
const attributeFields = document.querySelector("#attributeFields");
const attributeMeta = document.querySelector("#attributeMeta");
const draftNo = document.querySelector("#draftNo");
const draftList = document.querySelector("#draftList");
const taskList = document.querySelector("#taskList");
const toast = document.querySelector("#toast");

let allStores = [];
let productImages = [];
const MAX_IMAGES = 9;
let manufacturerLinkedToBrand = true;

const categoryPicker = {
  columns: [],
  selectedPath: [],
  pendingSelection: null,
  sourceMessage: "",
};

function getCurrentStoreId() {
  const store = getSelectedStore();
  return store?.id || Number(storeIdInput.value) || null;
}

function formatBrowseAttributes(attrs) {
  if (!attrs || typeof attrs !== "object") return "";
  return Object.entries(attrs)
    .map(([key, value]) => `${key}: ${value}`)
    .join(" | ");
}

function categoryName(item) {
  return item?.display_name || item?.name || "";
}

function applyCategorySelection(selection) {
  if (!selection) return;

  categoryIdInput.value = selection.id || "";
  categoryPathInput.value = selection.path_text || selection.path?.join(" > ") || categoryName(selection);
  categoryDisplay.value = categoryPathInput.value;
  productTypeInput.value = selection.product_type || "";
  browseNodeAttributesInput.value = JSON.stringify(selection.browse_node_attributes || {});

  const metaParts = [];
  if (selection.product_type) metaParts.push(`Product Type: ${selection.product_type}`);
  const browseText = formatBrowseAttributes(selection.browse_node_attributes);
  if (browseText) metaParts.push(browseText);
  categoryMeta.textContent = metaParts.join(" ｜ ");
}

function updateCategoryRecommend(node) {
  const productType = node?.product_type || node?.productType || "";
  categoryRecommend.textContent = productType
    ? `平台推荐产品类型: ${productType}`
    : "平台推荐产品类型: -";
}

function renderCategoryBreadcrumb() {
  if (!categoryPicker.selectedPath.length) {
    categoryBreadcrumb.textContent = "请选择分类";
    updateCategoryRecommend(null);
    return;
  }
  categoryBreadcrumb.textContent = categoryPicker.selectedPath.map(categoryName).join(" > ");
  updateCategoryRecommend(categoryPicker.selectedPath[categoryPicker.selectedPath.length - 1]);
}

function renderCategoryColumn(level, items, loading = false) {
  const column = document.createElement("div");
  column.className = "category-column";
  column.dataset.level = String(level);

  if (loading) {
    column.innerHTML = '<div class="category-column-loading">加载中...</div>';
    return column;
  }

  if (!items.length) {
    column.innerHTML = '<div class="category-column-empty">暂无分类</div>';
    return column;
  }

  items.forEach((item) => {
    const activeNode = categoryPicker.selectedPath[level];
    const button = document.createElement("button");
    button.type = "button";
    button.className = "category-item";
    if (activeNode?.id === item.id) button.classList.add("active");
    button.innerHTML = `
      <span>${categoryName(item)}</span>
      ${item.has_children ? '<span class="arrow">›</span>' : ""}
    `;
    button.addEventListener("click", () => {
      onCategoryNodeClick(level, item).catch((error) => showToast(error.message));
    });
    column.appendChild(button);
  });

  return column;
}

function renderCategoryColumns() {
  categoryColumns.innerHTML = "";
  categoryPicker.columns.forEach((items, level) => {
    categoryColumns.appendChild(renderCategoryColumn(level, items));
  });
  while (categoryColumns.children.length < 4) {
    categoryColumns.appendChild(renderCategoryColumn(categoryColumns.children.length, []));
  }
}

async function fetchCategoryNodes(parentId = null) {
  const storeId = getCurrentStoreId();
  const query = storeId ? `store_id=${encodeURIComponent(storeId)}` : "";
  const url = parentId
    ? `/api/categories/children?${query}&parent_id=${encodeURIComponent(parentId)}`
    : `/api/categories/root?${query}`;
  const result = await apiGet(url);
  categoryPicker.sourceMessage = result.message || (result.source === "lingxing" ? "数据来源：领星 API" : "数据来源：演示数据");
  categorySourceTip.textContent = categoryPicker.sourceMessage;
  categorySourceTip.classList.toggle("warning", /403|白名单|不可用|未配置/.test(categoryPicker.sourceMessage));
  return result.data || [];
}

async function onCategoryNodeClick(level, node) {
  categoryPicker.selectedPath = categoryPicker.selectedPath.slice(0, level);
  categoryPicker.selectedPath.push(node);
  categoryPicker.pendingSelection = node.has_children
    ? null
    : {
        id: node.id,
        name: node.name,
        display_name: categoryName(node),
        path: categoryPicker.selectedPath.map(categoryName),
        path_text: categoryPicker.selectedPath.map(categoryName).join(" > "),
        product_type: node.product_type || "",
        browse_node_attributes: node.browse_node_attributes || {},
      };

  categoryPicker.columns = categoryPicker.columns.slice(0, level + 1);
  renderCategoryBreadcrumb();
  confirmCategoryPicker.disabled = !categoryPicker.pendingSelection;

  if (!node.has_children) {
    renderCategoryColumns();
    return;
  }

  categoryPicker.columns[level + 1] = [];
  renderCategoryColumns();
  categoryPicker.columns[level + 1] = await fetchCategoryNodes(node.id);
  categoryPicker.columns = categoryPicker.columns.slice(0, level + 2);
  renderCategoryColumns();
}

async function openCategoryPicker() {
  if (!getCurrentStoreId()) {
    showToast("请先选择店铺账号和站点");
    return;
  }

  categoryModal.classList.remove("hidden");
  categoryModal.setAttribute("aria-hidden", "false");
  categorySearchInput.value = "";
  categorySearchResults.classList.add("hidden");
  categorySearchResults.innerHTML = "";
  categoryPicker.selectedPath = [];
  categoryPicker.pendingSelection = null;
  categoryPicker.columns = [[]];
  confirmCategoryPicker.disabled = true;
  renderCategoryBreadcrumb();
  renderCategoryColumns();

  categoryPicker.columns[0] = await fetchCategoryNodes();
  renderCategoryColumns();
}

function closeCategoryPicker() {
  categoryModal.classList.add("hidden");
  categoryModal.setAttribute("aria-hidden", "true");
}

async function confirmCategorySelection() {
  if (!categoryPicker.pendingSelection) {
    showToast("请选择末级分类");
    return;
  }
  applyCategorySelection(categoryPicker.pendingSelection);
  closeCategoryPicker();
  await loadSchema();
  showToast("分类已选择");
}

async function searchCategories(keyword) {
  if (!keyword.trim()) {
    categorySearchResults.classList.add("hidden");
    categorySearchResults.innerHTML = "";
    categoryColumns.classList.remove("hidden");
    return;
  }

  const storeId = getSelectedStore()?.id || "";
  const result = await apiGet(
    `/api/categories/search?q=${encodeURIComponent(keyword.trim())}&store_id=${encodeURIComponent(storeId)}`,
  );
  const items = result.data || [];
  categoryColumns.classList.add("hidden");
  categorySearchResults.classList.remove("hidden");
  categorySearchResults.innerHTML = "";

  if (!items.length) {
    categorySearchResults.innerHTML = '<div class="category-column-empty">未找到匹配分类</div>';
    return;
  }

  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "category-search-item";
    button.innerHTML = `
      <strong>${categoryName(item)}</strong>
      <span>${item.path_text || ""}${item.product_type ? ` ｜ ${item.product_type}` : ""}</span>
    `;
    button.addEventListener("click", () => {
      categoryPicker.pendingSelection = item;
      categoryPicker.selectedPath = item.path.map((name, index) => ({
        id: index === item.path.length - 1 ? item.id : `path-${index}`,
        name,
        display_name: name,
        product_type: index === item.path.length - 1 ? item.product_type : "",
      }));
      renderCategoryBreadcrumb();
      confirmCategoryPicker.disabled = false;
      categorySearchResults.classList.add("hidden");
      categoryColumns.classList.remove("hidden");
      categorySearchInput.value = "";
      showToast("已从搜索结果选中分类，请点击确定");
    });
    categorySearchResults.appendChild(button);
  });
}

const APP_BASE = (() => {
  const path = window.location.pathname;
  if (path === "/listing" || path.startsWith("/listing/")) return "/listing";
  return "";
})();

function appUrl(path) {
  if (!path.startsWith("/")) return path;
  return `${APP_BASE}${path}`;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2600);
}

async function apiGet(url) {
  const response = await fetch(appUrl(url));
  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }
  return response.json();
}

async function apiPost(url, payload) {
  const response = await fetch(appUrl(url), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.code === 0) {
    if (response.status === 413) {
      throw new Error("提交失败：请求体过大（413）。请删除旧版 base64 图片后，重新上传本地图片。");
    }
    throw new Error(data.message || `提交失败：${response.status}`);
  }
  return data;
}

async function uploadImageFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(appUrl("/api/images/upload"), {
    method: "POST",
    body: formData,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.code === 0) {
    if (response.status === 413) {
      throw new Error("图片过大，单张请控制在 10MB 以内");
    }
    throw new Error(data.message || `图片上传失败：${response.status}`);
  }
  return data.data?.url || "";
}

function option(value, label) {
  const item = document.createElement("option");
  item.value = value;
  item.textContent = label;
  return item;
}

function fieldLabelHtml(field) {
  if (field.type === "subsection") return "";
  const en = field.label_en || field.label || field.key;
  const zh = field.label_zh || "";
  return zh && zh !== en ? `${en}(${zh})` : en;
}

function fieldSearchText(field) {
  return [field.key, field.label_en, field.label_zh, field.label, field.title]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function normalizeSelectOptions(options) {
  if (!options) return [];
  return options.map((item) =>
    typeof item === "string" ? { value: item, label: item } : item,
  );
}

function createSelect(name, options, placeholder = "请选择") {
  const select = document.createElement("select");
  select.name = name;
  select.className = "dxm-control dxm-select";
  select.appendChild(option("", placeholder));
  normalizeSelectOptions(options).forEach((item) => {
    select.appendChild(option(item.value, item.label));
  });
  return select;
}

function createSearchableSelect(name, options, field) {
  const wrap = document.createElement("div");
  wrap.className = "dxm-search-select";

  const hidden = document.createElement("input");
  hidden.type = "hidden";
  hidden.name = name;

  const input = document.createElement("input");
  input.type = "text";
  input.className = "dxm-search-select-input";
  input.autocomplete = "off";
  input.placeholder = field.placeholder || "请选择";

  const gearBtn = document.createElement("button");
  gearBtn.type = "button";
  gearBtn.className = "dxm-search-select-gear";
  gearBtn.title = "自定义";
  gearBtn.setAttribute("aria-label", "自定义");
  gearBtn.innerHTML = `<svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor"><path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/><path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319z"/></svg>`;

  const dropdown = document.createElement("div");
  dropdown.className = "dxm-search-select-dropdown hidden";

  const normalized = normalizeSelectOptions(options);
  let selectedValue = field.default || "";

  function labelFor(value) {
    const item = normalized.find((entry) => entry.value === value);
    return item ? item.label : value;
  }

  function setValue(value, label) {
    selectedValue = value;
    hidden.value = value;
    input.value = label || labelFor(value);
  }

  function renderDropdown(filter = "") {
    dropdown.innerHTML = "";
    const keyword = filter.trim().toLowerCase();
    const matched = normalized.filter((item) => {
      if (!keyword) return true;
      return (
        item.label.toLowerCase().includes(keyword) ||
        item.value.toLowerCase().includes(keyword)
      );
    });

    if (!matched.length) {
      const empty = document.createElement("div");
      empty.className = "dxm-search-select-empty";
      empty.textContent = "无匹配选项";
      dropdown.appendChild(empty);
      return;
    }

    matched.forEach((item) => {
      const row = document.createElement("div");
      row.className = "dxm-search-select-option";
      if (item.value === selectedValue) row.classList.add("active");
      row.textContent = item.label;
      row.addEventListener("mousedown", (event) => {
        event.preventDefault();
        setValue(item.value, item.label);
        closeDropdown();
      });
      dropdown.appendChild(row);
    });
  }

  function openDropdown() {
    const filterText = input.value === labelFor(selectedValue) ? "" : input.value;
    renderDropdown(filterText);
    dropdown.classList.remove("hidden");
    wrap.classList.add("open");
  }

  function closeDropdown() {
    dropdown.classList.add("hidden");
    wrap.classList.remove("open");
    input.value = labelFor(selectedValue);
  }

  if (selectedValue) {
    setValue(selectedValue);
  }

  input.addEventListener("focus", openDropdown);
  input.addEventListener("click", openDropdown);
  input.addEventListener("input", () => {
    renderDropdown(input.value);
    dropdown.classList.remove("hidden");
    wrap.classList.add("open");
  });
  input.addEventListener("blur", () => {
    window.setTimeout(closeDropdown, 150);
  });

  gearBtn.addEventListener("mousedown", (event) => event.preventDefault());
  gearBtn.addEventListener("click", () => {
    const custom = window.prompt("输入自定义外饰面", input.value || labelFor(selectedValue));
    if (!custom?.trim()) return;
    setValue(custom.trim(), custom.trim());
    closeDropdown();
  });

  wrap.appendChild(input);
  wrap.appendChild(gearBtn);
  wrap.appendChild(dropdown);
  wrap.appendChild(hidden);
  return wrap;
}

function createDropdownSearchSelect(name, options, field) {
  const wrap = document.createElement("div");
  wrap.className = "dxm-dropdown-select";

  const hidden = document.createElement("input");
  hidden.type = "hidden";
  hidden.name = name;

  const trigger = document.createElement("div");
  trigger.className = "dxm-dropdown-select-trigger";
  trigger.tabIndex = 0;

  const display = document.createElement("span");
  display.className = "dxm-dropdown-select-value";

  const arrow = document.createElement("span");
  arrow.className = "dxm-dropdown-select-arrow";
  arrow.textContent = "▾";

  trigger.appendChild(display);
  trigger.appendChild(arrow);

  const dropdown = document.createElement("div");
  dropdown.className = "dxm-dropdown-select-panel hidden";

  const searchWrap = document.createElement("div");
  searchWrap.className = "dxm-dropdown-select-search";
  const searchInput = document.createElement("input");
  searchInput.type = "text";
  searchInput.placeholder = "输入搜索值";
  searchInput.autocomplete = "off";
  const searchIcon = document.createElement("span");
  searchIcon.className = "dxm-dropdown-select-search-icon";
  searchIcon.textContent = "⌕";
  searchWrap.appendChild(searchInput);
  searchWrap.appendChild(searchIcon);

  const list = document.createElement("div");
  list.className = "dxm-dropdown-select-list";
  dropdown.appendChild(searchWrap);
  dropdown.appendChild(list);

  const normalized = normalizeSelectOptions(options);
  let selectedValue = field.default || "";

  function labelFor(value) {
    const item = normalized.find((entry) => entry.value === value);
    return item ? item.label : value;
  }

  function setValue(value) {
    selectedValue = value;
    hidden.value = value;
    display.textContent = labelFor(value) || field.placeholder || "请选择";
    display.title = display.textContent;
  }

  function renderList(filter = "") {
    list.innerHTML = "";
    const keyword = filter.trim().toLowerCase();
    const matched = normalized.filter((item) => {
      if (!keyword) return true;
      return (
        item.label.toLowerCase().includes(keyword) ||
        item.value.toLowerCase().includes(keyword)
      );
    });

    if (!matched.length) {
      const empty = document.createElement("div");
      empty.className = "dxm-dropdown-select-empty";
      empty.textContent = "无匹配选项";
      list.appendChild(empty);
      return;
    }

    matched.forEach((item) => {
      const row = document.createElement("div");
      row.className = "dxm-dropdown-select-option";
      if (item.value === selectedValue) row.classList.add("active");
      row.textContent = item.label;
      row.title = item.label;
      row.addEventListener("mousedown", (event) => {
        event.preventDefault();
        setValue(item.value);
        closeDropdown();
      });
      list.appendChild(row);
    });
  }

  function openDropdown() {
    searchInput.value = "";
    renderList("");
    dropdown.classList.remove("hidden");
    wrap.classList.add("open");
    window.setTimeout(() => searchInput.focus(), 0);
  }

  function closeDropdown() {
    dropdown.classList.add("hidden");
    wrap.classList.remove("open");
  }

  if (selectedValue) {
    setValue(selectedValue);
  } else {
    display.textContent = field.placeholder || "请选择";
  }

  trigger.addEventListener("click", () => {
    if (wrap.classList.contains("open")) {
      closeDropdown();
    } else {
      openDropdown();
    }
  });

  searchInput.addEventListener("input", () => renderList(searchInput.value));
  searchInput.addEventListener("mousedown", (event) => event.stopPropagation());

  document.addEventListener("click", (event) => {
    if (!wrap.contains(event.target)) {
      closeDropdown();
    }
  });

  wrap.appendChild(trigger);
  wrap.appendChild(dropdown);
  wrap.appendChild(hidden);
  return wrap;
}

function appendHelpIcon(label, field) {
  if (field.help === false) return;
  const help = document.createElement("span");
  help.className = "help-icon";
  help.title = field.help || "字段说明";
  help.textContent = "?";
  label.appendChild(help);
}

let attributePanel = null;
let showMoreAttributes = false;

function closeAttributePanel() {
  attributePanel = null;
}

function applyFieldDefault(control, field) {
  if (field.default == null || field.default === "") return;
  if (control.tagName === "SELECT") {
    control.value = field.default;
  } else {
    control.value = field.default;
  }
}

function applyFieldConstraints(control, field) {
  const constraints = field.constraints || {};
  const maxlength = field.maxlength || constraints.max_length;
  if (maxlength != null) control.maxLength = Number(maxlength);
  if (constraints.min_length != null) control.minLength = Number(constraints.min_length);
  if (field.min != null || constraints.minimum != null) control.min = field.min ?? constraints.minimum;
  if (field.max != null || constraints.maximum != null) control.max = field.max ?? constraints.maximum;
  if (constraints.pattern) control.pattern = constraints.pattern;
  if (field.step) control.step = field.step;
}

function normalizeOption(option) {
  if (option && typeof option === "object") {
    return {
      value: String(option.value ?? option.label ?? ""),
      label: String(option.label ?? option.value ?? ""),
    };
  }
  return { value: String(option ?? ""), label: String(option ?? "") };
}

function renderCheckboxGroup(field) {
  const labels = field.option_labels || {};
  const usePlain = field.layout === "grid" || (field.layout === "inline" && !field.editable_options && !field.allow_other);
  const wrap = document.createElement("div");
  wrap.className = "checkbox-group";
  if (field.layout === "inline") wrap.classList.add("inline");
  if (field.layout === "grid") {
    wrap.classList.add("grid");
    if (field.columns) wrap.style.setProperty("--checkbox-cols", String(field.columns));
  }
  wrap.dataset.fieldKey = field.key;

  const appendCheckbox = (rawOption) => {
    const option = normalizeOption(rawOption);
    const value = option.value;
    const displayLabel = labels[value] || option.label || value;
    if (usePlain) {
      const label = document.createElement("label");
      label.className = "checkbox-item";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = `attr_${field.key}[]`;
      input.value = value;
      if (field.default && String(field.default).split(",").map((v) => v.trim()).includes(value)) {
        input.checked = true;
      }
      const text = document.createElement("span");
      text.className = "component-text";
      text.textContent = displayLabel;
      label.appendChild(input);
      label.appendChild(text);
      wrap.appendChild(label);
      return;
    }

    const row = document.createElement("div");
    row.className = "component-option";
    const label = document.createElement("label");
    label.className = "checkbox-item";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = `attr_${field.key}[]`;
    input.value = value;
    if (field.default && String(field.default).split(",").map((v) => v.trim()).includes(value)) {
      input.checked = true;
    }
    const text = document.createElement("span");
    text.className = "component-text";
    text.textContent = displayLabel;
    label.appendChild(input);
    label.appendChild(text);
    row.appendChild(label);
    if (field.editable_options) {
      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "component-edit-btn";
      editBtn.title = "编辑";
      editBtn.textContent = "✎";
      editBtn.addEventListener("click", () => {
        const next = window.prompt("编辑组件名称", text.textContent);
        if (!next?.trim()) return;
        text.textContent = next.trim();
        input.value = next.trim();
      });
      row.appendChild(editBtn);
    }
    wrap.appendChild(row);
  };

  field.options.forEach(appendCheckbox);

  if (field.allow_other) {
    const otherRow = document.createElement("div");
    otherRow.className = "checkbox-other-row";
    const otherLabel = document.createElement("span");
    otherLabel.className = "other-label";
    otherLabel.textContent = "其它";
    const otherInput = document.createElement("input");
    otherInput.type = "text";
    otherInput.name = `attr_${field.key}_other`;
    otherInput.className = "dxm-control other-input";
    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.className = "dxm-link-btn";
    addBtn.textContent = "添加";
    addBtn.addEventListener("click", () => {
      const text = otherInput.value.trim();
      if (!text) return;
      const exists = [...wrap.querySelectorAll(`input[name="attr_${field.key}[]"]`)].some(
        (node) => node.value === text,
      );
      if (exists) {
        showToast("该选项已存在");
        return;
      }
      const row = document.createElement("div");
      row.className = "component-option";
      const label = document.createElement("label");
      label.className = "checkbox-item";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = `attr_${field.key}[]`;
      input.value = text;
      input.checked = true;
      const span = document.createElement("span");
      span.className = "component-text";
      span.textContent = text;
      label.appendChild(input);
      label.appendChild(span);
      row.appendChild(label);
      wrap.insertBefore(row, otherRow);
      otherInput.value = "";
    });
    otherRow.appendChild(otherLabel);
    otherRow.appendChild(otherInput);
    otherRow.appendChild(addBtn);
    wrap.appendChild(otherRow);
  }

  return wrap;
}

function renderAttributeField(field) {
  if (field.type === "subsection") {
    closeAttributePanel();
    const title = document.createElement("div");
    title.className = "attribute-subsection";
    if (field.advanced) title.classList.add("advanced-attribute");
    title.dataset.searchText = (field.title || "").toLowerCase();
    title.textContent = field.title || "";
    attributeFields.appendChild(title);
    if (field.panel) {
      attributePanel = document.createElement("div");
      attributePanel.className = "attr-panel";
      attributeFields.appendChild(attributePanel);
    }
    return;
  }

  const target = attributePanel || attributeFields;
  const row = document.createElement("div");
  row.className = "form-row attribute-row dxm-attr-row";
  if (field.required) row.classList.add("required");
  if (field.advanced) row.classList.add("advanced-attribute");
  row.dataset.searchText = fieldSearchText(field);
  row.dataset.fieldKey = field.key || "";

  const label = document.createElement("div");
  label.className = "row-label dxm-attr-label";
  label.innerHTML = fieldLabelHtml(field);
  appendHelpIcon(label, field);

  const content = document.createElement("div");
  content.className = "row-content dxm-attr-content";

  if (field.type === "select" && field.searchable) {
    if (field.searchable_mode === "dropdown") {
      content.appendChild(createDropdownSearchSelect(`attr_${field.key}`, field.options, field));
    } else {
      content.appendChild(createSearchableSelect(`attr_${field.key}`, field.options, field));
    }
  } else if (field.type === "select") {
    const select = createSelect(`attr_${field.key}`, field.options);
    applyFieldDefault(select, field);
    content.appendChild(select);
  } else if (field.type === "unit") {
    const unitRow = document.createElement("div");
    unitRow.className = "unit-input-row";
    const input = document.createElement("input");
    input.name = `attr_${field.key}`;
    input.type = "number";
    input.className = "dxm-control dxm-unit-value";
    input.step = field.step || "any";
    applyFieldConstraints(input, field);
    applyFieldDefault(input, field);
    const unitSelect = createSelect(`attr_${field.unit_key}`, field.unit_options, "单位");
    applyFieldDefault(unitSelect, { default: field.unit_default });
    unitRow.appendChild(input);
    unitRow.appendChild(unitSelect);
    content.appendChild(unitRow);
  } else if (field.type === "dimensions") {
    const dimensionRow = document.createElement("div");
    dimensionRow.className = "unit-input-row";
    const dimensionLabels = { length: "长", width: "宽", height: "高" };
    const parts = field.dimension_parts || ["length", "width", "height"];
    parts.forEach((part) => {
      const input = document.createElement("input");
      input.name = `attr_${field.key}_${part}`;
      input.type = "number";
      input.className = "dxm-control dxm-unit-value";
      input.step = "any";
      input.placeholder = dimensionLabels[part] || part;
      applyFieldConstraints(input, field);
      dimensionRow.appendChild(input);
    });
    const unitSelect = createSelect(`attr_${field.key}_unit`, field.unit_options || [
      { value: "inches", label: "Inches(英寸)" },
      { value: "centimeters", label: "Centimeters(厘米)" },
    ], "单位");
    applyFieldDefault(unitSelect, { default: field.unit_default || "inches" });
    dimensionRow.appendChild(unitSelect);
    content.appendChild(dimensionRow);
  } else if (field.type === "unit_count") {
    const unitCountRow = document.createElement("div");
    unitCountRow.className = "unit-input-row";
    const input = document.createElement("input");
    input.name = `attr_${field.key}`;
    input.type = "number";
    input.className = "dxm-control dxm-unit-value";
    input.step = "any";
    input.placeholder = "数量";
    applyFieldConstraints(input, field);
    applyFieldDefault(input, field);
    const typeSelect = createSelect(
      `attr_${field.type_key || `${field.key}_type`}`,
      field.type_options || [{ value: "Count", label: "Count(件)" }],
      "单位类型",
    );
    applyFieldDefault(typeSelect, { default: field.type_default || "Count" });
    unitCountRow.appendChild(input);
    unitCountRow.appendChild(typeSelect);
    content.appendChild(unitCountRow);
  } else if (field.type === "checkbox_group") {
    content.appendChild(renderCheckboxGroup(field));
  } else {
    const input = document.createElement("input");
    input.name = `attr_${field.key}`;
    input.className = "dxm-control";
    input.type = ["number", "date", "url"].includes(field.type) ? field.type : "text";
    input.placeholder = field.placeholder || "";
    applyFieldConstraints(input, field);
    applyFieldDefault(input, field);
    content.appendChild(input);
  }

  row.appendChild(label);
  row.appendChild(content);
  target.appendChild(row);
}

let allAttributeFields = [];
let baseAttributeFields = [];
let currentVariationThemes = [];

function isVariationSaleType(data = formToObject()) {
  return (data.sale_type || "single") === "variation";
}

function syncSaleTypeState() {
  const variationMode = isVariationSaleType();
  document.querySelector("#variation-info")?.classList.toggle("hidden", !variationMode);
  document.querySelector("#variationNavLink")?.classList.toggle("hidden", !variationMode);
  if (!variationMode) {
    document.querySelector("#variationThemeRow")?.classList.remove("invalid");
  }
}

function renderVariationThemeField(themes, selectedValue = "") {
  const wrap = document.querySelector("#variationThemeWrap");
  const hint = document.querySelector("#variationThemeHint");
  if (!wrap) return;
  wrap.innerHTML = "";
  if (!themes.length) {
    if (hint) hint.textContent = "当前 Product Type 暂无变种主题，请确认分类是否正确。";
    return;
  }
  wrap.appendChild(
    createDropdownSearchSelect("variation_theme", themes, {
      placeholder: "请选择",
      default: selectedValue,
    }),
  );
  if (hint) {
    hint.textContent = `已加载 ${themes.length} 个变种主题，可按名称搜索`;
  }
}

async function loadVariationThemes(options = {}) {
  const wrap = document.querySelector("#variationThemeWrap");
  const hint = document.querySelector("#variationThemeHint");
  if (!wrap || !isVariationSaleType()) return;

  const productType = productTypeInput.value;
  const preserved =
    options.selectedValue ||
    form.querySelector('[name="variation_theme"]')?.value ||
    "";

  if (!productType) {
    wrap.innerHTML = "";
    if (hint) hint.textContent = "请先选择产品分类，系统将按亚马逊 Schema 加载可选变种主题。";
    return;
  }

  if (Array.isArray(options.themes)) {
    currentVariationThemes = options.themes;
    renderVariationThemeField(currentVariationThemes, preserved);
    return;
  }

  if (hint) hint.textContent = "正在加载变种主题...";
  const marketplaceId = getSelectedStore()?.marketplace_id || "ATVPDKIKX0DER";
  try {
    const result = await apiGet(
      `/api/variation-themes?product_type=${encodeURIComponent(productType)}&marketplace_id=${encodeURIComponent(marketplaceId)}`,
    );
    currentVariationThemes = result.themes || [];
    renderVariationThemeField(currentVariationThemes, preserved);
    if (hint && currentVariationThemes.length) {
      hint.textContent = `已加载 ${currentVariationThemes.length} 个变种主题（来源：${
        result.source === "lingxing" ? "亚马逊 Schema" : "演示数据"
      }）`;
    }
  } catch (error) {
    wrap.innerHTML = "";
    if (hint) hint.textContent = error.message || "加载变种主题失败";
  }
}

function validateVariationInfo() {
  if (!isVariationSaleType()) return true;
  const theme = form.querySelector('[name="variation_theme"]')?.value.trim();
  const row = document.querySelector("#variationThemeRow");
  row?.classList.toggle("invalid", !theme);
  if (!theme) {
    showToast("请选择变种主题");
    return false;
  }
  return true;
}

let currentAttributeRules = [];
let currentBaselineRequired = new Set();
let currentRequiredSummary = { required_count: 0, required_keys: [], required_labels: {} };

function buildAttributeRuleContext(data) {
  const context = { ...data };
  if (data.quantity) {
    context.fulfillment_availability = "present";
  }
  if (data.upc_exemption === "yes") {
    context.attr_supplier_declared_has_product_identifier_exemption = "true";
    context.supplier_declared_has_product_identifier_exemption = "True";
  } else if (data.upc_exemption === "no") {
    context.attr_supplier_declared_has_product_identifier_exemption = "false";
    context.supplier_declared_has_product_identifier_exemption = "False";
  }
  if ((data.sale_type || "single") === "single") {
    context.parentage_level = "";
    context.child_parent_sku_relationship = "";
    context.variation_theme = "";
  } else if (data.variation_theme) {
    context.parentage_level = "present";
    context.child_parent_sku_relationship = "present";
    context.variation_theme = data.variation_theme;
  }
  return context;
}

function valuesForField(data, key) {
  const context = buildAttributeRuleContext(data);
  const raw =
    context[`attr_${key}`] ||
    context[`attr_${key}[]`] ||
    context[key] ||
    "";
  return splitAttributeValues(raw);
}

function conditionMatches(condition, data) {
  const values = valuesForField(data, condition.field);
  if (condition.operator === "present") return values.length > 0;
  if (condition.operator === "not_in") {
    if (!values.length) return false;
    return values.every((value) => !(condition.values || []).includes(String(value)));
  }
  return values.some((value) => (condition.values || []).includes(String(value)));
}

function ruleMatches(rule, data) {
  const conditions = rule.when || [];
  return conditions.length > 0 && conditions.every((condition) => conditionMatches(condition, data));
}

function computeAttributeFields(fields, data = formToObject()) {
  const requiredKeys = new Set(currentBaselineRequired || []);
  const shownKeys = new Set(currentBaselineRequired || []);
  (currentAttributeRules || []).forEach((rule) => {
    if (!ruleMatches(rule, data)) return;
    (rule.require || []).forEach((key) => requiredKeys.add(key));
    (rule.show || rule.require || []).forEach((key) => shownKeys.add(key));
  });

  return (fields || []).map((field) => {
    if (field.type === "subsection") return { ...field };
    const isSchemaRequired = Boolean(field.schema_required || field.baseline_required || field.required_static);
    const isPresetVisible = field.preset_visible === true;
    const dynamicRequired = requiredKeys.has(field.key);
    const required = isSchemaRequired || dynamicRequired || (isPresetVisible && field.required);
    const conditionalActive = shownKeys.has(field.key) || dynamicRequired;
    return {
      ...field,
      required,
      dynamic_required: dynamicRequired,
      hidden: isPresetVisible ? false : Boolean(field.conditional && !conditionalActive),
      advanced: isSchemaRequired || isPresetVisible ? false : conditionalActive ? false : Boolean(field.advanced && !required),
    };
  });
}

function attributeStateKey(fields) {
  return (fields || [])
    .filter((field) => field.type !== "subsection")
    .map((field) => `${field.key}:${field.required ? "1" : "0"}:${field.advanced ? "1" : "0"}:${field.hidden ? "1" : "0"}`)
    .join("|");
}

function restoreAttributeValues(data) {
  Object.entries(data)
    .filter(([name]) => name.startsWith("attr_"))
    .forEach(([name, value]) => setFieldValue(name, value));
}

function refreshAttributeState() {
  const data = formToObject();
  const nextFields = computeAttributeFields(baseAttributeFields, data);
  const nextSignature = attributeStateKey(nextFields);
  if (nextSignature === attributeStateSignature) return;
  renderAttributeFields(baseAttributeFields, { preserveData: data });
}

function visibleAttributeFields(fields) {
  const keyword = document.querySelector("#attributeSearchInput")?.value.trim() || "";
  const showAdvanced = showMoreAttributes || Boolean(keyword);
  const result = [];
  let index = 0;

  while (index < (fields || []).length) {
    const field = fields[index];
    if (field.type !== "subsection") {
      if (!field.hidden && (showAdvanced || !field.advanced)) {
        result.push(field);
      }
      index += 1;
      continue;
    }

    const section = field;
    index += 1;
    const sectionFields = [];
    while (index < fields.length && fields[index].type !== "subsection") {
      const item = fields[index];
      if (!item.hidden && (showAdvanced || !item.advanced)) {
        sectionFields.push(item);
      }
      index += 1;
    }
    if (sectionFields.length) {
      result.push({ ...section, advanced: false });
      result.push(...sectionFields);
    }
  }

  return result;
}

function renderAttributeFields(fields, options = {}) {
  if (!options.keepBase) {
    baseAttributeFields = fields || [];
  }
  allAttributeFields = computeAttributeFields(baseAttributeFields, options.preserveData || formToObject());
  attributeStateSignature = attributeStateKey(allAttributeFields);
  attributeFields.innerHTML = "";
  closeAttributePanel();
  visibleAttributeFields(allAttributeFields).forEach(renderAttributeField);
  closeAttributePanel();
  if (options.preserveData) restoreAttributeValues(options.preserveData);
  filterAttributeFields(document.querySelector("#attributeSearchInput")?.value || "");
  const toggle = document.querySelector("#toggleMoreAttributes");
  if (toggle) {
    const advancedCount = allAttributeFields.filter((field) => field.advanced && !field.hidden && field.type !== "subsection").length;
    toggle.textContent = showMoreAttributes ? "收起更多属性 ▴" : `更多属性（${advancedCount}）▾`;
  }
}

function filterAttributeFields(keyword) {
  const text = keyword.trim().toLowerCase();

  attributeFields.querySelectorAll(".attribute-subsection").forEach((node) => {
    node.classList.toggle("hidden", Boolean(text));
  });

  attributeFields.querySelectorAll(".attribute-row").forEach((row) => {
    const matched = !text || (row.dataset.searchText || "").includes(text);
    row.classList.toggle("hidden", !matched);
  });

  attributeFields.querySelectorAll(".attr-panel").forEach((panel) => {
    if (!text) {
      panel.classList.remove("hidden");
      return;
    }
    const hasVisible = [...panel.querySelectorAll(".attribute-row")].some(
      (row) => !row.classList.contains("hidden"),
    );
    panel.classList.toggle("hidden", !hasVisible);
  });
}

function bindAttributeTools() {
  const searchInput = document.querySelector("#attributeSearchInput");
  searchInput?.addEventListener("input", () => {
    renderAttributeFields(baseAttributeFields, { keepBase: true, preserveData: formToObject() });
    filterAttributeFields(searchInput.value);
  });

  document.querySelector("#toggleMoreAttributes")?.addEventListener("click", () => {
    showMoreAttributes = !showMoreAttributes;
    renderAttributeFields(baseAttributeFields, { keepBase: true, preserveData: formToObject() });
  });

  attributeFields?.addEventListener("input", () => {
    refreshAttributeState();
    updateAttributeMetaProgress();
  });
  attributeFields?.addEventListener("change", () => {
    refreshAttributeState();
    updateAttributeMetaProgress();
  });
}

function formToObject() {
  const data = Object.fromEntries(new FormData(form).entries());
  const checkboxNames = new Set();
  form.querySelectorAll('input[type="checkbox"][name^="attr_"][name$="[]"]').forEach((node) => {
    checkboxNames.add(node.name);
  });
  checkboxNames.forEach((name) => {
    delete data[name];
    const values = [...form.querySelectorAll(`[name="${CSS.escape(name)}"]:checked`)].map(
      (node) => node.value,
    );
    if (values.length) data[name] = values.join(", ");
  });
  return data;
}

function setFieldValue(name, value) {
  const fields = form.querySelectorAll(`[name="${CSS.escape(name)}"]`);
  if (!fields.length) {
    if (name.endsWith("[]")) {
      setCheckboxGroupValue(name, value);
    }
    return;
  }

  if (fields[0].type === "radio") {
    fields.forEach((field) => {
      field.checked = field.value === value;
    });
    return;
  }

  if (fields[0].type === "checkbox") {
    const values = String(value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    fields.forEach((field) => {
      field.checked = values.includes(field.value);
    });
    return;
  }

  fields[0].value = value ?? "";
}

function setCheckboxGroupValue(name, value) {
  const values = String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const boxes = form.querySelectorAll(`[name="${CSS.escape(name)}"]`);
  boxes.forEach((field) => {
    field.checked = values.includes(field.value);
  });
  values.forEach((item) => {
    const exists = [...boxes].some((field) => field.value === item);
    if (exists) return;
    const baseName = name.replace(/\[\]$/, "");
    const wrap = form.querySelector(`[data-field-key="${baseName.replace("attr_", "")}"]`);
    const otherRow = wrap?.querySelector(".checkbox-other-row");
    if (!wrap || !otherRow) return;
    const label = document.createElement("label");
    label.className = "checkbox-item";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = name;
    input.value = item;
    input.checked = true;
    label.appendChild(input);
    label.append(` ${item}`);
    wrap.insertBefore(label, otherRow);
  });
}

function attributeValue(value, field, marketplaceId) {
  const schema = field.schema || {};
  let nextValue = value;
  if (schema.value_type === "number" || schema.value_type === "integer") {
    nextValue = Number(value);
  } else if (schema.value_type === "boolean") {
    nextValue = value === true || String(value).toLowerCase() === "true";
  }

  const item = { [schema.value_key || "value"]: nextValue };
  if (schema.has_language_tag) item.language_tag = "en_US";
  if (schema.has_marketplace_id !== false) item.marketplace_id = marketplaceId;
  return item;
}

function splitAttributeValues(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function dimensionParts(field) {
  return field.dimension_parts || ["length", "width", "height"];
}

function dimensionPartValue(field, data, part) {
  return (
    data[`attr_${field.key}_${part}`] ||
    (field.key === "item_package_dimensions" ? data[`attr_item_package_${part}`] : "")
  );
}

function applySchemaAttribute(attributes, field, data, marketplaceId) {
  if (!field?.key || field.hidden || field.type === "subsection" || SKIP_DYNAMIC_ATTRIBUTE_KEYS.has(field.key)) return;

  if (field.type === "dimensions") {
    const parts = dimensionParts(field);
    const unit =
      data[`attr_${field.key}_unit`] ||
      data.attr_item_package_length_unit ||
      data.attr_item_package_width_unit ||
      data.attr_item_package_height_unit ||
      field.unit_default ||
      "inches";
    const item = { marketplace_id: marketplaceId };
    let complete = true;
    parts.forEach((part) => {
      const raw = dimensionPartValue(field, data, part);
      if (!raw) {
        complete = false;
        return;
      }
      item[part] = { value: Number(raw), unit };
    });
    if (complete) {
      attributes[field.key] = [item];
    }
    return;
  }

  if (field.type === "unit_count") {
    const value = data[`attr_${field.key}`];
    if (!value) return;
    const typeKey = field.type_key || `${field.key}_type`;
    attributes[field.key] = [
      {
        value: Number(value),
        type: {
          value: data[`attr_${typeKey}`] || field.type_default || "Count",
          language_tag: "en_US",
        },
        marketplace_id: marketplaceId,
      },
    ];
    return;
  }

  if (field.type === "unit") {
    const value = data[`attr_${field.key}`];
    if (!value) return;
    attributes[field.key] = [
      {
        value: Number(value),
        unit: data[`attr_${field.unit_key}`] || field.unit_default || "",
        marketplace_id: marketplaceId,
      },
    ];
    return;
  }

  if (field.key === "list_price") {
    const value = data[`attr_${field.key}`];
    if (value === undefined || value === null || value === "") return;
    attributes.list_price = [
      {
        value: Number(value),
        currency: data.attr_list_price_currency || field.currency_default || "USD",
        marketplace_id: marketplaceId,
      },
    ];
    return;
  }

  const rawValue = data[`attr_${field.key}`] || data[`attr_${field.key}[]`];
  const values = splitAttributeValues(rawValue);
  if (!values.length) return;
  attributes[field.key] = values.map((value) => attributeValue(value, field, marketplaceId));
}

function schemaFieldHasValue(field, data) {
  if (!field?.required || field.hidden || field.type === "subsection" || SKIP_DYNAMIC_ATTRIBUTE_KEYS.has(field.key)) return true;
  if (field.type === "dimensions") {
    return dimensionParts(field).every((part) => Boolean(dimensionPartValue(field, data, part)));
  }
  if (field.type === "unit_count") {
    return Boolean(data[`attr_${field.key}`]);
  }
  if (field.type === "unit") {
    return Boolean(data[`attr_${field.key}`]);
  }
  return Boolean(data[`attr_${field.key}`] || data[`attr_${field.key}[]`]);
}

function schemaFieldValues(field, data) {
  if (field.type === "checkbox_group") return valuesForField(data, field.key);
  const rawValue = data[`attr_${field.key}`] || data[`attr_${field.key}[]`];
  return splitAttributeValues(rawValue);
}

function validateFieldConstraints(field, data) {
  if (field.hidden || field.type === "subsection" || SKIP_DYNAMIC_ATTRIBUTE_KEYS.has(field.key)) return "";
  if (!schemaFieldHasValue(field, data)) {
    return `请填写产品属性：${field.label_zh || field.label_en || field.key}`;
  }
  if (!schemaFieldValues(field, data).length && field.type !== "dimensions" && field.type !== "unit" && field.type !== "unit_count") return "";

  const constraints = field.constraints || {};
  const options = (field.options || []).map((item) => String(normalizeOption(item).value));
  const values = schemaFieldValues(field, data);
  if (options.length && (field.type === "select" || field.type === "checkbox_group")) {
    const allowed = new Set(options.map((item) => item.toLowerCase()));
    const invalid = values.find((value) => !allowed.has(String(value).toLowerCase()));
    if (invalid) return `${field.label_zh || field.label_en || field.key} 只能选择系统给出的选项`;
  }

  if (field.type === "dimensions") {
    if (!field.required) return "";
    const length = data[`attr_${field.key}_length`] || data.attr_item_package_length;
    const width = data[`attr_${field.key}_width`] || data.attr_item_package_width;
    const height = data[`attr_${field.key}_height`] || data.attr_item_package_height;
    return length && width && height ? "" : `请完整填写 ${field.label_zh || field.label_en || field.key} 的长宽高`;
  }

  if (field.type === "unit" && field.required) {
    return data[`attr_${field.key}`] && data[`attr_${field.unit_key}`]
      ? ""
      : `请完整填写 ${field.label_zh || field.label_en || field.key} 的数值和单位`;
  }

  for (const value of values) {
    if (constraints.min_length != null && String(value).length < Number(constraints.min_length)) {
      return `${field.label_zh || field.label_en || field.key} 长度不能少于 ${constraints.min_length}`;
    }
    if (constraints.max_length != null && String(value).length > Number(constraints.max_length)) {
      return `${field.label_zh || field.label_en || field.key} 长度不能超过 ${constraints.max_length}`;
    }
    if (field.type === "number" || (field.schema || {}).value_type === "number" || (field.schema || {}).value_type === "integer") {
      const number = Number(value);
      if (Number.isNaN(number)) return `${field.label_zh || field.label_en || field.key} 必须是数字`;
      if (constraints.minimum != null && number < Number(constraints.minimum)) {
        return `${field.label_zh || field.label_en || field.key} 不能小于 ${constraints.minimum}`;
      }
      if (constraints.maximum != null && number > Number(constraints.maximum)) {
        return `${field.label_zh || field.label_en || field.key} 不能大于 ${constraints.maximum}`;
      }
    }
    if (field.type === "url") {
      try {
        new URL(value);
      } catch {
        return `${field.label_zh || field.label_en || field.key} 必须是有效 URL`;
      }
    }
  }
  return "";
}

function focusSchemaField(field) {
  const candidates = [
    `attr_${field.key}`,
    `attr_${field.key}[]`,
    `attr_${field.key}_length`,
  ];
  for (const name of candidates) {
    const control = form.querySelector(`[name="${CSS.escape(name)}"]`);
    if (control) {
      control.focus();
      control.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
  }
}

function validateSchemaRequiredAttributes(data) {
  allAttributeFields = computeAttributeFields(baseAttributeFields, data);
  const invalid = allAttributeFields.find((field) => validateFieldConstraints(field, data));
  if (!invalid) return true;

  const message = validateFieldConstraints(invalid, data);
  if (invalid.advanced && !showMoreAttributes) {
    showMoreAttributes = true;
    renderAttributeFields(baseAttributeFields, { keepBase: true, preserveData: data });
  }
  showToast(message);
  focusSchemaField(invalid);
  return false;
}

const SKIP_DYNAMIC_ATTRIBUTE_KEYS = new Set([
  "item_package_length",
  "item_package_width",
  "item_package_height",
  "item_package_length_unit",
  "item_package_width_unit",
  "item_package_height_unit",
  "unit_count_type",
  "list_price_currency",
]);

function buildAttributes(data) {
  const marketplaceId = data.marketplace || "ATVPDKIKX0DER";
  const textValue = (value) => [{ value, language_tag: "en_US", marketplace_id: marketplaceId }];
  const plainValue = (value) => [{ value, marketplace_id: marketplaceId }];

  const attributes = {};

  if (data.item_name) attributes.item_name = textValue(data.item_name);
  if (data.brand) attributes.brand = textValue(data.brand);
  const manufacturer = data.manufacturer || data.brand;
  if (manufacturer) attributes.manufacturer = textValue(manufacturer);
  if (data.product_description) attributes.product_description = textValue(data.product_description);

  const bullets = [
    data.bullet_point_1,
    data.bullet_point_2,
    data.bullet_point_3,
    data.bullet_point_4,
    data.bullet_point_5,
  ].filter(Boolean);
  if (bullets.length) {
    attributes.bullet_point = bullets.map((value) => ({
      value,
      language_tag: "en_US",
      marketplace_id: marketplaceId,
    }));
  }

  if (data.price) {
    attributes.purchasable_offer = [
      {
        marketplace_id: marketplaceId,
        our_price: [
          {
            schedule: [{ value_with_tax: Number(data.price) }],
          },
        ],
      },
    ];
  }

  if (data.quantity) {
    attributes.fulfillment_availability = [
      {
        fulfillment_channel_code: data.fulfillment_channel || "DEFAULT",
        quantity: Number(data.quantity),
        marketplace_id: marketplaceId,
      },
    ];
  }

  if (data.upc_exemption === "yes") {
    attributes.supplier_declared_has_product_identifier_exemption = plainValue(true);
  } else if (data.product_id) {
    attributes.externally_assigned_product_identifier = [
      {
        type: data.product_id_type,
        value: data.product_id,
        marketplace_id: marketplaceId,
      },
    ];
  }

  if (data.merchant_shipping_group) {
    attributes.merchant_shipping_group = plainValue(data.merchant_shipping_group);
  }

  if (data.generic_keyword) {
    attributes.generic_keyword = textValue(data.generic_keyword);
  }

  const images = productImages.length ? productImages : JSON.parse(data.product_images || "[]");
  if (images.length) {
    attributes.main_product_image_locator = [
      { media_location: images[0], marketplace_id: marketplaceId },
    ];
    images.slice(1).forEach((url, index) => {
      attributes[`other_product_image_locator_${index + 1}`] = [
        { media_location: url, marketplace_id: marketplaceId },
      ];
    });
  }

  const activeAttributeFields = computeAttributeFields(baseAttributeFields, data);
  activeAttributeFields.forEach((field) => applySchemaAttribute(attributes, field, data, marketplaceId));

  if (!attributes.included_components) {
    const includedRaw =
      data.attr_included_components ||
      data["attr_included_components[]"] ||
      data.attr_model_name ||
      data.item_name;
    const includedValues = String(includedRaw || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    if (includedValues.length) {
      attributes.included_components = includedValues.map((item) => ({
        value: item,
        language_tag: "en_US",
        marketplace_id: marketplaceId,
      }));
    }
  }

  const packageLength = data.attr_item_package_length;
  const packageWidth = data.attr_item_package_width;
  const packageHeight = data.attr_item_package_height;
  const packageUnit =
    data.attr_item_package_length_unit ||
    data.attr_item_package_width_unit ||
    data.attr_item_package_height_unit ||
    "inches";
  if (!attributes.item_package_dimensions && packageLength && packageWidth && packageHeight) {
    attributes.item_package_dimensions = [
      {
        length: { value: Number(packageLength), unit: packageUnit },
        width: { value: Number(packageWidth), unit: packageUnit },
        height: { value: Number(packageHeight), unit: packageUnit },
        marketplace_id: marketplaceId,
      },
    ];
  }

  // Handle item_dimensions (virtual dimension field for item_length/width/height)
  const itemLength = data.attr_item_dimensions_length || data.attr_item_length;
  const itemWidth = data.attr_item_dimensions_width || data.attr_item_width;
  const itemHeight = data.attr_item_dimensions_height || data.attr_item_height;
  const itemDimUnit =
    data.attr_item_dimensions_unit ||
    data.attr_item_length_unit ||
    data.attr_item_width_unit ||
    data.attr_item_height_unit ||
    "inches";
  if (itemLength || itemWidth || itemHeight) {
    attributes.item_dimensions = [
      {
        length: itemLength ? { value: Number(itemLength), unit: itemDimUnit } : undefined,
        width: itemWidth ? { value: Number(itemWidth), unit: itemDimUnit } : undefined,
        height: itemHeight ? { value: Number(itemHeight), unit: itemDimUnit } : undefined,
        marketplace_id: marketplaceId,
      },
    ];
  }

  const packageWeight = data.attr_item_package_weight;
  const packageWeightUnit = data.attr_item_package_weight_unit || "pounds";
  if (!attributes.item_package_weight && packageWeight) {
    attributes.item_package_weight = [
      {
        value: Number(packageWeight),
        unit: packageWeightUnit,
        marketplace_id: marketplaceId,
      },
    ];
  }

  try {
    const browseAttrs = JSON.parse(data.browse_node_attributes || "{}");
    if (browseAttrs.item_type_keyword) {
      attributes.item_type_keyword = plainValue(browseAttrs.item_type_keyword);
    } else if (browseAttrs.recommended_browse_nodes) {
      attributes.recommended_browse_nodes = plainValue(browseAttrs.recommended_browse_nodes);
    }
  } catch {
    // ignore invalid browse node json
  }

  if (data.sale_type === "variation" && data.variation_theme) {
    attributes.parentage_level = [{ value: "parent", marketplace_id: marketplaceId }];
    attributes.child_parent_sku_relationship = [
      {
        child_relationship_type: "variation",
        marketplace_id: marketplaceId,
      },
    ];
    attributes.variation_theme = [{ name: data.variation_theme, marketplace_id: marketplaceId }];
  }

  return attributes;
}

function getSelectedStore() {
  const account = accountSelect.value;
  const siteCode = siteSelect.value;
  if (!account || !siteCode) return null;
  return allStores.find((store) => store.account === account && store.site_code === siteCode) || null;
}

function uniqueAccounts(stores) {
  return [...new Set(stores.map((store) => store.account))].sort((a, b) => a.localeCompare(b, "zh-CN"));
}

function uniqueSites(stores) {
  const order = { CA: 1, MX: 2, US: 3 };
  const seen = new Set();
  return stores
    .filter((store) => {
      if (seen.has(store.site_code)) return false;
      seen.add(store.site_code);
      return true;
    })
    .sort((a, b) => order[a.site_code] - order[b.site_code]);
}

function fillSelect(select, items, getValue, getLabel, placeholder) {
  const current = select.value;
  select.innerHTML = "";
  select.appendChild(option("", placeholder));
  items.forEach((item) => {
    const node = option(getValue(item), getLabel(item));
    select.appendChild(node);
  });
  if ([...select.options].some((node) => node.value === current)) {
    select.value = current;
  }
}

function syncStoreFields() {
  const store = getSelectedStore();
  storeIdInput.value = store?.id || "";
  marketplaceIdInput.value = store?.marketplace_id || "";
  storeFullNameInput.value = store?.full_name || "";
}

function renderAccountOptions(siteCode = "") {
  const source = siteCode ? allStores.filter((store) => store.site_code === siteCode) : allStores;
  fillSelect(
    accountSelect,
    uniqueAccounts(source),
    (account) => account,
    (account) => account,
    "请选择店铺账号",
  );
}

function renderSiteOptions(account = "") {
  const source = account ? allStores.filter((store) => store.account === account) : allStores;
  fillSelect(
    siteSelect,
    uniqueSites(source),
    (store) => store.site_code,
    (store) => store.site_name,
    "请选择站点",
  );
}

function onAccountChange() {
  const account = accountSelect.value;
  renderSiteOptions(account);
  if (account) {
    const available = allStores.filter((store) => store.account === account);
    const currentSite = siteSelect.value;
    const stillValid = available.some((store) => store.site_code === currentSite);
    if (!stillValid && available.length) {
      siteSelect.value = available[0].site_code;
    }
  }
  syncStoreFields();
  loadShippingTemplates().catch(() => {});
}

function onSiteChange() {
  const siteCode = siteSelect.value;
  renderAccountOptions(siteCode);
  if (siteCode) {
    const available = allStores.filter((store) => store.site_code === siteCode);
    const currentAccount = accountSelect.value;
    const stillValid = available.some((store) => store.account === currentAccount);
    if (!stillValid && available.length) {
      accountSelect.value = available[0].account;
    }
  }
  syncStoreFields();
  loadShippingTemplates().catch(() => {});
}

function buildPayload(status) {
  const data = formToObject();
  const selectedStore = getSelectedStore();

  return {
    status,
    store_id: selectedStore?.id || Number(data.store_id) || null,
    store_account: selectedStore?.account || data.store_account || "",
    store_full_name: selectedStore?.full_name || data.store_full_name || "",
    store_name: selectedStore?.full_name || data.store_full_name || "",
    seller_id: selectedStore?.seller_id || data.seller_id || "",
    site_code: selectedStore?.site_code || data.site_code || "",
    site_name: selectedStore?.site_name || "",
    marketplace_id: selectedStore?.marketplace_id || data.marketplace || "",
    category_id: data.category || categoryIdInput.value || "",
    category_name: data.category_path || categoryDisplay.value || "",
    category_path: data.category_path || categoryDisplay.value || "",
    product_type: data.product_type || productTypeInput.value || "AUTO_PART",
    browse_node_attributes: data.browse_node_attributes || browseNodeAttributesInput.value || "{}",
    draft_no: data.draft_no || "",
    msku: data.seller_sku || data.parent_sku || "",
    local_sku: data.local_sku || "",
    operation_type: 0,
    source_url: data.source_url || "",
    attributes: buildAttributes(data),
    raw_form: data,
  };
}

function isUpcExempt() {
  return form.querySelector('input[name="upc_exemption"]:checked')?.value === "yes";
}

function syncProductIdState() {
  const productIdInput = document.querySelector("#productIdInput");
  const productIdType = document.querySelector("#productIdType");
  const autoFetchBtn = document.querySelector("#autoFetchProductId");
  const productIdRow = document.querySelector("#productIdRow");
  const exempt = isUpcExempt();
  const typeIsUpc = productIdType?.value === "UPC";
  const shouldDisable = exempt && typeIsUpc;

  if (productIdInput) {
    productIdInput.disabled = shouldDisable;
    if (shouldDisable) {
      productIdInput.value = "";
      productIdRow?.classList.remove("invalid");
    }
  }
  if (autoFetchBtn) {
    autoFetchBtn.disabled = shouldDisable;
  }
  productIdRow?.classList.toggle("product-id-exempt", shouldDisable);
}

function syncManufacturerFromBrand() {
  const brandInput = document.querySelector("#brandInput");
  const manufacturerInput = document.querySelector("#manufacturerInput");
  if (!brandInput || !manufacturerInput || !manufacturerLinkedToBrand) return;
  manufacturerInput.value = brandInput.value;
  manufacturerInput.dispatchEvent(new Event("input"));
  document.querySelector("#manufacturerRow")?.classList.remove("invalid");
}

function bindBrandManufacturerSync() {
  const brandInput = document.querySelector("#brandInput");
  const manufacturerInput = document.querySelector("#manufacturerInput");
  if (!brandInput || !manufacturerInput) return;

  brandInput.addEventListener("input", () => {
    syncManufacturerFromBrand();
  });

  manufacturerInput.addEventListener("input", () => {
    manufacturerLinkedToBrand = manufacturerInput.value === brandInput.value;
    if (manufacturerInput.value.trim()) {
      document.querySelector("#manufacturerRow")?.classList.remove("invalid");
    }
  });
}

function validateProductInfo() {
  const parentSku = document.querySelector("#parentSkuInput");
  const parentSkuRow = document.querySelector("#parentSkuRow");
  const productIdInput = document.querySelector("#productIdInput");
  const productIdRow = document.querySelector("#productIdRow");
  const manufacturerInput = document.querySelector("#manufacturerInput");
  const manufacturerRow = document.querySelector("#manufacturerRow");

  let isValid = true;

  const parentSkuValid = Boolean(parentSku?.value.trim());
  parentSkuRow?.classList.toggle("invalid", !parentSkuValid);
  if (!parentSkuValid) isValid = false;

  const needProductId = !isUpcExempt();
  const productIdValid =
    !needProductId || Boolean(productIdInput?.value.trim() && !productIdInput?.disabled);
  productIdRow?.classList.toggle("invalid", needProductId && !productIdValid);
  if (needProductId && !productIdValid) isValid = false;

  const manufacturerValid = Boolean(manufacturerInput?.value.trim());
  manufacturerRow?.classList.toggle("invalid", !manufacturerValid);
  if (!manufacturerValid) isValid = false;

  return isValid;
}

function updateImageCount() {
  const counter = document.querySelector("#imageSelectedCount");
  if (counter) counter.textContent = String(productImages.length);
  const hidden = document.querySelector("#productImagesData");
  if (hidden) hidden.value = JSON.stringify(productImages);
}

function renderImageGrid() {
  const grid = document.querySelector("#imageGrid");
  if (!grid) return;
  grid.innerHTML = "";

  if (!productImages.length) {
    const empty = document.createElement("div");
    empty.className = "image-slot-empty";
    empty.textContent = "暂无图片";
    grid.appendChild(empty);
    updateImageCount();
    return;
  }

  productImages.forEach((url, index) => {
    const item = document.createElement("div");
    item.className = "image-item";
    item.draggable = true;
    item.dataset.index = String(index);

    const img = document.createElement("img");
    img.src = url;
    img.alt = `产品图片${index + 1}`;

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "remove-btn";
    removeBtn.dataset.index = String(index);
    removeBtn.textContent = "×";

    item.appendChild(img);
    item.appendChild(removeBtn);
    grid.appendChild(item);
  });
  updateImageCount();
}

function hasDataUrlImages() {
  return productImages.some((url) => typeof url === "string" && url.startsWith("data:"));
}

function validateImagesForSubmit() {
  if (!hasDataUrlImages()) return true;
  showToast("检测到旧版本地图片，请删除后重新上传。");
  return false;
}

function addImages(urls) {
  const remain = MAX_IMAGES - productImages.length;
  if (remain <= 0) {
    showToast("图片最多选用9张");
    return;
  }
  const accepted = urls.slice(0, remain);
  productImages.push(...accepted);
  if (urls.length > remain) showToast(`最多还能添加${remain}张图片`);
  renderImageGrid();
}

async function uploadLocalFiles(files) {
  const remain = MAX_IMAGES - productImages.length;
  if (remain <= 0) {
    showToast("图片最多选用9张");
    return;
  }

  const queue = [...files].slice(0, remain);
  if (files.length > remain) showToast(`最多还能添加${remain}张图片`);

  showToast(`正在上传 ${queue.length} 张图片...`);
  for (const file of queue) {
    const url = await uploadImageFile(file);
    if (!url) throw new Error("图片上传未返回 URL");
    productImages.push(url);
    renderImageGrid();
  }
  showToast("图片已上传，可继续填写并发布");
}

function bindImageSection() {
  const dropdownWrap = document.querySelector(".dropdown-wrap");
  const selectBtn = document.querySelector("#selectImageBtn");
  const menu = document.querySelector("#imageSourceMenu");
  const localInput = document.querySelector("#localImageInput");
  const grid = document.querySelector("#imageGrid");

  selectBtn?.addEventListener("click", (event) => {
    event.stopPropagation();
    dropdownWrap?.classList.toggle("open");
  });

  document.addEventListener("click", () => dropdownWrap?.classList.remove("open"));

  menu?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-source]");
    if (!button) return;
    event.stopPropagation();
    dropdownWrap?.classList.remove("open");

    const source = button.dataset.source;
    if (source === "local") {
      localInput?.click();
      return;
    }
    if (source === "network") {
      const url = window.prompt("请输入网络图片 URL");
      if (url?.trim()) addImages([url.trim()]);
      return;
    }
    showToast("该功能开发中，请先使用本地图片或网络图片");
  });

  localInput?.addEventListener("change", async (event) => {
    const files = event.target.files;
    if (!files?.length) return;
    try {
      await uploadLocalFiles(files);
    } catch (error) {
      showToast(error.message);
    } finally {
      localInput.value = "";
    }
  });

  grid?.addEventListener("click", (event) => {
    const removeBtn = event.target.closest(".remove-btn");
    if (!removeBtn) return;
    const index = Number(removeBtn.dataset.index);
    productImages.splice(index, 1);
    renderImageGrid();
  });

  let dragIndex = null;
  grid?.addEventListener("dragstart", (event) => {
    const item = event.target.closest(".image-item");
    if (!item) return;
    dragIndex = Number(item.dataset.index);
    item.classList.add("dragging");
  });

  grid?.addEventListener("dragend", (event) => {
    event.target.closest(".image-item")?.classList.remove("dragging");
    dragIndex = null;
  });

  grid?.addEventListener("dragover", (event) => {
    event.preventDefault();
  });

  grid?.addEventListener("drop", (event) => {
    event.preventDefault();
    const item = event.target.closest(".image-item");
    if (item == null || dragIndex == null) return;
    const dropIndex = Number(item.dataset.index);
    if (dragIndex === dropIndex) return;
    const [moved] = productImages.splice(dragIndex, 1);
    productImages.splice(dropIndex, 0, moved);
    renderImageGrid();
  });

  renderImageGrid();
}

function restoreProductImages(rawForm) {
  try {
    productImages = JSON.parse(rawForm.product_images || "[]");
  } catch {
    productImages = [];
  }
  renderImageGrid();
}

function bindCounters() {
  document.querySelectorAll("input[maxlength]").forEach((field) => {
    const counter = document.querySelector(`.counter[data-for="${field.name}"]`);
    const update = () => {
      if (counter) {
        counter.textContent = `${field.value.length} / ${field.maxLength}`;
      }
      if (field.id === "parentSkuInput" && field.value.trim()) {
        document.querySelector("#parentSkuRow")?.classList.remove("invalid");
      }
    };
    field.addEventListener("input", update);
    update();
  });
}

async function saveDraft(status = "draft") {
  if (!validateImagesForSubmit()) return false;
  const payload = buildPayload(status);
  if (status === "ready" && !validateProductInfo()) {
    if (!document.querySelector("#parentSkuInput")?.value.trim()) {
      showToast("请填写Parent SKU");
      document.querySelector("#parentSkuInput")?.focus();
    } else if (!document.querySelector("#manufacturerInput")?.value.trim()) {
      showToast("请填写制造商");
      document.querySelector("#manufacturerInput")?.focus();
    } else {
      showToast("请填写Product ID");
      document.querySelector("#productIdInput")?.focus();
    }
    return false;
  }
  if (status === "ready" && !validateVariationInfo()) return false;
  if (status === "ready" && !validateSchemaRequiredAttributes(payload.raw_form || {})) return false;
  const result = await apiPost("/api/drafts", payload);
  if (result.data?.draft_no) {
    draftNo.value = result.data.draft_no;
  }
  await loadDrafts();
  showToast(result.message || "已保存");
  return true;
}

async function publishPreview() {
  if (!validateImagesForSubmit()) return;
  if (!validateProductInfo()) {
    if (!document.querySelector("#parentSkuInput")?.value.trim()) {
      showToast("请填写Parent SKU");
      document.querySelector("#parentSkuInput")?.focus();
    } else if (!document.querySelector("#manufacturerInput")?.value.trim()) {
      showToast("请填写制造商");
      document.querySelector("#manufacturerInput")?.focus();
    } else {
      showToast("请填写Product ID");
      document.querySelector("#productIdInput")?.focus();
    }
    return;
  }
  if (!draftNo.value) {
    const saved = await saveDraft("ready");
    if (!saved) return;
  }
  const payload = buildPayload("ready");
  if (!validateVariationInfo()) return;
  if (!validateSchemaRequiredAttributes(payload.raw_form || {})) return;
  const localSku = document.querySelector("#localSkuInput")?.value.trim();
  if (!localSku) {
    const go = window.confirm(
      "未填写「本地 SKU」，刊登成功后无法自动配对。\n\n可在任务列表点「配对」补填，或现在返回填写。\n\n是否仍继续提交？"
    );
    if (!go) {
      document.querySelector("#localSkuInput")?.focus();
      return;
    }
  }
  const result = await apiPost("/api/publish", payload);
  console.log("publish", result.data);
  await loadTasks();
  showToast(result.message || "已提交领星刊登，系统将自动查询结果");
}

async function loadStores() {
  const result = await apiGet("/api/stores");
  allStores = result.data || [];
  renderAccountOptions();
  renderSiteOptions();
  syncStoreFields();
  await loadShippingTemplates();
  if (result.message) {
    console.info("[stores]", result.source || "unknown", result.message);
  }
}

async function loadShippingTemplates() {
  const store = getSelectedStore();
  const productType = productTypeInput?.value || "AUTO_PART";
  const select = document.querySelector('select[name="merchant_shipping_group"]');
  if (!select || !store?.seller_id) return;

  try {
    const result = await apiGet(
      `/api/shipping-templates?seller_id=${encodeURIComponent(store.seller_id)}&marketplace_id=${encodeURIComponent(store.marketplace_id || "ATVPDKIKX0DER")}&product_type=${encodeURIComponent(productType)}`,
    );
    const items = result.data || [];
    const current = select.value;
    select.innerHTML =
      '<option value="">请选择</option>' +
      items
        .map(
          (item) =>
            `<option value="${escapeHtml(item.value)}">${escapeHtml(item.name || item.value)}</option>`,
        )
        .join("");
    if (current && [...select.options].some((opt) => opt.value === current)) {
      select.value = current;
    }
    if (result.message) {
      console.info("[shipping]", result.source || "unknown", result.message);
    }
  } catch (error) {
    console.warn("[shipping]", error.message);
  }
}

function getPresetRequiredFields() {
  const keys = currentRequiredSummary.required_keys || [];
  const labels = currentRequiredSummary.required_labels || {};
  const fieldMap = Object.fromEntries(
    (baseAttributeFields || [])
      .filter((field) => field.type !== "subsection")
      .map((field) => [field.key, field]),
  );

  if (!keys.length) {
    return (baseAttributeFields || []).filter(
      (field) => field.type !== "subsection" && field.required && field.preset_visible !== false,
    );
  }

  return keys.map((key) => {
    const field = fieldMap[key];
    if (field) return field;
    return {
      key,
      label_en: key,
      label_zh: labels[key] || key,
      required: true,
      preset_visible: true,
    };
  });
}

function scrollToAttributeField(fieldKey) {
  const row = attributeFields.querySelector(`.attribute-row[data-field-key="${fieldKey}"]`);
  if (!row) {
    showToast("该字段在下方，请向上滚动产品属性区域查看");
    return;
  }
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  const control = row.querySelector("input, select, textarea, button");
  control?.focus();
}

function updateAttributeMetaProgress() {
  if (!attributeMeta) return;
  const progressEl = attributeMeta.querySelector("#attrRequiredProgress");
  if (!progressEl) return;
  const requiredFields = getPresetRequiredFields();
  const data = formToObject();
  const filled = requiredFields.filter((field) => schemaFieldHasValue(field, data)).length;
  progressEl.textContent = `已填 ${filled}/${requiredFields.length}`;
}

function renderAttributeMeta() {
  if (!attributeMeta) return;
  const productType = productTypeInput.value || "AUTO_PART";
  const requiredFields = getPresetRequiredFields();
  const requiredCount = currentRequiredSummary.required_count || requiredFields.length;
  const source = attributeMeta.dataset.source || "领星 Schema";
  const checklist = requiredFields
    .map((field, index) => {
      const label = field.label_zh || field.label_en || field.key;
      return `<button type="button" class="attr-required-chip" data-field-key="${field.key}" title="点击定位到该字段">${index + 1}. ${label}</button>`;
    })
    .join("");

  attributeMeta.innerHTML = `
    <div class="attr-meta-row">
      <span class="attr-meta-item">Product Type: <strong>${productType}</strong></span>
      <span class="attr-meta-item">数据来源: ${source}</span>
      <span class="attr-meta-item">亚马逊必填项: <strong>${requiredCount}</strong> 个</span>
      <span class="attr-meta-item" id="attrRequiredProgress">已填 0/${requiredCount}</span>
      <span class="attr-meta-tip">必填项由亚马逊 Schema 自动识别，请完整填写后刊登</span>
    </div>
    <details class="attr-required-details" open>
      <summary>必填项清单（${requiredCount} 项，点击可定位）</summary>
      <div class="attr-required-list">${checklist}</div>
    </details>
  `;
  attributeMeta.dataset.source = attributeMeta.dataset.source || source;

  attributeMeta.querySelectorAll(".attr-required-chip").forEach((button) => {
    button.addEventListener("click", () => scrollToAttributeField(button.dataset.fieldKey));
  });
  updateAttributeMetaProgress();
}

async function loadSchema() {
  const productType = productTypeInput.value || "AUTO_PART";
  const marketplaceId = getSelectedStore()?.marketplace_id || "ATVPDKIKX0DER";
  const result = await apiGet(
    `/api/schema?product_type=${encodeURIComponent(productType)}&marketplace_id=${encodeURIComponent(marketplaceId)}`,
  );
  currentAttributeRules = result.rules || result.data?.rules || [];
  currentBaselineRequired = new Set(result.baseline_required_keys || result.data?.baseline_required_keys || []);
  currentRequiredSummary = result.required_summary || {
    required_count: (result.required || []).length,
    required_keys: result.required || [],
    required_labels: {},
  };
  if (attributeMeta) {
    attributeMeta.dataset.source = result.source === "lingxing" ? "领星 Schema" : "演示模板";
  }
  renderAttributeFields(result.attributes || result.data?.attributes || []);
  renderAttributeMeta();
  currentVariationThemes = result.variation_themes || result.data?.variation_themes || [];
  syncSaleTypeState();
  if (isVariationSaleType()) {
    await loadVariationThemes({ themes: currentVariationThemes });
  }
  await loadShippingTemplates();
  showToast(
    result.message ||
      `已加载 ${result.product_type || productType} 属性模板，共 ${currentRequiredSummary.required_count || getPresetRequiredFields().length} 个亚马逊必填项`,
  );
}

let taskPollTimer = null;

const ACTIVE_TASK_STATUSES = new Set(["SUBMITTED", "PROCESSING", "LISTING_SYNCING"]);

function statusPillClass(status) {
  if (status === "COMPLETED" || status === "SUCCESS") return "success";
  if (status === "LISTING_SYNCED") return "success";
  if (status === "FAILED" || status === "TIMEOUT" || status === "SYNC_TIMEOUT") return "failed";
  if (ACTIVE_TASK_STATUSES.has(status)) return "processing";
  return "";
}

function syncTaskPolling(tasks) {
  const hasActive = (tasks || []).some((task) => ACTIVE_TASK_STATUSES.has(task.status));
  if (hasActive && !taskPollTimer) {
    taskPollTimer = window.setInterval(() => {
      loadTasks().catch(() => {});
    }, 15000);
  } else if (!hasActive && taskPollTimer) {
    window.clearInterval(taskPollTimer);
    taskPollTimer = null;
  }
}

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatFailureReason(raw) {
  if (!raw) return "";
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed
        .map((item, index) => {
          const message = item.message || item.msg || JSON.stringify(item);
          const code = item.code ? `[${item.code}] ` : "";
          return `${index + 1}. ${code}${message}`;
        })
        .join("\n");
    }
  } catch {
    // keep plain text
  }
  return String(raw);
}

function renderDrafts(drafts) {
  draftList.innerHTML = "";
  if (!drafts.length) {
    draftList.innerHTML = '<div class="empty">暂无草稿</div>';
    return;
  }

  drafts.forEach((draft) => {
    const item = document.createElement("div");
    item.className = "record-item";
    item.innerHTML = `
      <div class="record-header">
        <div class="record-title">${draft.raw_form?.item_name || "未填写标题"}</div>
      </div>
      <div class="record-meta">
        <div class="record-meta-row">草稿号：${draft.draft_no}</div>
        <div class="record-meta-row">店铺：${draft.store_name || "-"}</div>
        <div class="record-meta-row">SKU：${draft.msku || "-"}</div>
        <div class="record-meta-row">更新时间：${draft.updated_at || "-"}</div>
      </div>
      <div class="record-actions">
        <button type="button" class="btn ghost" data-draft-no="${draft.draft_no}">恢复</button>
        <button type="button" class="btn ghost danger" data-draft-delete="${draft.draft_no}">删除</button>
      </div>
    `;
    draftList.appendChild(item);
  });
}

function renderTasks(tasks) {
  taskList.innerHTML = "";
  if (!tasks.length) {
    taskList.innerHTML = '<div class="empty">暂无任务</div>';
    return;
  }

  tasks.forEach((task) => {
    const item = document.createElement("div");
    item.className = "record-item";
    const pollHint =
      ACTIVE_TASK_STATUSES.has(task.status) && task.record_unique_id
        ? `自动跟进中${task.poll_attempt ? `（刊登已查 ${task.poll_attempt} 次` : ""}${task.sync_attempt ? `${task.poll_attempt ? "，" : "（"}Listing 已查 ${task.sync_attempt} 次` : ""}${task.poll_attempt || task.sync_attempt ? "）" : ""}`
        : "";
    const failureText = formatFailureReason(task.failure_reason);
    const batchInfo = !failureText && task.record_unique_id ? `批次号：${task.record_unique_id}` : "";
    const pillClass = statusPillClass(task.status);
    item.innerHTML = `
      <div class="record-header">
        <div class="record-title">${task.msku || "未填写 MSKU"}</div>
        <span class="status-pill ${pillClass}">${task.status_text || task.status}</span>
      </div>
      <div class="record-meta">
        <div class="record-meta-row">任务号：${task.task_no}</div>
        <div class="record-meta-row">店铺：${task.store_name || "-"}</div>
        <div class="record-meta-row">类型：${task.product_type || "-"}</div>
        <div class="record-meta-row">创建：${task.created_at || "-"}</div>
        ${pollHint ? `<div class="record-meta-row">${pollHint}</div>` : ""}
        ${task.asin ? `<div class="record-meta-row">ASIN：${task.asin}</div>` : ""}
        ${task.local_sku ? `<div class="record-meta-row">本地 SKU：${task.local_sku}</div>` : ""}
        ${
          task.status === "LISTING_SYNCED" && !task.sku_paired && !task.local_sku
            ? '<div class="record-meta-row record-warn">未填本地 SKU，请点击下方「填写 SKU 并配对」</div>'
            : ""
        }
        ${batchInfo ? `<div class="record-meta-row">${batchInfo}</div>` : ""}
      </div>
      ${
        failureText
          ? `<div class="record-failure"><div class="record-failure-title">失败原因</div>${escapeHtml(failureText)}</div>`
          : ""
      }
      <div class="record-actions">
        ${task.record_unique_id && ["SUBMITTED", "PROCESSING", "TIMEOUT"].includes(task.status) ? '<button type="button" class="btn ghost poll-task">查刊登</button>' : ""}
        ${["LISTING_SYNCING", "SYNC_TIMEOUT", "LISTING_SYNCED"].includes(task.status) ? '<button type="button" class="btn ghost sync-task">查Listing</button>' : ""}
        ${
          task.status === "LISTING_SYNCED"
            ? `<button type="button" class="btn ghost pair-task">${task.local_sku ? "配对" : "填写 SKU 并配对"}</button>`
            : ""
        }
        ${["FAILED", "TIMEOUT"].includes(task.status) ? '<button type="button" class="btn ghost retry-task">重新提交</button>' : ""}
      </div>
    `;
    item.querySelector(".poll-task")?.addEventListener("click", () => {
      pollPublishResult(task.task_no).catch((error) => showToast(error.message));
    });
    item.querySelector(".sync-task")?.addEventListener("click", () => {
      syncListingNow(task.task_no).catch((error) => showToast(error.message));
    });
    item.querySelector(".pair-task")?.addEventListener("click", () => {
      pairSkuNow(task).catch((error) => showToast(error.message));
    });
    item.querySelector(".retry-task")?.addEventListener("click", () => {
      retryTask(task.task_no).catch((error) => showToast(error.message));
    });
    taskList.appendChild(item);
  });
}

async function loadDrafts() {
  const result = await apiGet("/api/drafts");
  renderDrafts(result.data || []);
}

async function pollPublishResult(taskNo) {
  const result = await apiGet(`/api/publish/result/${encodeURIComponent(taskNo)}`);
  await loadTasks();
  showToast(result.message || "已刷新刊登结果");
}

async function syncListingNow(taskNo) {
  const result = await apiPost(`/api/tasks/${encodeURIComponent(taskNo)}/sync`, {});
  await loadTasks();
  showToast(result.message || "已查询 Listing");
}

async function pairSkuNow(task) {
  const taskNo = task.task_no;
  let localSku = (task.local_sku || "").trim();
  if (!localSku) {
    const input = window.prompt("请输入领星 ERP 本地 SKU（与库存系统一致的编码）：");
    if (!input?.trim()) {
      showToast("已取消配对");
      return;
    }
    localSku = input.trim();
  }
  const result = await apiPost(`/api/tasks/${encodeURIComponent(taskNo)}/pair`, {
    local_sku: localSku,
  });
  await loadTasks();
  showToast(result.message || "SKU 配对成功");
}

async function deleteDraft(draftNo) {
  if (!window.confirm("确定删除这条草稿吗？")) return;
  const result = await apiPost("/api/drafts/delete", { draft_no: draftNo });
  await loadDrafts();
  showToast(result.message || "草稿已删除");
}

async function retryTask(taskNo) {
  if (!window.confirm("将使用任务保存的资料重新提交刊登，是否继续？")) return;
  const result = await apiPost(`/api/tasks/${encodeURIComponent(taskNo)}/retry`, {});
  await loadTasks();
  showToast(result.message || "已重新提交");
}

async function loadTasks() {
  const status = document.querySelector("#taskStatusFilter")?.value || "";
  const url = status ? `/api/tasks?status=${encodeURIComponent(status)}` : "/api/tasks";
  const result = await apiGet(url);
  const tasks = result.data || [];
  renderTasks(tasks);
  syncTaskPolling(tasks);
}

async function restoreDraft(draftNumber) {
  const result = await apiGet(`/api/drafts/${encodeURIComponent(draftNumber)}`);
  const draft = result.data || {};
  const rawForm = draft.raw_form || {};
  const storeAccount = rawForm.store_account || draft.store_account || "";
  const siteCode = rawForm.site_code || draft.site_code || "";

  renderAccountOptions(siteCode);
  renderSiteOptions(storeAccount);
  accountSelect.value = storeAccount;
  siteSelect.value = siteCode;
  syncStoreFields();

  Object.entries(rawForm)
    .filter(
      ([name]) =>
        !name.startsWith("attr_") &&
        !["store_account", "site_code", "store_id", "marketplace", "store_full_name", "product_images"].includes(
          name,
        ),
    )
    .forEach(([name, value]) => setFieldValue(name, value));
  const brandValue = document.querySelector("#brandInput")?.value.trim() || "";
  const manufacturerValue = document.querySelector("#manufacturerInput")?.value.trim() || "";
  manufacturerLinkedToBrand = !manufacturerValue || manufacturerValue === brandValue;
  if (!manufacturerValue && brandValue) {
    syncManufacturerFromBrand();
  }
  restoreProductImages(rawForm);
  syncProductIdState();
  categoryDisplay.value = rawForm.category_path || draft.category_path || draft.category_name || "";
  categoryIdInput.value = rawForm.category || draft.category_id || "";
  categoryPathInput.value = rawForm.category_path || draft.category_path || "";
  productTypeInput.value = rawForm.product_type || draft.product_type || "";
  browseNodeAttributesInput.value = rawForm.browse_node_attributes || draft.browse_node_attributes || "{}";
  categoryMeta.textContent = productTypeInput.value ? `Product Type: ${productTypeInput.value}` : "";
  syncSaleTypeState();
  await loadSchema();
  if (isVariationSaleType(rawForm)) {
    await loadVariationThemes({
      selectedValue: rawForm.variation_theme || "",
    });
  }
  if (!rawForm.attr_included_components && rawForm["attr_included_components[]"]) {
    rawForm.attr_included_components = rawForm["attr_included_components[]"];
  }
  if (!rawForm.attr_item_package_dimensions_length && rawForm.attr_item_package_length) {
    rawForm.attr_item_package_dimensions_length = rawForm.attr_item_package_length;
    rawForm.attr_item_package_dimensions_width = rawForm.attr_item_package_width;
    rawForm.attr_item_package_dimensions_height = rawForm.attr_item_package_height;
    rawForm.attr_item_package_dimensions_unit =
      rawForm.attr_item_package_length_unit ||
      rawForm.attr_item_package_width_unit ||
      rawForm.attr_item_package_height_unit ||
      "inches";
  }
  // Convert legacy item_length/width/height to item_dimensions format
  if (!rawForm.attr_item_dimensions_length && rawForm.attr_item_length) {
    rawForm.attr_item_dimensions_length = rawForm.attr_item_length;
    rawForm.attr_item_dimensions_width = rawForm.attr_item_width;
    rawForm.attr_item_dimensions_height = rawForm.attr_item_height;
    rawForm.attr_item_dimensions_unit =
      rawForm.attr_item_length_unit ||
      rawForm.attr_item_width_unit ||
      rawForm.attr_item_height_unit ||
      "inches";
  }
  Object.entries(rawForm)
    .filter(([name]) => name.startsWith("attr_"))
    .forEach(([name, value]) => setFieldValue(name, value));
  draftNo.value = result.data.draft_no;
  showToast("草稿已恢复");
}

function bindActions() {
  ["saveDraftTop", "saveDraftBottom", "saveOnlyTop", "saveOnlyBottom"].forEach((id) => {
    document.querySelector(`#${id}`).addEventListener("click", (event) => {
      event.preventDefault();
      saveDraft(id.includes("saveOnly") ? "ready" : "draft").catch((error) => showToast(error.message));
    });
  });

  ["publishTop", "publishBottom"].forEach((id) => {
    document.querySelector(`#${id}`).addEventListener("click", (event) => {
      event.preventDefault();
      publishPreview().catch((error) => showToast(error.message));
    });
  });

  document.querySelector("#openCategoryPicker").addEventListener("click", (event) => {
    event.preventDefault();
    openCategoryPicker().catch((error) => showToast(error.message));
  });

  document.querySelector("#closeCategoryPicker").addEventListener("click", closeCategoryPicker);
  document.querySelector("#cancelCategoryPicker").addEventListener("click", closeCategoryPicker);
  document.querySelector("#categoryModalMask").addEventListener("click", closeCategoryPicker);
  confirmCategoryPicker.addEventListener("click", () => {
    confirmCategorySelection().catch((error) => showToast(error.message));
  });

  let searchTimer = null;
  categorySearchInput.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
      searchCategories(categorySearchInput.value).catch((error) => showToast(error.message));
    }, 250);
  });

  accountSelect.addEventListener("change", onAccountChange);
  siteSelect.addEventListener("change", onSiteChange);

  document.querySelector("#refreshDrafts").addEventListener("click", () => {
    loadDrafts().catch((error) => showToast(error.message));
  });

  document.querySelector("#refreshTasks").addEventListener("click", () => {
    loadTasks().catch((error) => showToast(error.message));
  });
  document.querySelector("#taskStatusFilter")?.addEventListener("change", () => {
    loadTasks().catch((error) => showToast(error.message));
  });
  document.querySelector("#shippingTemplateRefresh")?.addEventListener("click", () => {
    loadShippingTemplates().catch((error) => showToast(error.message));
  });

  draftList.addEventListener("click", (event) => {
    const deleteBtn = event.target.closest("[data-draft-delete]");
    if (deleteBtn) {
      deleteDraft(deleteBtn.dataset.draftDelete).catch((error) => showToast(error.message));
      return;
    }
    const button = event.target.closest("[data-draft-no]");
    if (!button) return;
    restoreDraft(button.dataset.draftNo).catch((error) => showToast(error.message));
  });

  bindCounters();
  bindBrandManufacturerSync();
  bindAttributeTools();
  bindImageSection();

  form.querySelectorAll('input[name="upc_exemption"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      syncProductIdState();
      refreshAttributeState();
      updateAttributeMetaProgress();
    });
  });
  form.querySelectorAll('input[name="sale_type"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      syncSaleTypeState();
      if (isVariationSaleType()) {
        loadVariationThemes().catch((error) => showToast(error.message));
      }
      refreshAttributeState();
      updateAttributeMetaProgress();
    });
  });
  document.querySelector("#variationThemeWrap")?.addEventListener("click", () => {
    window.setTimeout(() => {
      document.querySelector("#variationThemeRow")?.classList.remove("invalid");
      refreshAttributeState();
      updateAttributeMetaProgress();
    }, 0);
  });
  form.querySelector('input[name="quantity"]')?.addEventListener("input", () => {
    refreshAttributeState();
    updateAttributeMetaProgress();
  });
  form.querySelector('select[name="fulfillment_channel"]')?.addEventListener("change", () => {
    refreshAttributeState();
    updateAttributeMetaProgress();
  });
  document.querySelector("#productIdType")?.addEventListener("change", syncProductIdState);
  document.querySelector("#productIdInput")?.addEventListener("input", () => {
    if (document.querySelector("#productIdInput")?.value.trim()) {
      document.querySelector("#productIdRow")?.classList.remove("invalid");
    }
  });
  syncProductIdState();
}

async function init() {
  if (window.location.protocol === "file:") {
    showToast("请通过 start.bat 启动后访问 http://127.0.0.1:8001/create-product");
    return;
  }
  bindActions();
  await loadStores();
  if (allStores.length) {
    accountSelect.value = allStores[0].account;
    onAccountChange();
    siteSelect.value = allStores[0].site_code;
    onSiteChange();
  }
  await loadSchema();
  await Promise.all([loadDrafts(), loadTasks()]);

  // Check for listing content from listing-tools page
  const pending = localStorage.getItem("listing_apply");
  if (pending) {
    try {
      const data = JSON.parse(pending);
      if (window.confirm("检测到 Listing 生成器暂存的内容，是否填入产品表单？\n\n标题: " + (data.title || "").substring(0, 80) + "...")) {
        setFieldValue("item_name", data.title || "");
        (data.bullets || []).forEach((b, i) => setFieldValue("bullet_point_" + (i + 1), b || ""));
        setFieldValue("product_description", data.description || "");
        setFieldValue("generic_keyword", data.search_terms || "");
        showToast("已填入生成器内容");
      }
    } catch (e) { /* ignore */ }
    localStorage.removeItem("listing_apply");
  }
}

init().catch((error) => showToast(error.message));
