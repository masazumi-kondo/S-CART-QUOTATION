// profit_summary.js: Handles profit-summary-section update (値引き前/後 UI)
// 依存: details_table.js で grand_total_sell, grand_total_cost を出力していること
(function () {
  // Utility: parse float, fallback 0
  function parseNum(v) {
    if (v == null) return 0;
    if (typeof v === 'number') return v;
    var s = String(v).replace(/,/g, '').trim();
    if (!s) return 0;
    var n = Number(s);
    return Number.isFinite(n) ? n : 0;
  }

  // DOM helpers
  function setText(id, v) {
    var el = document.getElementById(id);
    if (el) el.textContent = v;
  }
  function setValue(id, v) {
    var el = document.getElementById(id);
    if (el) el.value = v;
  }

  // lastEdited: 'amount' or 'rate'
  var lastEdited = null;

  // Main update function
  function updateProfitSummary() {
    // 1. 値引き前合計取得
    var sellPre = parseNum(document.getElementById('grand_total_sell')?.textContent || document.getElementById('grand_total_sell')?.value || 0);
    var cost = parseNum(document.getElementById('grand_total_cost')?.textContent || document.getElementById('grand_total_cost')?.value || 0);
    // fallback: 0
    // 2. 値引き入力取得
    var discountAmount = parseNum(document.getElementById('discount_amount')?.value || 0);
    var discountRate = parseNum(document.getElementById('discount_rate')?.value || 0);

    // 3. lastEdited方式で相互反映
    if (lastEdited === 'amount') {
      // 値引き率 = (値引き額/売価合計)*100
      var rate = sellPre > 0 ? (discountAmount / sellPre) * 100 : 0;
      setValue('discount_rate', rate.toFixed(1));
    } else if (lastEdited === 'rate') {
      // 値引き額 = (売価合計*値引き率/100)
      var amt = Math.floor(sellPre * discountRate / 100);
      setValue('discount_amount', amt);
      discountAmount = amt; // for below
    }

    // 4. 値引き前利益率
    var profitPre = sellPre > 0 ? ((sellPre - cost) / sellPre) * 100 : null;
    setText('sum_sell_before_discount', sellPre.toLocaleString());
    setText('sum_cost_total', cost.toLocaleString());
    setText('sum_profit_rate_before_discount', profitPre !== null ? profitPre.toFixed(1) + '%' : '-');

    // 5. 値引き後計算
    var sellFinal = Math.max(0, sellPre - discountAmount);
    var profitFinal = sellFinal > 0 ? ((sellFinal - cost) / sellFinal) * 100 : null;
    setText('sum_sell_after_discount', sellFinal.toLocaleString());
    setText('sum_cost_total_after_discount', cost.toLocaleString());
    setText('sum_profit_rate_after_discount', profitFinal !== null ? profitFinal.toFixed(1) + '%' : '-');

    // 6. 旧IDもあれば同時更新
    setText('grand_total_sell_pre', sellPre.toLocaleString());
    setText('grand_total_cost', cost.toLocaleString());
    setText('profit_rate_pre', profitPre !== null ? profitPre.toFixed(1) + '%' : '-');
    setText('grand_total_sell_final', sellFinal.toLocaleString());
    setText('grand_total_cost_final', cost.toLocaleString());
    setText('profit_rate_final', profitFinal !== null ? profitFinal.toFixed(1) + '%' : '-');
  }

  // イベント購読
  document.addEventListener('profit_preview:update', updateProfitSummary);
  window.updateProfitSummary = updateProfitSummary;

})();
