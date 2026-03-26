// ========== TEMA CLARO/ESCURO ==========
// Aplica tema ANTES de qualquer renderizacao (evita flash)
(function() {
  const saved = localStorage.getItem('theme');
  if (saved === 'light') {
    document.documentElement.classList.add('light');
    document.documentElement.classList.remove('dark');
  } else {
    document.documentElement.classList.add('dark');
    document.documentElement.classList.remove('light');
  }
})();

// ========== CSRF para HTMX ==========
document.body.addEventListener("htmx:configRequest", function (event) {
  const csrfToken = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
  if (csrfToken) {
    event.detail.headers["X-CSRFToken"] = csrfToken;
  }
});

// ========== LOADING INDICATOR ==========
document.body.addEventListener("htmx:beforeRequest", function () {
  document.getElementById("loading-indicator")?.classList.remove("hidden");
});
document.body.addEventListener("htmx:afterRequest", function () {
  document.getElementById("loading-indicator")?.classList.add("hidden");
});
