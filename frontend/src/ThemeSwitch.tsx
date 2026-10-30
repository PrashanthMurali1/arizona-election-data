import { useEffect, useState } from "react";
import Icon from "./Icon";

type Theme = "light" | "dark";
const storageKey = "az-election-theme";

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", theme === "dark" ? "#0b0f18" : "#f3f5f9");
}

// Theme state belongs to this control, not the router or data-loading views.
export default function ThemeSwitch() {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === "light" ? "light" : "dark",
  );
  const [announcement, setAnnouncement] = useState("");
  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key !== storageKey) return;
      const next = event.newValue === "light" ? "light" : "dark";
      applyTheme(next);
      setTheme(next);
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);
  function choose(next: Theme) {
    applyTheme(next);
    setTheme(next);
    try {
      localStorage.setItem(storageKey, next);
    } catch {
      /* The current tab still works. */
    }
    setAnnouncement(`${next === "dark" ? "Dark" : "Light"} theme selected.`);
  }
  return (
    <>
      <div className="theme-choice" role="group" aria-label="Color theme">
        {(["light", "dark"] as const).map((value) => (
          <button
            key={value}
            type="button"
            aria-label={`${value === "light" ? "Light" : "Dark"} theme`}
            aria-pressed={theme === value}
            onClick={() => choose(value)}
          >
            <Icon name={value === "light" ? "sun" : "moon"} />
            {value === "light" ? "Light" : "Dark"}
          </button>
        ))}
      </div>
      <span className="sr-only" role="status">
        {announcement}
      </span>
    </>
  );
}
