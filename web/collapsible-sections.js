(() => {
  const sections = [
    {
      toggleId: "new-opportunities-toggle",
      contentId: "new-opportunities-content",
      arrowId: "new-opportunities-arrow",
      defaultExpanded: true,
    },
    {
      toggleId: "active-toggle",
      contentId: "active-content",
      arrowId: "active-arrow",
      defaultExpanded: true,
    },
    {
      toggleId: "expired-toggle",
      contentId: "expired-content",
      arrowId: "expired-arrow",
      defaultExpanded: false,
    },
  ];

  function setExpanded(section, expanded) {
    const toggle = document.getElementById(section.toggleId);
    const content = document.getElementById(section.contentId);
    const arrow = document.getElementById(section.arrowId);
    if (!toggle || !content) return;

    toggle.setAttribute("aria-expanded", String(expanded));
    content.classList.toggle("hidden", !expanded);
    if (arrow) arrow.textContent = expanded ? "⌃" : "⌄";
  }

  function bind(section) {
    const toggle = document.getElementById(section.toggleId);
    if (!toggle || toggle.dataset.collapsibleBound === "true") return;

    toggle.dataset.collapsibleBound = "true";
    setExpanded(
      section,
      toggle.getAttribute("aria-expanded") === "true"
        ? true
        : section.defaultExpanded,
    );

    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      setExpanded(section, !expanded);
    });
  }

  const bindAll = () => sections.forEach(bind);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindAll, { once: true });
  } else {
    bindAll();
  }
})();
