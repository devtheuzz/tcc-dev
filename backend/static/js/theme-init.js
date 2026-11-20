// Executado antes do CSS para restaurar o tema sem piscar a tela clara.
(() => {
  let theme = 'dia';
  try {
    if (localStorage.getItem('nexa-play-theme') === 'noite') theme = 'noite';
  } catch { /* O tema claro continua disponível sem armazenamento. */ }
  document.documentElement.dataset.theme = theme;
})();
