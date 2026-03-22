// dropdown.js
(function () {
  function getField(dropdown) {
    return dropdown.closest(".field") || dropdown.parentElement;
  }

  function getNativeSelect(dropdown) {
    const field = getField(dropdown);
    return field ? field.querySelector("select.select--native") : null;
  }

  function getButton(dropdown) {
    return dropdown.querySelector("[data-dropdown-btn]");
  }

  function getValueEl(dropdown) {
    return dropdown.querySelector("[data-dropdown-value]");
  }

  function getPlaceholder(dropdown) {
    return dropdown.dataset.dropdownPlaceholder || "Select...";
  }

  function getSelectedOption(select) {
    if (!select) return null;
    return select.options[select.selectedIndex] || null;
  }

  function syncDropdownFromSelect(dropdown) {
    const select = getNativeSelect(dropdown);
    const valueEl = getValueEl(dropdown);
    if (!select || !valueEl) return;

    const selectedOption = getSelectedOption(select);
    const label = selectedOption ? selectedOption.textContent.trim() : getPlaceholder(dropdown);
    valueEl.textContent = label || getPlaceholder(dropdown);

    dropdown.querySelectorAll(".dropdown__item").forEach((item) => {
      const isSelected = item.getAttribute("data-value") === (select.value ?? "");
      if (isSelected) {
        item.setAttribute("data-selected", "1");
      } else {
        item.removeAttribute("data-selected");
      }
      item.setAttribute("aria-selected", isSelected ? "true" : "false");
    });
  }

  function closeDropdown(dropdown) {
    if (!dropdown) return;
    dropdown.classList.remove("is-open");
    const button = getButton(dropdown);
    if (button) button.setAttribute("aria-expanded", "false");
  }

  function closeAll(except = null) {
    document.querySelectorAll("[data-dropdown].is-open").forEach((dropdown) => {
      if (dropdown !== except) closeDropdown(dropdown);
    });
  }

  function openDropdown(dropdown) {
    if (!dropdown || dropdown.dataset.disabled === "1") return;
    closeAll(dropdown);
    dropdown.classList.add("is-open");
    const button = getButton(dropdown);
    if (button) button.setAttribute("aria-expanded", "true");
  }

  function toggleDropdown(dropdown) {
    if (!dropdown || dropdown.dataset.disabled === "1") return;
    if (dropdown.classList.contains("is-open")) {
      closeDropdown(dropdown);
    } else {
      openDropdown(dropdown);
    }
  }

  function selectDropdownValue(dropdown, value) {
    const select = getNativeSelect(dropdown);
    if (!select) return;

    const nextValue = value ?? "";
    if (select.value === nextValue) {
      syncDropdownFromSelect(dropdown);
      closeDropdown(dropdown);
      return;
    }

    select.value = nextValue;
    syncDropdownFromSelect(dropdown);
    select.dispatchEvent(new Event("change", { bubbles: true }));
    closeDropdown(dropdown);
  }

  function initDropdowns(root = document) {
    root.querySelectorAll("[data-dropdown]").forEach((dropdown) => {
      syncDropdownFromSelect(dropdown);
      closeDropdown(dropdown);
    });
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-dropdown-btn]");
    if (button) {
      const dropdown = button.closest("[data-dropdown]");
      toggleDropdown(dropdown);
      return;
    }

    const item = event.target.closest(".dropdown__item");
    if (item) {
      const dropdown = item.closest("[data-dropdown]");
      if (!dropdown || item.disabled || dropdown.dataset.disabled === "1") return;
      selectDropdownValue(dropdown, item.getAttribute("data-value"));
      return;
    }

    if (!event.target.closest("[data-dropdown]")) {
      closeAll();
    }
  });

  document.addEventListener("change", (event) => {
    const select = event.target.closest("select.select--native");
    if (!select) return;

    const field = select.closest(".field") || select.parentElement;
    const dropdown = field ? field.querySelector("[data-dropdown]") : null;
    if (dropdown) syncDropdownFromSelect(dropdown);
  });

  document.addEventListener("dropdown:sync", (event) => {
    const select = event.target.closest("select.select--native");
    if (!select) return;

    const field = select.closest(".field") || select.parentElement;
    const dropdown = field ? field.querySelector("[data-dropdown]") : null;
    if (dropdown) syncDropdownFromSelect(dropdown);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAll();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => initDropdowns());
  } else {
    initDropdowns();
  }
})();
