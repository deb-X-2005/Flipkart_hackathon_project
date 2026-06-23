export type Theme = "dark" | "light";

const KEY = "theme";

export function getTheme(): Theme {
  const saved = localStorage.getItem(KEY) as Theme | null;
  if (saved === "dark" || saved === "light") return saved;
  const preferLight = typeof window !== "undefined"
    && window.matchMedia?.("(prefers-color-scheme: light)").matches;
  return preferLight ? "light" : "dark";
}

export function setTheme(t: Theme) {
  document.documentElement.dataset.theme = t;
  localStorage.setItem(KEY, t);
}

export function applyInitialTheme() {
  setTheme(getTheme());
}
