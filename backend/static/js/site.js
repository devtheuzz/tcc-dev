(() => {
  const themeKey = "nexa-play-theme";
  const showToast = (message) => {
    const toast = document.querySelector("#toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("is-visible");
    window.clearTimeout(showToast.timeout);
    showToast.timeout = window.setTimeout(() => toast.classList.remove("is-visible"), 3200);
  };
  const updateThemeControls = () => {
    const dark = document.documentElement.dataset.theme === 'noite';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#181716' : '#f8f3e7');
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      const label = dark ? 'Ativar modo claro' : 'Ativar modo escuro';
      button.setAttribute('aria-pressed', String(dark));
      button.setAttribute('aria-label', label);
      const text = button.querySelector('[data-theme-label]');
      if (text) text.textContent = label;
    });
  };
  updateThemeControls();
  document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const nextTheme = document.documentElement.dataset.theme === 'noite' ? 'dia' : 'noite';
      document.documentElement.dataset.theme = nextTheme;
      try { localStorage.setItem(themeKey, nextTheme); } catch { /* Preferência apenas nesta página. */ }
      updateThemeControls();
      showToast(nextTheme === 'noite' ? 'Modo escuro ativado.' : 'Modo claro ativado.');
    });
  });
  window.addEventListener('storage', (event) => {
    if (event.key === themeKey) {
      document.documentElement.dataset.theme = event.newValue === 'noite' ? 'noite' : 'dia';
      updateThemeControls();
    }
  });
  document.querySelectorAll("[data-nav]").forEach((link) => {
    if (link.dataset.nav === document.body.dataset.page) link.setAttribute("aria-current", "page");
  });
  const menuButton = document.querySelector(".menu-toggle");
  const mobileMenu = document.querySelector("#mobile-nav");
  if (menuButton && mobileMenu) {
    menuButton.addEventListener("click", () => {
      const isOpen = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!isOpen));
      menuButton.setAttribute("aria-label", isOpen ? "Abrir menu" : "Fechar menu");
      mobileMenu.hidden = isOpen;
    });
  }
  document.querySelectorAll('form[method="post"]').forEach((form) => {
    form.addEventListener("submit", () => {
      form.querySelectorAll('button[type="submit"]').forEach((button) => {
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
      });
    });
  });
  window.addEventListener("pageshow", () => {
    document.querySelectorAll('button[aria-busy="true"]').forEach((button) => {
      button.disabled = false;
      button.removeAttribute("aria-busy");
    });
  });
})();
