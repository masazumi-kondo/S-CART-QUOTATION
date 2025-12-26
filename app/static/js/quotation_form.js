// ========== Jinja埋め込みJSON読込 & グローバル変数セット ==========
// 1. 先にグローバル変数を安全なデフォルトで初期化
window.products = window.products || [];
window.CUSTOMERS_META = window.CUSTOMERS_META || {};
window.CUSTOMERS = window.CUSTOMERS || [];
window.INITIAL_VALUES = window.INITIAL_VALUES || null;
window.INITIAL_DETAILS = window.INITIAL_DETAILS || null;

(function() {
  function init() {
    if (window.__quotationFormInited) return;
    window.__quotationFormInited = true;
    // JSONデータをDOMから取得してparse
    const readJson = (id, fallback) => {
      const el = document.getElementById(id);
      if (!el) return fallback;
      try { return JSON.parse(el.textContent || ""); } catch { return fallback; }
    };
    window.products = readJson("products-json", []);
    window.CUSTOMERS_META = readJson("customers-meta-json", {});
    window.CUSTOMERS = readJson("customers-json", []);
    window.INITIAL_VALUES = readJson("initial-values-json", null);
    window.INITIAL_DETAILS = readJson("initial-details-json", null);
    console.log("products JSON:", window.products);

    // submit debug
    document.addEventListener("submit", (e) => {
      const f = e.target;
      if (f && f.tagName === "FORM") {
        console.log("[DEBUG submit] action=", f.action, "method=", f.method);
      }
    }, true);

    // --- 顧客選択UI ---
    const customers = window.CUSTOMERS || [];
    const customerSearch = document.getElementById('customer_search');
    const customerCandidates = document.getElementById('customer_candidates');
    const customerIdInput = document.getElementById('customer_id');
    const companyNameInput = document.getElementById('company_name');

    function renderCandidates(keyword) {
      if (!customerCandidates) return;
      customerCandidates.innerHTML = '';
      if (!keyword) return;
      const kw = keyword.trim().toLowerCase();
      const filtered = customers.filter(c => {
        const name = (c.name || '').toLowerCase();
        const kana = (c.name_kana || '').toLowerCase();
        return name.includes(kw) || kana.includes(kw);
      });
      filtered.forEach(c => {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'list-group-item list-group-item-action';
        item.textContent = c.name + (c.name_kana ? '（' + c.name_kana + '）' : '');
        item.dataset.customerId = c.id;
        item.dataset.customerName = c.name;
        item.onclick = () => {
          if (customerIdInput) customerIdInput.value = c.id;
          if (companyNameInput) companyNameInput.value = c.name;
          if (customerSearch) customerSearch.value = c.name;
          customerCandidates.innerHTML = '';
          // 支払条件自動反映用: hidden変更イベントを発火
          if (customerIdInput) {
            customerIdInput.dispatchEvent(new Event("change", { bubbles: true }));
          }
        };
        customerCandidates.appendChild(item);
      });
    }
    if (customerSearch) {
      customerSearch.addEventListener('input', e => {
        renderCandidates(e.target.value);
        // 顧客名を手動で消した場合はcustomer_idも消す
        if (!e.target.value && customerIdInput) customerIdInput.value = '';
      });
      customerSearch.addEventListener('blur', () => {
        setTimeout(() => { if (customerCandidates) customerCandidates.innerHTML = ''; }, 200);
      });
    }
    if (companyNameInput) {
      companyNameInput.addEventListener('input', () => {
        if (customerIdInput) customerIdInput.value = '';
      });
    }
    // 既存値があれば初期表示
    if (customerIdInput && customerIdInput.value && customers && customers.length) {
      const c = customers.find(c => c.id == customerIdInput.value);
      if (c && customerSearch) {
        customerSearch.value = c.name;
      }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
// ========== /Jinja埋め込みJSON読込 ==========

// ==============================
// 顧客選択時の支払条件自動反映
// ==============================
document.addEventListener('DOMContentLoaded', function() {
  function applyPaymentTermsFromCustomer(customerId, {force=false}={}) {
    if (!window.CUSTOMERS_META) return;
    const meta = window.CUSTOMERS_META[String(customerId)];
    if (!meta) return;
    const candidate = meta.payment_term_name || meta.payment_terms_legacy || "";
    const paymentInput = document.getElementById("payment_terms");
    if (!paymentInput) return;
    if (!force && paymentInput.value) return; // 既に入力済みなら上書きしない
    if (!candidate) return;
    paymentInput.value = candidate;
  }
  const customerIdInput = document.getElementById('customer_id');
  if (customerIdInput) {
    customerIdInput.addEventListener('change', function(e) {
      const val = e.target.value;
      if (val) applyPaymentTermsFromCustomer(val);
    });
    // 初期表示時: customer_idがあり、支払条件欄が空なら自動セット
    const paymentInput = document.getElementById("payment_terms");
    if (customerIdInput.value && paymentInput && !paymentInput.value) {
      applyPaymentTermsFromCustomer(customerIdInput.value);
    }
  }
});
// static/js/quotation_form.js (REAL, v6)

// どのファイルが実行されているか確認用シグネチャ
console.log("[quotation_form.js] *** ACTIVE FILE CHECK *** v6 @", window.location.href);
console.log("[quotation_form.js] loaded v6");

// ==============================
// 定数・ヘルパー
// ==============================

// 原価レート（hあたり）
window.LABOR_RATE = 7920; // 原価計算用

// 売価レート（設計・セットアップ共通）
const DESIGN_SELL_RATE = 15000;
const SETUP_SELL_RATE  = 15000;

// 安全な数値変換
function safeParseFloat(value) {
  if (value == null) return 0;
  const n = parseFloat(String(value).replace(/,/g, ""));
  return isNaN(n) ? 0 : n;
}

// 利益率計算（%）: (売価 - 原価) / 売価 * 100
function calcProfitRatePercent(sell, cost) {
  const sellNum = safeParseFloat(sell);
  const costNum = safeParseFloat(cost);
  if (sellNum <= 0) return 0;
  return ((sellNum - costNum) / sellNum) * 100;
}

// ==============================
// 製品原価・売価合計関連
// ==============================

// 製品原価合計（コスト）: 各行の (product.cost * quantity) を合計
window.calcProductCostTotal = function () {
  const products = Array.isArray(window.products) ? window.products : [];
  const tbody = document.getElementById("detail-body");
  if (!tbody) return 0;

  let totalCost = 0;
  Array.from(tbody.querySelectorAll("tr")).forEach((row) => {
    const select   = row.querySelector('select[name="product_id[]"]');
    const qtyInput = row.querySelector('input[name="quantity[]"]');
    if (!select || !qtyInput) return;

    const productId = select.value;
    const qty       = safeParseFloat(qtyInput.value);
    if (!productId || qty <= 0) return;

    const p = products.find((p) => String(p.id) === String(productId));
    if (!p) return;

    totalCost += safeParseFloat(p.cost) * qty;
  });
  return totalCost;
};

// 小計合計（売価）を #grand-total に反映
window.updateGrandTotal = function () {
  const tbody = document.getElementById("detail-body");
  let total = 0;
  if (tbody) {
    Array.from(tbody.querySelectorAll('input[name="subtotal[]"]')).forEach((input) => {
      total += safeParseFloat(input.value);
    });
  }
  const grandTotalEl = document.getElementById("grand-total");
  if (grandTotalEl) {
    grandTotalEl.textContent = total.toLocaleString();
  }
  return total;
};

// ==============================
// 設計・セットアップ工数計算
// ==============================

// --- 設計工数計算 ---
window.calcDesignHours = function (params) {
  const vehicleCount      = safeParseFloat(params.vehicleCount);
  const intersectionCount = safeParseFloat(params.intersections);
  const stationCount      = safeParseFloat(params.stations);
  const distance          = safeParseFloat(params.distance);

  // 設計工数計算式
  let designHoursBase =
    vehicleCount * intersectionCount * 2 +
    stationCount * 1 +
    distance / 100;

  let designHoursRaw = designHoursBase * 1.1; // 安全率
  return designHoursRaw; // 切り上げは呼び出し側で
};

// --- セットアップ工数計算 ---
window.calcSetupHours = function (params) {
  const vehicleCount      = safeParseFloat(params.vehicleCount);
  const intersectionCount = safeParseFloat(params.intersections);
  const stationCount      = safeParseFloat(params.stations);
  const distance          = safeParseFloat(params.distance);

  // AGV速度・CT
  const speed   = 30; // m/min
  const ct_min  = distance / speed + 0.1 * stationCount;

  // 試運転
  const trialCount = 10 * vehicleCount;
  const trialHours = (ct_min * trialCount) / 60;

  // バグ修正
  const bugFixHours = 1.0 * trialCount;

  // インターロック
  const interlockHours = 0.1 * vehicleCount * intersectionCount * stationCount;

  // 安全率
  const baseHours            = trialHours + bugFixHours + interlockHours;
  const baseHoursWithSafety  = baseHours * 1.1;

  // 人数ロジック
  let workers = 3;
  if (vehicleCount <= 1 && distance <= 50) {
    workers = 1;
  } else if (vehicleCount >= 2 && vehicleCount <= 5 && distance <= 100) {
    workers = 2;
  }

  const setupHoursRaw = baseHoursWithSafety * workers;
  return setupHoursRaw; // 切り上げは呼び出し側で
};

// ==============================
// 設計/セットアップ費用プレビュー
// ==============================

window.updateAutoFeePreview = function () {
  const distance      = safeParseFloat(document.getElementById("distance_m")?.value);
  const intersections = safeParseFloat(document.getElementById("intersection_count")?.value);
  const stations      = safeParseFloat(document.getElementById("station_count")?.value);
  const vehicles      = safeParseFloat(document.getElementById("vehicle_count")?.value);
  const equipments    = safeParseFloat(document.getElementById("equipment_count")?.value);
  const difficulty    = safeParseFloat(document.getElementById("circuit_difficulty")?.value);

  const params = {
    distance,
    intersections,
    stations,
    vehicleCount: vehicles,
    equipmentCount: equipments,
    difficulty,
  };

  // 設計・セットアップ工数（生値 → 切り上げ）
  const designHoursRaw = window.calcDesignHours(params);
  const setupHoursRaw  = window.calcSetupHours(params);

  const designHours = Math.ceil(designHoursRaw);
  const setupHours  = Math.ceil(setupHoursRaw);

  // 原価・売価
  const designCost = designHours * window.LABOR_RATE;
  const setupCost  = setupHours  * window.LABOR_RATE;
  const designFee  = designHours * DESIGN_SELL_RATE;
  const setupFee   = setupHours  * SETUP_SELL_RATE;

  // 利益率
  const designProfitRate = calcProfitRatePercent(designFee, designCost);
  const setupProfitRate  = calcProfitRatePercent(setupFee,  setupCost);

  // プレビュー欄更新
  const previewDesignFee         = document.getElementById("preview-design-fee");
  const previewSetupFee          = document.getElementById("preview-setup-fee");
  const previewDesignHours       = document.getElementById("preview-design-hours");
  const previewSetupHours        = document.getElementById("preview-setup-hours");
  const previewDesignCost        = document.getElementById("preview-design-cost");
  const previewSetupCost         = document.getElementById("preview-setup-cost");
  const previewDesignProfitRate  = document.getElementById("preview-design-profit-rate");
  const previewSetupProfitRate   = document.getElementById("preview-setup-profit-rate");

  if (previewDesignFee)        previewDesignFee.textContent        = designFee.toLocaleString();
  if (previewSetupFee)         previewSetupFee.textContent         = setupFee.toLocaleString();
  if (previewDesignHours)      previewDesignHours.textContent      = designHours.toFixed(1);
  if (previewSetupHours)       previewSetupHours.textContent       = setupHours.toFixed(1);
  if (previewDesignCost)       previewDesignCost.textContent       = designCost.toLocaleString();
  if (previewSetupCost)        previewSetupCost.textContent        = setupCost.toLocaleString();
  if (previewDesignProfitRate) previewDesignProfitRate.textContent = designProfitRate.toFixed(1) + "%";
  if (previewSetupProfitRate)  previewSetupProfitRate.textContent  = setupProfitRate.toFixed(1) + "%";

  // 合計用オブジェクトを構成して updateTotalProfitPreview に渡す
  const fees = {
    designFee,
    setupFee,
    totalWithFee: designFee + setupFee,
  };

  window.updateTotalProfitPreview(fees, designCost, setupCost);
};

// --- 全体利益プレビュー更新 ---
window.updateTotalProfitPreview = function (fees, designCost, setupCost) {
  const productTotal     = window.updateGrandTotal();       // 製品小計合計
  const productCostTotal = window.calcProductCostTotal();   // 製品原価合計
  const designPrice      = fees.designFee || 0;
  const setupPrice       = fees.setupFee  || 0;

  const totalSellBeforeDiscount = productTotal + designPrice + setupPrice;
  const totalCost               = productCostTotal + (designCost || 0) + (setupCost || 0);

  // --- 値引き計算 ---
  const discountRateInput = document.getElementById("discount_rate");
  const discountRate = discountRateInput ? safeParseFloat(discountRateInput.value) / 100 : 0;

  let discountAmount = 0;
  if (discountRate > 0 && totalSellBeforeDiscount > 0) {
    discountAmount = Math.round(totalSellBeforeDiscount * discountRate);
  }

  const finalSell = totalSellBeforeDiscount - discountAmount;

  // 最終利益率（最終売価に対する利益率）
  const finalProfitRate = finalSell > 0
    ? ((finalSell - totalCost) / finalSell) * 100
    : 0;

  const elTotalSell        = document.getElementById("preview-total-sell");
  const elTotalCost        = document.getElementById("preview-total-cost");
  const elFinalSell        = document.getElementById("preview-final-sell");
  const elTotalProfitRate  = document.getElementById("preview-total-profit-rate");
  const elDiscountAmount   = document.getElementById("discount-amount");

  if (elTotalSell)       elTotalSell.textContent       = totalSellBeforeDiscount.toLocaleString();
  if (elTotalCost)       elTotalCost.textContent       = totalCost.toLocaleString();
  if (elFinalSell)       elFinalSell.textContent       = finalSell.toLocaleString();
  if (elTotalProfitRate) elTotalProfitRate.textContent = finalProfitRate.toFixed(1) + "%";
  if (elDiscountAmount)  elDiscountAmount.textContent  =
    discountAmount > 0 ? "-" + discountAmount.toLocaleString() : "0";
};

// ==============================
// イベントバインド
// ==============================

// 自動計算パラメータ入力欄へのバインド
window.bindAutoFeeInputs = function () {
  const ids = [
    "distance_m",
    "intersection_count",
    "station_count",
    "vehicle_count",
    "equipment_count",
    "circuit_difficulty",
    "discount_rate",
  ];
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", function () {
        if (typeof window.updateAutoFeePreview === "function") {
          window.updateAutoFeePreview();
        }
      });
    }
  });
};

// 明細行イベントバインド（単価・数量・製品選択）
window.bindDetailRowEvents = function (row) {
  const unitPriceInput = row.querySelector('input[name="unit_price[]"]');
  const quantityInput  = row.querySelector('input[name="quantity[]"]');
  const subtotalInput  = row.querySelector('input[name="subtotal[]"]');
  const productSelect  = row.querySelector('select[name="product_id[]"]');
  const descInput      = row.querySelector('input[name="description[]"]');
  const codeInput      = row.querySelector('input[name="code[]"]');

  let bindCount = 0;

  function recalcSubtotal() {
    if (!unitPriceInput || !quantityInput || !subtotalInput) return;
    const price = safeParseFloat(unitPriceInput.value);
    const qty   = safeParseFloat(quantityInput.value);
    const subtotal = price * qty;
    subtotalInput.value = subtotal > 0 ? subtotal : "";
    window.updateGrandTotal();
    if (typeof window.updateAutoFeePreview === "function") {
      window.updateAutoFeePreview();
    }
  }

  // 単価・数量の変更で小計／合計を更新
  if (unitPriceInput && quantityInput && subtotalInput) {
    [unitPriceInput, quantityInput].forEach((input) => {
      input.addEventListener("input", recalcSubtotal);
      bindCount++;
    });
  }

  // 製品選択時に品名・単価・コードを自動反映
  if (productSelect && Array.isArray(window.products)) {
    productSelect.addEventListener("change", function () {
      const p = window.products.find(
        (p) => String(p.id) === String(productSelect.value)
      );

      if (!p) {
        // 選択解除時は関連項目クリア
        if (descInput)  descInput.value  = "";
        if (codeInput)  codeInput.value  = "";
        if (unitPriceInput) {
          unitPriceInput.value = "";
            unitPriceInput.readOnly = false; // 初期は編集可
        }
        recalcSubtotal();
        return;
      }

      // 品名補完
      if (descInput) {
        descInput.value = p.name || "";
      }

      // コードもセット（idやcodeプロパティ優先）
      if (codeInput) {
        codeInput.value = p.code != null ? p.code : p.id;
      }

      // 単価はマスタから自動セット＆編集禁止
      if (unitPriceInput) {
        const unitPrice = p.unit_price != null ? p.unit_price : p.price;
        if (unitPrice != null) {
          unitPriceInput.value = unitPrice;
        }
        unitPriceInput.readOnly = true;
      }

      // 数量が空ならデフォルト1
      if (quantityInput && !quantityInput.value) {
        quantityInput.value = 1;
      }

      recalcSubtotal();
    });
    bindCount++;
  }

  console.log(
    "[quotation_form.js] bindDetailRowEvents: row にイベントをバインドしました。bindCount=",
    bindCount
  );
};

// 明細行生成
window.createDetailRow = function () {
  const row = document.createElement("tr");

  // 製品 select
  const tdProduct = document.createElement("td");
  const select = document.createElement("select");
  select.name = "product_id[]";
  select.className = "form-select product-select-custom";
  select.innerHTML = '<option value="">選択</option>';
  if (Array.isArray(window.products)) {
    window.products.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name || p.id; // 表示は name 優先
      select.appendChild(opt);
    });
  }
  tdProduct.appendChild(select);
  row.appendChild(tdProduct);


  // 品名（description）
  const tdName = document.createElement("td");
  const descInput = document.createElement("input");
  descInput.type = "text";
  descInput.name = "description[]";
  descInput.className = "form-control";
  tdName.appendChild(descInput);
  // コード（code）hidden input
  const codeInput = document.createElement("input");
  codeInput.type = "hidden";
  codeInput.name = "code[]";
  codeInput.value = "";
  tdName.appendChild(codeInput);
  row.appendChild(tdName);

  // 単価
  const tdUnitPrice = document.createElement("td");
  const unitPriceInput = document.createElement("input");
  unitPriceInput.type = "number";
  unitPriceInput.name = "unit_price[]";
  unitPriceInput.className = "form-control text-end";
  unitPriceInput.min = "0";
  unitPriceInput.step = "1";
  unitPriceInput.readOnly = false; // 初期は編集可
  tdUnitPrice.appendChild(unitPriceInput);
  row.appendChild(tdUnitPrice);

  // 数量
  const tdQty = document.createElement("td");
  const qtyInput = document.createElement("input");
  qtyInput.type = "number";
  qtyInput.name = "quantity[]";
  qtyInput.className = "form-control text-end";
  qtyInput.min = "0";
  qtyInput.step = "1";
  tdQty.appendChild(qtyInput);
  row.appendChild(tdQty);

  // 小計
  const tdSubtotal = document.createElement("td");
  const subtotalInput = document.createElement("input");
  subtotalInput.type = "text";
  subtotalInput.name = "subtotal[]";
  subtotalInput.className = "form-control text-end";
  subtotalInput.readOnly = true;
  tdSubtotal.appendChild(subtotalInput);
  row.appendChild(tdSubtotal);

  // 削除ボタン
  const tdRemove = document.createElement("td");
  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = "btn btn-sm btn-outline-danger remove-row-btn";
  removeBtn.textContent = "削除";
  tdRemove.appendChild(removeBtn);
  row.appendChild(tdRemove);

  // 行イベントをバインド
  if (typeof window.bindDetailRowEvents === "function") {
    window.bindDetailRowEvents(row);
  }

  // 削除ボタンイベント
  removeBtn.addEventListener("click", function () {
    const tbody = document.getElementById("detail-body");
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll("tr"));
    if (rows.length <= 1) {
      // 1行だけならクリア
      row.querySelectorAll("input, select, textarea").forEach((el) => {
        if (el.type === "checkbox" || el.type === "radio") {
          el.checked = false;
        } else {
          el.value = "";
        }
      });
    } else {
      // 2行以上なら削除
      tbody.removeChild(row);
    }
    window.updateGrandTotal();
    if (typeof window.updateAutoFeePreview === "function") {
      window.updateAutoFeePreview();
    }
  });

  return row;
};

// 明細行追加
window.addDetailRow = function () {
  const tbody = document.getElementById("detail-body");
  if (!tbody || typeof window.createDetailRow !== "function") return;
  const row = window.createDetailRow();
  tbody.appendChild(row);
  window.updateGrandTotal();
  if (typeof window.updateAutoFeePreview === "function") {
    window.updateAutoFeePreview();
  }
};

// ==============================
// 初期化
// ==============================

document.addEventListener("DOMContentLoaded", function () {
  console.log("[quotation_form.js] DOMContentLoaded - init start");

  const tbody = document.getElementById("detail-body");
  // 改定時: INITIAL_DETAILSがあれば全行復元
  if (tbody && Array.isArray(window.INITIAL_DETAILS) && window.INITIAL_DETAILS.length > 0) {
    tbody.innerHTML = "";
    window.INITIAL_DETAILS.forEach(function (d) {
      if (typeof window.createDetailRow === "function") {
        const row = window.createDetailRow();
        if (row) {

          const isFixed = d.label === "設計費（パラメータ）" || d.label === "現地セットアップ（パラメータ）";
          // より安全な product_id 判定
          const pidStr = (d.product_id == null ? "" : String(d.product_id)).trim();
          const hasProduct = pidStr !== "" && pidStr !== "0";

          // product_id有り行
          if (hasProduct && row.querySelector('select[name="product_id[]"]')) {
            const sel = row.querySelector('select[name="product_id[]"]');
            // 先に数量
            if (d.quantity !== undefined && row.querySelector('input[name="quantity[]"]')) {
              row.querySelector('input[name="quantity[]"]').value = d.quantity;
            }
            // valueは文字列で揃える
            sel.value = pidStr;
            if (!isFixed) {
              sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
          }

          // product_idが無い行または0（自由入力行）
          if (!hasProduct) {
            if (d.description !== undefined && row.querySelector('input[name="description[]"]')) row.querySelector('input[name="description[]"]').value = d.description;
            if (d.price !== undefined && row.querySelector('input[name="unit_price[]"]')) row.querySelector('input[name="unit_price[]"]').value = d.price;
            if (d.quantity !== undefined && row.querySelector('input[name="quantity[]"]')) row.querySelector('input[name="quantity[]"]').value = d.quantity;
            if (d.subtotal !== undefined && row.querySelector('input[name="subtotal[]"]')) row.querySelector('input[name="subtotal[]"]').value = d.subtotal;
          }

          // code
          if (d.code !== undefined && row.querySelector('input[name="code[]"]')) {
            row.querySelector('input[name="code[]"]').value = d.code;
          }
          // subtotal（product_id有り行も明示的にセット）
          if (d.subtotal !== undefined && row.querySelector('input[name="subtotal[]"]')) {
            row.querySelector('input[name="subtotal[]"]').value = d.subtotal;
          }
          // --- 設計費/セットアップ費行はUI固定 ---
          if (isFixed) {
            const sel = row.querySelector('select[name="product_id[]"]');
            if (sel) sel.disabled = true;
            const desc = row.querySelector('input[name="description[]"]');
            if (desc) desc.readOnly = true;
            const up = row.querySelector('input[name="unit_price[]"]');
            if (up) up.readOnly = true;
            const qty = row.querySelector('input[name="quantity[]"]');
            if (qty) qty.readOnly = true;
            const removeBtn = row.querySelector('.remove-row-btn');
            if (removeBtn) removeBtn.disabled = true;
          }
          tbody.appendChild(row);
        }
      }
    });
    // 復元後に1回だけ合計等を更新
    window.updateGrandTotal();
    if (typeof window.updateAutoFeePreview === "function") {
      window.updateAutoFeePreview();
    }
  } else if (tbody) {
    // 新規作成時: 既存ロジック
    const rows = Array.from(tbody.querySelectorAll("tr"));
    if (rows.length === 0) {
      if (typeof window.addDetailRow === "function") {
        window.addDetailRow();
      }
    } else {
      rows.forEach((row) => {
        if (typeof window.bindDetailRowEvents === "function") {
          window.bindDetailRowEvents(row);
        }
      });
    }
  }

  const addRowBtn = document.getElementById("add-row-btn");
  if (addRowBtn && typeof window.addDetailRow === "function") {
    addRowBtn.addEventListener("click", function () {
      window.addDetailRow();
      // 追加後に全selectを確認
      setTimeout(() => {
        const selects = document.querySelectorAll('select.product-select-custom');
        console.log(`[quotation_form.js] product-select-custom count (after add):`, selects.length);
      }, 0);
    });
  }

  if (typeof window.bindAutoFeeInputs === "function") {
    window.bindAutoFeeInputs();
  }

  window.updateGrandTotal();
  if (typeof window.updateAutoFeePreview === "function") {
    window.updateAutoFeePreview();
  }

  // 初期表示時に全selectを一度だけ確認
  setTimeout(() => {
    const selects = document.querySelectorAll('select.product-select-custom');
    console.log(`[quotation_form.js] product-select-custom count (init):`, selects.length);
  }, 0);

  console.log(
    "[quotation_form.js] typeof updateAutoFeePreview =",
    typeof window.updateAutoFeePreview,
    ", typeof calcDesignHours =",
    typeof window.calcDesignHours,
    ", typeof updateTotalProfitPreview =",
    typeof window.updateTotalProfitPreview
  );

  console.log("[quotation_form.js] DOMContentLoaded - init done");
});
