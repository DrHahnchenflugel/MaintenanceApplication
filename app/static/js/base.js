(function () {
  // ---- Date/clock (safe on pages that don't include them) ----
  function updateDateTime() {
    const now = new Date();

    const clockEl = document.getElementById("clock");
    if (clockEl) {
      clockEl.textContent = now.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      });
    }

    const dateEl = document.getElementById("date");
    if (dateEl) {
      dateEl.textContent = now.toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
      });
    }
  }

  // ---- Image modal (expose functions for inline onclick handlers) ----
  function openImgModal(src) {
    const m = document.getElementById("imgModal");
    const img = document.getElementById("imgModalContent");
    if (!m || !img) return;

    img.src = src;
    m.classList.add("open");
    document.body.classList.add("no-scroll");
  }

  function closeImgModal() {
    const m = document.getElementById("imgModal");
    const img = document.getElementById("imgModalContent");
    if (!m || !img) return;

    m.classList.remove("open");
    img.src = "";

    // Only remove no-scroll if sidebar drawer OR text modal isn't open
    const sidebar = document.getElementById("sidebar");
    const drawerOpen = sidebar && sidebar.classList.contains("is-open");

    const textModal = document.getElementById("textModal");
    const textOpen = textModal && textModal.classList.contains("open");

    if (!drawerOpen && !textOpen) document.body.classList.remove("no-scroll");
  }

  // Make them available to HTML onclick=""
  window.openImgModal = openImgModal;
  window.closeImgModal = closeImgModal;

  // ---- Text modal (generic) ----
  function openTextModal(title, text) {
    const modal = document.getElementById("textModal");
    const t = document.getElementById("textModalTitle");
    const b = document.getElementById("textModalBody");
    if (!modal || !t || !b) return;

    t.textContent = title || "Details";

    // Safe text -> preserve line breaks
    const safe = (text || "").toString();
    b.innerHTML = safe.replace(/&/g, "&amp;")
                      .replace(/</g, "&lt;")
                      .replace(/>/g, "&gt;")
                      .replace(/"/g, "&quot;")
                      .replace(/'/g, "&#039;")
                      .replace(/\n/g, "<br>");

    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("no-scroll");
  }

  function closeTextModal() {
    const modal = document.getElementById("textModal");
    const b = document.getElementById("textModalBody");
    if (!modal || !b) return;

    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    b.innerHTML = "";

    // Only remove no-scroll if sidebar drawer OR image modal isn't open
    const sidebar = document.getElementById("sidebar");
    const drawerOpen = sidebar && sidebar.classList.contains("is-open");

    const imgModal = document.getElementById("imgModal");
    const imgOpen = imgModal && imgModal.classList.contains("open");

    if (!drawerOpen && !imgOpen) document.body.classList.remove("no-scroll");
  }

  // Helper: read full text from a hidden element by id
  function openTextModalFromEl(elId, title) {
    const el = document.getElementById(elId);
    if (!el) return;

    const modal = document.getElementById("textModal");
    const t = document.getElementById("textModalTitle");
    const b = document.getElementById("textModalBody");
    if (!modal || !t || !b) return;

    t.textContent = title || "Details";

    // IMPORTANT: render HTML, not text
    b.innerHTML = el.innerHTML;

    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("no-scroll");
  }
  
  window.openTextModal = openTextModal;
  window.closeTextModal = closeTextModal;
  window.openTextModalFromEl = openTextModalFromEl;

  // ---- Clamp toggles ----
  function initClampToggles() {
    document.querySelectorAll('[data-clamp="true"]').forEach((el) => {
      const btn = el.parentElement?.querySelector(".clamp-btn");
      if (!btn) return;

      // show/hide button depending on overflow
      const needsClamp = el.scrollHeight > el.clientHeight + 2;
      btn.hidden = !needsClamp;

      // avoid double-binding if init runs twice
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";

      btn.addEventListener("click", () => {
        const open = el.classList.toggle("is-open");
        btn.textContent = open ? "Show less" : "Show more";
      });
    });
  }

  // ---- Sidebar drawer (tablet/phone) ----
  function initSidebarDrawer() {
    const sidebar = document.getElementById("sidebar");
    const scrim = document.getElementById("sidebarScrim");
    const btn = document.getElementById("navToggle");
    if (!sidebar || !scrim || !btn) return;

    function openNav() {
      sidebar.classList.add("is-open");
      scrim.hidden = false;
      document.body.classList.add("no-scroll");
    }

    function closeNav() {
      sidebar.classList.remove("is-open");
      scrim.hidden = true;

      // Only remove no-scroll if image modal AND text modal aren't open
      const imgModal = document.getElementById("imgModal");
      const imgOpen = imgModal && imgModal.classList.contains("open");

      const textModal = document.getElementById("textModal");
      const textOpen = textModal && textModal.classList.contains("open");

      if (!imgOpen && !textOpen) document.body.classList.remove("no-scroll");
    }

    btn.addEventListener("click", openNav);
    scrim.addEventListener("click", closeNav);
  }

  // ---- Escape key: close top-most overlay ----
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;

    // Close text modal first if open (top-most)
    const textModal = document.getElementById("textModal");
    if (textModal && textModal.classList.contains("open")) {
      closeTextModal();
      return;
    }

    // Then close image modal if open
    const imgModal = document.getElementById("imgModal");
    if (imgModal && imgModal.classList.contains("open")) {
      closeImgModal();
      return;
    }

    // Otherwise close sidebar if open
    const sidebar = document.getElementById("sidebar");
    const scrim = document.getElementById("sidebarScrim");
    if (sidebar && sidebar.classList.contains("is-open")) {
      sidebar.classList.remove("is-open");
      if (scrim) scrim.hidden = true;
      document.body.classList.remove("no-scroll");
    }
  });

  // ---- Boot ----
  document.addEventListener("DOMContentLoaded", () => {
    updateDateTime();
    setInterval(updateDateTime, 60000);

    initClampToggles();
    initSidebarDrawer();
  });

  // Run again after images/fonts settle (helps clamp correctness)
  window.addEventListener("load", () => {
    initClampToggles();
  });
})();
