// Apply the remembered palette before the application paints. Storage is optional.
(() => {
  let theme = "dark";
  try {
    const stored = localStorage.getItem("az-election-theme");
    if (stored === "light" || stored === "dark") theme = stored;
  } catch {
    /* Private or restricted storage must not prevent rendering. */
  }
  document.documentElement.dataset.theme = theme;
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", theme === "dark" ? "#0b0f18" : "#f3f5f9");
})();
