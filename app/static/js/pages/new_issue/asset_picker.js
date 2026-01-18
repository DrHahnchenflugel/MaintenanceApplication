(function(){
  const btn = document.getElementById('toggleAssetPicker');
  const panel = document.getElementById('assetPicker');
  if (!btn || !panel) return;

  const searchUrl = panel.dataset.searchUrl;

  const el = {
    input: document.getElementById('assetSearch'),
    results: document.getElementById('apResults'),
    apply: document.getElementById('apApply'),
    clear: document.getElementById('apClear'),

    site: document.getElementById('apSite'),
    status: document.getElementById('apStatus'),
    category: document.getElementById('apCategory'),
    make: document.getElementById('apMake'),
    model: document.getElementById('apModel'),
    variant: document.getElementById('apVariant'),

    assetId: document.getElementById('assetId'),
  };

  // Where to write the selected asset summary (reuse your existing area)
  const headerTag = document.querySelector('.new-issue-asset__tag');
  const headerFallback = document.querySelector('.new-issue-asset__title .muted');

  function setHeaderText(textHtml){
    if (headerTag) headerTag.innerHTML = textHtml;
    else if (headerFallback) headerFallback.innerHTML = textHtml;
  }

  btn.addEventListener('click', () => {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) el.input?.focus();
  });

  function qsParams(){
    const p = new URLSearchParams();
    const q = (el.input?.value || '').trim();

    if (q) p.set('q', q);
    if (el.site?.value) p.set('site_id', el.site.value);
    if (el.status?.value) p.set('status', el.status.value);
    if (el.category?.value) p.set('category_id', el.category.value);
    if (el.make?.value) p.set('make_id', el.make.value);
    if (el.model?.value) p.set('model_id', el.model.value);
    if (el.variant?.value) p.set('variant_id', el.variant.value);

    return p;
  }

  function renderResults(items){
    if (!items || items.length === 0){
      el.results.innerHTML = '<div class="asset-picker__empty muted">No matching assets.</div>';
      return;
    }

    const rows = items.map(a => {
      const tag = escapeHtml(a.asset_tag || '');
      const site = escapeHtml(a.site_shorthand || '');
      const make = escapeHtml(a.make || '');
      const model = escapeHtml(a.model || '');
      const variant = escapeHtml(a.variant || '');
      const status = escapeHtml(a.status_label || a.status_code || '');

      const meta = [site, [make, model].filter(Boolean).join(' '), variant].filter(Boolean).join(' · ');

      return `
        <div class="asset-picker__row" role="button" tabindex="0"
             data-asset-id="${a.id}"
             data-asset-tag="${tag}"
             data-site="${site}"
             data-make="${make}"
             data-model="${model}"
             data-variant="${variant}">
          <div class="asset-picker__tag">${tag}</div>
          <div class="asset-picker__meta">${meta || '&nbsp;'}</div>
          <div class="asset-picker__meta">${escapeHtml(a.serial_num || '')}</div>
          <div class="asset-picker__pill">${status}</div>
        </div>
      `;
    }).join('');

    el.results.innerHTML = `<div class="asset-picker__list">${rows}</div>`;
  }

  async function runSearch(){
    if (!searchUrl){
      el.results.innerHTML = '<div class="asset-picker__empty muted">Missing data-search-url on asset picker.</div>';
      return;
    }

    el.results.innerHTML = '<div class="asset-picker__empty muted">Searching…</div>';

    const url = `${searchUrl}?${qsParams().toString()}`;

    try{
      const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Expect: { items: [...] } OR just [...]
      const items = Array.isArray(data) ? data : (data.items || []);
      renderResults(items);
    } catch (e){
      el.results.innerHTML = '<div class="asset-picker__empty muted">Search failed. Check endpoint / auth / console.</div>';
      console.error(e);
    }
  }

  function clearFilters(){
    el.input.value = '';
    el.site.value = '';
    el.status.value = '';
    el.category.value = '';
    el.make.value = '';
    el.model.innerHTML = '<option value="">All</option>';
    el.model.disabled = true;
    el.variant.innerHTML = '<option value="">All</option>';
    el.variant.disabled = true;
    el.results.innerHTML = '<div class="asset-picker__empty muted">Use filters or search, then hit Apply.</div>';
  }

  // Apply/Clear buttons
  el.apply?.addEventListener('click', runSearch);
  el.clear?.addEventListener('click', clearFilters);

  // Optional: hit Enter in search to apply
  el.input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter'){
      e.preventDefault();
      runSearch();
    }
  });

  // Optional: debounce while typing (uncomment if you want “live” search)
  let t = null;
  el.input?.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => {
      // runSearch(); // enable if you want auto-search while typing
    }, 250);
  });

  // Click-to-select
  el.results.addEventListener('click', (e) => {
    const row = e.target.closest('.asset-picker__row');
    if (!row) return;

    const id = row.dataset.assetId;
    const tag = row.dataset.assetTag || '';
    const site = row.dataset.site || '';
    const make = row.dataset.make || '';
    const model = row.dataset.model || '';
    const variant = row.dataset.variant || '';

    el.assetId.value = id;

    const bits = [];
    if (site) bits.push(site);
    const mm = [make, model].filter(Boolean).join(' ');
    if (mm) bits.push(mm);
    if (variant) bits.push(variant);

    setHeaderText(`<strong>${escapeHtml(tag)}</strong> <span class="muted">${bits.length ? ' · ' + escapeHtml(bits.join(' · ')) : ''}</span>`);

    panel.hidden = true;
  });

  // Basic cascading dropdown behavior placeholders
  // Wire these to endpoints later; for now it just enables/disables.
  el.make?.addEventListener('change', () => {
    el.model.disabled = !el.make.value;
    el.variant.disabled = true;
    el.variant.innerHTML = '<option value="">All</option>';
  });

  el.model?.addEventListener('change', () => {
    el.variant.disabled = !el.model.value;
  });

  function escapeHtml(s){
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
    }[c]));
  }
})();
