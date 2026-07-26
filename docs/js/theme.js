// Wires the dark-mode toggle button. The initial theme (avoiding a flash of
// the wrong theme) is set by an inline script in <head>, before this file
// loads — this only handles the click.
function toggleTheme() {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  localStorage.setItem("optionslab-theme", next);
}
