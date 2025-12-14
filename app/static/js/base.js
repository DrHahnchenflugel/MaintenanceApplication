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
    document.body.classList.remove("no-scroll");
    img.src = "";
  }

  // Make them available to HTML onclick=""
  window.openImgModal = openImgModal;
  window.closeImgModal = closeImgModal;

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

  // ---- Boot ----
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeImgModal();
  });

  document.addEventListener("DOMContentLoaded", () => {
    updateDateTime();
    setInterval(updateDateTime, 60000);

    initClampToggles();
  });

  // Run again after images/fonts settle (helps clamp correctness)
  window.addEventListener("load", () => {
    initClampToggles();
  });
})();
