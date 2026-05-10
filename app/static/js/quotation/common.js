// ==============================
// common.js
// ==============================

// safeParseFloat
if (typeof window.safeParseFloat !== "function") {
  window.safeParseFloat = function safeParseFloat(v) {
    if (v == null) return 0;
    const s = String(v).replace(/,/g, "").trim();
    if (s === "") return 0;
    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
  };
}

// debounce helper
window._debounce = function _debounce(fn, waitMs) {
  let t = null;
  return function (...args) {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), waitMs);
  };
};

// format helpers
window._fmtInt = function (n) {
  if (!Number.isFinite(n)) return "-";
  return Math.round(n).toLocaleString();
};

window._fmt1 = function (n) {
  if (!Number.isFinite(n)) return "-";
  return Number(n).toFixed(1);
};
