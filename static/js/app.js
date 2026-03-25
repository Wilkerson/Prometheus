// CSRF token para requisições HTMX
document.body.addEventListener("htmx:configRequest", function (event) {
  const csrfToken = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="))
    ?.split("=")[1];
  if (csrfToken) {
    event.detail.headers["X-CSRFToken"] = csrfToken;
  }
});

// Indicador de loading global
document.body.addEventListener("htmx:beforeRequest", function () {
  document.getElementById("loading-indicator")?.classList.remove("hidden");
});
document.body.addEventListener("htmx:afterRequest", function () {
  document.getElementById("loading-indicator")?.classList.add("hidden");
});
