/* static/js/pages/new_issue/asset_picker.js
   Asset picker for New Issue page

   Expects these elements in the DOM:
   - button#toggleAssetPicker
   - div#assetPicker (optionally: data-assets-url="/api/v2/assets")
   - input#assetSearch
   - div#apResults
   - button#apApply
   - button#apClear
   - select#apSite (optional)
   - select#apStatus
   - select#apCategory (optional)
   - select#apMake (optional)
   - select#apModel (optional)
   - select#apVariant (optional)
   - input#assetId (hidden)
*/

(function () {
  const panel = document.getElementById("assetPicker");
  const toggleBtn = document.getElementById("toggleAssetPicker");

  // If this page doesn't have the picker, bail out safely.
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

  // Optional: where to display selected asset summary
  const headerTag = document.querySelector(".new-issue-asset__tag");
  const headerFallback = document.querySelector(".new-issue-asset__title .muted");

  // Endpoint defaults
  const ASSETS_URL = panel.dataset.assetsUrl || "/api/v2/assets";
  const STATUSES_URL = panel.dataset.assetStatusesUrl || "/api/v2/asset-statuses";

  // Cache for status labels (if assets don’t include expanded status fields)
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

  function setLoading(msg = "Searching…") {
    if (!el.results) return;
    el.results.innerHTML = `<div class="asset-picker__empty muted">${escapeHtml(msg)}</div>`;
  }

  // -----------------------------
  // Toggle open/close
  // -----------------------------
  el.toggleBtn.addEventListener("click", () => {
    el.panel.hidden = !el.panel.hidden;
    if (!el.panel.hidden) {
      // Move focus to search input
      if (el.input) el.input.focus();
    }
  });

  // -----------------------------
  // Populate asset statuses (UUID values)
  // -----------------------------
  async function loadAssetStatuses() {
    if (!el.status) return;

    // If options already exist server-side, we can still build the map,
    // but we won't overwrite your HTML.
    const alreadyHasOptions = el.status.options && el.status.options.length > 1;

    try {
      const res = await fetch(STATUSES_URL, { headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const statuses = await res.json(); // expects [{id, code, label, display_order}, ...]

      // Build map
      statuses.forEach((s) => statusLabelById.set(String(s.id), String(s.label)));

      // If you’re rendering server-side, don’t overwrite.
      if (alreadyHasOptions) return;

      const opts = statuses
        .slice()
        .sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0))
        .map((s) => `<option value="${escapeHtml(s.id)}">${escapeHtml(s.label)}</option>`)
        .join("");

      el.status.innerHTML = `<option value="">All</option>${opts}`;
    } catch (e) {
      // Not fatal. Picker still works.
      console.error("Failed to load asset statuses:", e);
    }
  }

  // -----------------------------
  // Cascading enable/disable for Model/Variant (simple UX)
  // You can later wire real model/variant lookups.
  // -----------------------------
  function resetSelect(selectEl) {
    if (!selectEl) return;
    selectEl.innerHTML = `<option value="">All</option>`;
    selectEl.value = "";
  }

  function setDisabled(selectEl, disabled) {
    if (!selectEl) return;
    selectEl.disabled = !!disabled;
    if (disabled) selectEl.value = "";
  }

  if (el.make) {
    el.make.addEventListener("change", () => {
      // In your schema: model depends on make
      resetSelect(el.model);
      resetSelect(el.variant);
      setDisabled(el.model, !el.make.value);
      setDisabled(el.variant, true);
    });
  }

  if (el.model) {
    el.model.addEventListener("change", () => {
      // variant depends on model
      resetSelect(el.variant);
      setDisabled(el.variant, !el.model.value);
    });
  }

  // -----------------------------
  // Build query params for /api/v2/assets
  // -----------------------------
  function buildParams() {
    const p = new URLSearchParams();

    // UUID FKs
    if (el.site?.value) p.set("site_id", el.site.value);
    if (el.category?.value) p.set("category_id", el.category.value);
    if (el.status?.value) p.set("status_id", el.status.value);
    if (el.make?.value) p.set("make_id", el.make.value);
    if (el.model?.value) p.set("model_id", el.model.value);
    if (el.variant?.value) p.set("variant_id", el.variant.value);

    // String search: your API supports asset_tag
    const tag = (el.input?.value || "").trim();
    if (tag) p.set("asset_tag", tag);

    // Reasonable defaults for picker
    p.set("page", "1");
    p.set("page_size", "25");
    p.set("retired", "active");

    // Ask for extra fields if your service layer supports include expansions
    // If your backend ignores unknown includes, fine.
    p.set("include", "site,make,model,variant,status");

    // Optional: sort
    p.set("sort", "asset_tag");

    return p;
  }

  // -----------------------------
  // Render results
  // -----------------------------
  function deriveStatusLabel(asset) {
    // Prefer expanded fields if present
    if (asset.status_label) return String(asset.status_label);
    if (asset.status_code) return String(asset.status_code);

    // Fall back to lookup mapping by status_id
    const sid = asset.status_id ? String(asset.status_id) : "";
    if (sid && statusLabelById.has(sid)) return statusLabelById.get(sid);

    return "";
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
      const id = escapeHtml(a.id);
      const tag = escapeHtml(a.asset_tag || "");
      const serial = escapeHtml(a.serial_num || "");
      const site = escapeHtml(deriveSite(a));
      const make = escapeHtml(deriveMake(a));
      const model = escapeHtml(deriveModel(a));
      const variant = escapeHtml(deriveVariant(a));
      const status = escapeHtml(deriveStatusLabel(a));

      const line1 = [site, [make, model].filter(Boolean).join(" "), variant].filter(Boolean).join(" · ");

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
  // Search
  // -----------------------------
  async function runSearch() {
    setLoading();

    const url = `${ASSETS_URL}?${buildParams().toString()}`;

    try {
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const items = Array.isArray(data) ? data : (data.items || []);
      renderResults(items);
    } catch (e) {
      console.error("Asset search failed:", e);
      setEmpty("Search failed. Check console + endpoint.");
    }
  }

  function clearFilters() {
    if (el.input) el.input.value = "";
    if (el.site) el.site.value = "";
    if (el.status) el.status.value = "";
    if (el.category) el.category.value = "";
    if (el.make) el.make.value = "";

    // Don’t destroy server-provided options; just reset values + disable cascade
    if (el.model) {
      el.model.value = "";
      el.model.disabled = true;
    }
    if (el.variant) {
      el.variant.value = "";
      el.variant.disabled = true;
    }

    setEmpty("Use filters or search, then hit Apply.");
  }

  // Buttons
  el.apply?.addEventListener("click", runSearch);
  el.clear?.addEventListener("click", clearFilters);

  // Enter in search triggers apply
  el.input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runSearch();
    }
  });

  // Optional live-search (disabled by default; enable if you want it)
  let debounceTimer = null;
  const LIVE_SEARCH = false;

  el.input?.addEventListener("input", () => {
    if (!LIVE_SEARCH) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runSearch, 250);
  });

  // If dropdowns change, optionally live-search
  [el.site, el.status, el.category, el.make, el.model, el.variant].forEach((sel) => {
    if (!sel) return;
    sel.addEventListener("change", () => {
      if (LIVE_SEARCH) runSearch();
    });
  });

  // -----------------------------
  // Select asset from results
  // -----------------------------
  function selectRow(row) {
    const id = row.dataset.assetId;
    const tag = row.dataset.assetTag || "";
    const site = row.dataset.site || "";
    const make = row.dataset.make || "";
    const model = row.dataset.model || "";
    const variant = row.dataset.variant || "";

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

    // Close picker after selection
    el.panel.hidden = true;
  }

  el.results?.addEventListener("click", (e) => {
    const row = e.target.closest(".asset-picker__row");
    if (!row) return;
    selectRow(row);
  });

  // Keyboard select (Enter/Space)
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
    // Initial empty state
    if (el.results && el.results.innerHTML.trim() === "") {
      setEmpty("Use filters or search, then hit Apply.");
    }

    // Populate statuses if needed + build label map
    await loadAssetStatuses();

    // If an asset is already selected (editing / coming from asset page),
    // you can optionally auto-close, nothing to do here.
  })();

})();
