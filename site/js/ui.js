// Shared page chrome: theme toggling and small render helpers.

const THEME_KEY = "grant-radar.theme";

export function initTheme() {
  const btn = document.getElementById("theme-toggle");
  const root = document.documentElement;
  const apply = (dark) => {
    root.classList.toggle("dark", dark);
    if (btn) btn.textContent = dark ? "☀" : "☾";
  };
  apply(root.classList.contains("dark"));
  btn?.addEventListener("click", () => {
    const dark = !root.classList.contains("dark");
    apply(dark);
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
  });
}

export function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

const MONTHS = ["January","February","March","April","May","June",
  "July","August","September","October","November","December"];

export function fmtDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1].slice(0, 3)} ${d}, ${y}`;
}

export function fmtDateLong(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}
