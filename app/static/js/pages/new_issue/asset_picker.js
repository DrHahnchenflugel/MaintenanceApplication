/* static/js/pages/new_issue/asset_picker.js
   Asset picker for New Issue page.

   HTML requirements:
   - button#toggleAssetPicker
   - div#assetPicker (with data-* urls; see below)
   - input#assetId (hidden)
   - input#assetSearch
   - div#apResults
   - button#apApply
   - button#apClear
   - select#apSite (optional)
   - select#apStatus (optional; if not server-rendered, will load from API)
   - select#apCategory (optional)
   - select#apMake
   - select#apModel
   - select#apVariant

   data attributes on #assetPicker:
   - data-assets-url              (default: /maintenance/api/v2/assets)
   - data-asset-statuses-url      (default: /maintenance/api/v2/asset-statuses)
   - data-makes-url               (default: /maintenance/api/v2/assets/makes)
   - data-models-url              (default: /maintenance/api/v2/assets/models)
   - data-variants-url            (default: /maintenance/api/v2/assets/variants)
*/

(function () {
  const panel = document.getElementById("assetPicker");
  const toggleBtn = document.getElementById("toggleAssetPicker");
  if (!panel || !toggleBtn) return;

  const el = {
    panel,
    toggleBtn,

    input: document.getElementById("assetSearch"),
    results: document.getElementById("apResults"),
    apply: document.getElementById("apApply"),
    clear: document.getElementById("apClear"),

    site: document.getElementById("apSite"),
    status: document.getElementById("apStatus"),
    category: document.getElementById("apCategory"),
    make: document.getElementById("apMake"),
    model: document.getElementById("apModel"),
    variant: document.getElementById("apVariant"),

    assetId: document.getElementById("assetId"),
  };

  const headerTag = document.querySelector(".new-issue-asset__tag");
  const headerFallback = document.querySelector(".new-issue-asset__title .muted");

  const URLS = {
    assets: panel.dataset.assetsUrl || "/maintenance/api/v2/assets",
    statuses: panel.dataset.assetStatusesUrl || "/maintenance/api/v2/asset-statuses",
    makes: panel.dataset.makesUrl || "/maintenance/api/v2/assets/makes",
    models: panel.dataset.modelsUrl || "/maintenance/api/v2/assets/models",
    variants: panel.dataset.variantsUrl || "/maintenance/api/v2/assets/variants",
  };

  // status_id(UUID) -> label (fallback if assets don't include status fields)
  const statusLabelById = new Map();

  // -----------------------------
  // Utilities
  // -----------------------------
  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  function setHeaderText(html) {
    if (headerTag) headerTag.innerHTML = html;
    else if (headerFallback) headerFallback.innerHTML = html;
  }

  function setEmpty(msg) {
    if (!el.results) return;
    el.results.innerHTML = `<div class="asset-picker__empty muted">${escapeHtml(msg)}</div>`;
  }

  function setLoading(msg = "Loading…") {
    if (!el.results) return;
    el.results.innerHTML = `<div class="asset-picker__empty muted">${escapeHtml(msg)}</div>`;
  }

  function resetSelect(selectEl, disabled = false) {
    if (!selectEl) return;
    selectEl.innerHTML = `<option value="">All</option>`;
    selectEl.value = "";
    selectEl.disabled = !!disabled;
  }

  async function fetchJson(url) {
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    return res.json();
  }

  // -----------------------------
  // Toggle open/close
  // -----------------------------
  el.toggleBtn.addEventListener("click", () => {
    el.panel.hidden = !el.panel.hidden;
    if (!el.panel.hidden) {
      if (el.input) el.input.focus();
    }
  });

  // -----------------------------
  // Load Statuses (if dropdown not server-rendered)
  // -----------------------------
  async function loadAssetStatuses() {
    if (!el.status) return;

    // If already populated server-side, still build map if possible via API,
    // but don't overwrite existing options.
    const alreadyHasOptions = (el.status.options?.length || 0) > 1;

    try {
      const statuses = await fetchJson(URLS.statuses);
      statuses.forEach((s) => statusLabelById.set(String(s.id), String(s.label)));

      if (alreadyHasOptions) return;

      const opts = statuses
        .slice()
        .sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0))
        .map((s) => `<option value="${escapeHtml(s.id)}">${escapeHtml(s.label)}</option>`)
        .join("");

      el.status.innerHTML = `<option value="">All</option>${opts}`;
    } catch (e) {
      console.error("Failed to load asset statuses:", e);
    }
  }

  // -----------------------------
  // Cascading lookups: Categories -> Makes -> Models -> Variants
  // -----------------------------
  async function loadCategories() {
    if (!el.category) return;

    const alreadyHas = (el.category.options?.length || 0) > 1;
    if (alreadyHas) return;

    try {
      const items = await fetchJson(panel.dataset.assetCategoriesUrl);
      el.category.innerHTML =
        '<option value="">All</option>' +
        items.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.label)}</option>`).join("");
    } catch (e) {
      console.error("Failed to load categories:", e);
    }
  }


  async function loadMakesForCategory(categoryId) {
    if (!el.make) return;

    resetSelect(el.make, true);
    resetSelect(el.model, true);
    resetSelect(el.variant, true);

    const url = categoryId
      ? `${URLS.makes}?category_id=${encodeURIComponent(categoryId)}`
      : `${URLS.makes}`;

    try {
      const items = await fetchJson(url);

      el.make.innerHTML =
        `<option value="">All</option>` +
        items.map(x => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.label)}</option>`).join("");

      el.make.disabled = false;
    } catch (e) {
      console.error("Failed to load makes:", e);
      resetSelect(el.make, true);
    }
  }


  async function loadModelsForMake(makeId) {
    if (!el.model) return;

    resetSelect(el.model, true);
    resetSelect(el.variant, true);

    if (!makeId) return;

    try {
      const url = `${URLS.models}?make_id=${encodeURIComponent(makeId)}`;
      const items = await fetchJson(url);

      el.model.innerHTML =
        `<option value="">All</option>` +
        items.map((x) => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.label)}</option>`).join("");

      el.model.disabled = false;
    } catch (e) {
      console.error("Failed to load models:", e);
      resetSelect(el.model, true);
    }
  }

  async function loadVariantsForModel(modelId) {
    if (!el.variant) return;

    resetSelect(el.variant, true);

    if (!modelId) return;

    try {
      const url = `${URLS.variants}?model_id=${encodeURIComponent(modelId)}`;
      const items = await fetchJson(url);

      el.variant.innerHTML =
        `<option value="">All</option>` +
        items.map((x) => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.label)}</option>`).join("");

      el.variant.disabled = false;
    } catch (e) {
      console.error("Failed to load variants:", e);
      resetSelect(el.variant, true);
    }
  }

  el.category?.addEventListener("change", () => {
    loadMakesForCategory(el.category.value);
  });

  el.make?.addEventListener("change", () => {
    loadModelsForMake(el.make.value);
  });

  el.model?.addEventListener("change", () => {
    loadVariantsForModel(el.model.value);
  });

  // -----------------------------
  // Build query params for /assets search
  // -----------------------------
  function buildAssetSearchParams() {
    const p = new URLSearchParams();

    // FK filters
    if (el.site?.value) p.set("site_id", el.site.value);
    if (el.status?.value) p.set("status_id", el.status.value);
    if (el.category?.value) p.set("category_id", el.category.value);
    if (el.make?.value) p.set("make_id", el.make.value);
    if (el.model?.value) p.set("model_id", el.model.value);
    if (el.variant?.value) p.set("variant_id", el.variant.value);

    // string search (your API supports asset_tag)
    const tag = (el.input?.value || "").trim();
    if (tag) p.set("asset_tag", tag);

    // picker defaults
    p.set("page", "1");
    p.set("page_size", "25");
    p.set("retired", "active");

    // optional expansions (safe if ignored)
    p.set("include", "site,make,model,variant,status");
    p.set("sort", "asset_tag");

    return p;
  }

  // -----------------------------
  // Results rendering
  // -----------------------------
  function deriveStatusLabel(asset) {
    if (asset.status_label) return String(asset.status_label);
    if (asset.status_code) return String(asset.status_code);

    const sid = asset.status_id ? String(asset.status_id) : "";
    return sid && statusLabelById.has(sid) ? statusLabelById.get(sid) : "";
  }

  function deriveSite(asset) {
    return asset.site_shorthand || asset.site?.shorthand || "";
  }

  function deriveMake(asset) {
    return asset.make || asset.make_label || asset.make?.label || asset.make?.name || "";
  }

  function deriveModel(asset) {
    return asset.model || asset.model_label || asset.model?.label || asset.model?.name || "";
  }

  function deriveVariant(asset) {
    return asset.variant || asset.variant_label || asset.variant?.label || asset.variant?.name || "";
  }

  function renderResults(items) {
    if (!el.results) return;

    if (!items || items.length === 0) {
      setEmpty("No matching assets.");
      return;
    }

    const rows = items.map((a) => {
      const id = escapeHtml(a.id || a.asset_id || "");
      const tag = escapeHtml(a.asset_tag || "");
      const serial = escapeHtml(a.serial_num || "");
      const site = escapeHtml(deriveSite(a));
      const make = escapeHtml(deriveMake(a));
      const model = escapeHtml(deriveModel(a));
      const variant = escapeHtml(deriveVariant(a));
      const status = escapeHtml(deriveStatusLabel(a));

      const line1 = [site, [make, model].filter(Boolean).join(" "), variant]
        .filter(Boolean)
        .join(" · ");

      return `
        <div class="asset-picker__row" role="button" tabindex="0"
             data-asset-id="${id}"
             data-asset-tag="${tag}"
             data-site="${site}"
             data-make="${make}"
             data-model="${model}"
             data-variant="${variant}">
          <div class="asset-picker__tag">${tag}</div>
          <div class="asset-picker__meta">${line1 || "&nbsp;"}</div>
          <div class="asset-picker__meta">${serial || "&nbsp;"}</div>
          <div class="asset-picker__pill">${status || "—"}</div>
        </div>
      `;
    }).join("");

    el.results.innerHTML = `<div class="asset-picker__list">${rows}</div>`;
  }

  // -----------------------------
  // Search actions
  // -----------------------------
  async function runSearch() {
    setLoading("Searching…");

    const url = `${URLS.assets}?${buildAssetSearchParams().toString()}`;

    try {
      const data = await fetchJson(url);
      const items = Array.isArray(data) ? data : (data.items || []);
      renderResults(items);
    } catch (e) {
      console.error("Asset search failed:", e);
      setEmpty("Search failed. Check console + API route.");
    }
  }

  function clearAll() {
    if (el.input) el.input.value = "";

    if (el.site) el.site.value = "";
    if (el.status) el.status.value = "";
    if (el.category) el.category.value = "";

    // Reset cascade
    resetSelect(el.make, true);
    resetSelect(el.model, true);
    resetSelect(el.variant, true);

    setEmpty("Use filters or search, then hit Apply.");
  }

  el.apply?.addEventListener("click", runSearch);
  el.clear?.addEventListener("click", clearAll);

  el.input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runSearch();
    }
  });

  // -----------------------------
  // Select an asset
  // -----------------------------
  function selectRow(row) {
    const id = row.dataset.assetId;
    const tag = row.dataset.assetTag || "";
    const site = row.dataset.site || "";
    const make = row.dataset.make || "";
    const model = row.dataset.model || "";
    const variant = row.dataset.variant || "";
    
    if (!id) {
      console.error("Selected row has no asset id. Check API response keys (id vs asset_id).", row.dataset);
      return;
    }
    
    if (el.assetId) el.assetId.value = id;

    const bits = [];
    if (site) bits.push(site);
    const mm = [make, model].filter(Boolean).join(" ");
    if (mm) bits.push(mm);
    if (variant) bits.push(variant);

    setHeaderText(
      `<strong>${escapeHtml(tag)}</strong>` +
      (bits.length ? ` <span class="muted"> · ${escapeHtml(bits.join(" · "))}</span>` : "")
    );

    el.panel.hidden = true;
  }

  el.results?.addEventListener("click", (e) => {
    const row = e.target.closest(".asset-picker__row");
    if (!row) return;
    selectRow(row);
  });

  el.results?.addEventListener("keydown", (e) => {
    const row = e.target.closest(".asset-picker__row");
    if (!row) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      selectRow(row);
    }
  });

  // -----------------------------
  // Init
  // -----------------------------
  (async function init() {
    // Initial state for cascade: make/model/variant disabled until category chosen
    if (el.make) el.make.disabled = true;
    if (el.model) el.model.disabled = true;
    if (el.variant) el.variant.disabled = true;

    // Ensure results box has content
    if (el.results && el.results.innerHTML.trim() === "") {
      setEmpty("Use filters or search, then hit Apply.");
    }
    await loadCategories();
    await loadAssetStatuses();

    // If category is already selected (e.g., page reload), load makes
    if (el.category?.value) {
      await loadMakesForCategory(el.category.value);
    }
    // If make is already selected, load models
    if (el.make?.value) {
      await loadModelsForMake(el.make.value);
    }
    // If model is already selected, load variants
    if (el.model?.value) {
      await loadVariantsForModel(el.model.value);
    }
  })();

})();
