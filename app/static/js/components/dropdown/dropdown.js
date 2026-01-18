// dropdown.js
function closeAll(except = null) {
  document.querySelectorAll("[data-dropdown].is-open").forEach((dd) => {
    if (dd !== except) {
      dd.classList.remove("is-open");
      const b = dd.querySelector("[data-dropdown-btn]");
      if (b) b.setAttribute("aria-expanded", "false");
    }
  });
}

document.addEventListener("click", (e) => {
  const dd = e.target.closest("[data-dropdown]");
  const btn = e.target.closest("[data-dropdown-btn]");
  const item = e.target.closest(".dropdown__item");

  if (!dd) {
    closeAll();
    return;
  }

  if (dd.dataset.disabled === "1") return;

  if (btn) {
    const isOpen = dd.classList.toggle("is-open");
    btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    closeAll(dd);
    return;
  }

  if (item && !item.disabled) {
    const value = item.getAttribute("data-value") ?? "";
    const label = item.textContent.trim();

    dd.querySelector("[data-dropdown-value]").textContent = label;

    // Sync to native select in the same field wrapper
    const field = dd.closest(".field") || dd.parentElement;
    const sel = field.querySelector("select.select--native");
    if (sel) {
      sel.value = value;
      sel.dispatchEvent(new Event("change", { bubbles: true }));
    }

    dd.classList.remove("is-open");
    const ddBtn = dd.querySelector("[data-dropdown-btn]");
    if (ddBtn) ddBtn.setAttribute("aria-expanded", "false");
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeAll();
});
