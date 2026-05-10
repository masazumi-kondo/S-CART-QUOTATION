(function () {
  function num(v) {
    if (v == null) return 0;
    const s = String(v).replace(/,/g, "").trim();
    if (s === "") return 0;
    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
  }

  function fmt(n) {
    return Math.round(Number(n || 0)).toLocaleString();
  }

  function pct(n) {
    if (!Number.isFinite(n)) return "-";
    return `${Math.round(n * 10) / 10}%`;
  }

  function getTotals() {
    const t = window.QUOTE_TOTALS || window.LAST_PROFIT_TOTALS;
    if (t && (Number(t.sellBeforeDiscount) > 0 || Number(t.costTotal) > 0)) {
      return {
        sellBeforeDiscount: Number(t.sellBeforeDiscount || 0),
        costTotal: Number(t.costTotal || 0)
      };
    }
    return { sellBeforeDiscount: 0, costTotal: 0 };
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function updateDiscountRatePreview() {
    const totals = getTotals();
    const sellBefore = Number(totals.sellBeforeDiscount || 0);
    const amount = num(document.getElementById("discount_amount")?.value);

    const rate = sellBefore > 0 && amount > 0
      ? (amount / sellBefore) * 100
      : 0;

    const rateText = `${Math.round(rate * 10) / 10}%`;

    const preview = document.getElementById("discount_rate_preview");
    if (preview) preview.textContent = rateText;

    const rateInput = document.getElementById("discount_rate");
    if (rateInput) rateInput.value = Math.round(rate * 10) / 10;
  }

  window.updateTotalProfitPreview = function updateTotalProfitPreview(options = {}) {
    const applyDiscount = options.applyDiscount === true;
    const totals = getTotals();

    const sellBefore = totals.sellBeforeDiscount;
    const costTotal = totals.costTotal;

    let discount = 0;
    if (applyDiscount) {
      const amountEl = document.getElementById("discount_amount");
      const rateEl = document.getElementById("discount_rate");
      const amount = num(amountEl?.value);
      const rate = num(rateEl?.value);
      
      if (amount > 0) {
        discount = amount;
        if (rateEl && sellBefore > 0) {
          rateEl.value = Math.round((amount / sellBefore) * 1000) / 10;
        }
      } else if (rate > 0) {
        discount = Math.round(sellBefore * rate / 100);
        if (amountEl) amountEl.value = String(discount);
      }
    }

    const sellAfter = Math.max(0, sellBefore - discount);

    const rateBefore = sellBefore > 0 ? ((sellBefore - costTotal) / sellBefore) * 100 : NaN;
    const rateAfter = sellAfter > 0 ? ((sellAfter - costTotal) / sellAfter) * 100 : NaN;

    setText("sum_sell_before_discount", fmt(sellBefore));
    setText("sum_cost_total", fmt(costTotal));
    setText("sum_profit_rate_before_discount", pct(rateBefore));

    setText("sum_sell_after_discount", fmt(sellAfter));
    setText("sum_cost_total_after_discount", fmt(costTotal));
    setText("sum_profit_rate_after_discount", pct(rateAfter));

    window.LAST_PROFIT_TOTALS = {
      sellBeforeDiscount: sellBefore,
      costTotal: costTotal
    };
  };

  document.addEventListener("DOMContentLoaded", () => {
    const btn =
      document.getElementById("discount_apply_btn") ||
      document.getElementById("apply_discount_btn") ||
      document.querySelector('button[data-action="apply-discount"]') ||
      Array.from(document.querySelectorAll("button")).find(b => b.textContent.trim() === "反映");

    if (btn && !btn.__discountApplyBound) {
      btn.__discountApplyBound = true;
      btn.addEventListener("click", () => {
        updateDiscountRatePreview();
        window.updateTotalProfitPreview({ applyDiscount: true });
      });
    }

    const amountEl = document.getElementById("discount_amount");
    if (amountEl && !amountEl.__discountRatePreviewBound) {
      amountEl.__discountRatePreviewBound = true;
      amountEl.addEventListener("input", () => {
        updateDiscountRatePreview();
      });
    }
  });

  document.addEventListener("profit_preview:update", () => {
    window.updateTotalProfitPreview({ applyDiscount: false });
  });
})();
