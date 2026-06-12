const copyButtons = document.querySelectorAll("[data-copy], [data-copy-active-code]");

async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text);
    const previous = button.textContent;
    button.textContent = "Copied";
    button.classList.add("copied");
    window.setTimeout(() => {
      button.textContent = previous;
      button.classList.remove("copied");
    }, 1400);
  } catch {
    button.textContent = "Select";
  }
}

copyButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const explicit = button.getAttribute("data-copy");
    const activeCode = document.querySelector(".code-block.active code");
    const text = explicit || (activeCode ? activeCode.textContent.trim() : "");
    if (text) {
      copyText(text, button);
    }
  });
});

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".code-block");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const target = tab.getAttribute("data-tab");
    tabs.forEach((item) => item.classList.toggle("active", item === tab));
    panels.forEach((panel) => {
      panel.classList.toggle("active", panel.getAttribute("data-panel") === target);
    });
  });
});

const filters = document.querySelectorAll(".filter");
const formatCards = document.querySelectorAll(".format-card");

filters.forEach((filter) => {
  filter.addEventListener("click", () => {
    const target = filter.getAttribute("data-filter");
    filters.forEach((item) => item.classList.toggle("active", item === filter));
    formatCards.forEach((card) => {
      const show = target === "all" || card.getAttribute("data-kind") === target;
      card.toggleAttribute("hidden", !show);
    });
  });
});
