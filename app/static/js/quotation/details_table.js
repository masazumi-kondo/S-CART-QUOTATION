// app/static/js/quotation/details_table.js
(function () {
		// Fallback for safeParseFloat if not loaded (safety net)
		if (typeof window.safeParseFloat !== "function") {
			window.safeParseFloat = function (v) {
				if (v == null) return 0;
				const s = String(v).replace(/,/g, "").trim();
				if (s === "") return 0;
				const n = Number(s);
				return Number.isFinite(n) ? n : 0;
			};
			console.warn("[details_table] safeParseFloat missing -> fallback attached");
		}
	if (window.__detailsTableModuleLoaded) return;
	window.__detailsTableModuleLoaded = true;

	// ==============================
	// products-json 読み込み
	// ==============================
	function readProducts() {
		const el = document.getElementById("products-json");
		if (!el) return [];
		try {
			return JSON.parse(el.textContent || "[]");
		} catch (e) {
			console.error("[details_table] products-json parse failed", e);
			return [];
		}
	}

	function getProductMap() {
		if (window.__PRODUCT_MAP__) return window.__PRODUCT_MAP__;
		const products = readProducts();
		window.__PRODUCTS__ = products;
		window.__PRODUCT_MAP__ = {};
		products.forEach(p => {
			window.__PRODUCT_MAP__[String(p.id)] = p;
		});
		return window.__PRODUCT_MAP__;
	}

	function n(v) {
		if (v == null) return 0;
		const s = String(v).replace(/,/g, "").trim();
		if (s === "") return 0;
		const x = Number(s);
		return Number.isFinite(x) ? x : 0;
	}

	// 製品をrow に適用
	function applyProductToRow(row, productId) {
		if (!row) return;
		const productMap = getProductMap();
		const p = productMap[String(productId || "")];
		if (!p) return;

		const desc = row.querySelector(".description-input");
		const unit = row.querySelector(".unit-price-input");
		const qty = row.querySelector(".quantity-input");
		const subtotal = row.querySelector(".subtotal-input");
		const cost = row.querySelector(".cost-input");

		if (desc && !desc.value) {
			desc.value = p.name || "";
		}

		if (unit) {
			unit.value = Math.round(n(p.unit_price || 0));
		}

		if (cost) {
			cost.value = Math.round(n(p.cost || 0));
		}

		if (qty && n(qty.value) <= 0) {
			qty.value = 1;
		}

		const q = n(qty?.value);
		const u = n(unit?.value);
		if (subtotal) {
			subtotal.value = Math.round(u * q);
		}

		if (typeof window.updateGrandTotal === "function") {
			window.updateGrandTotal();
		}
		if (typeof window.updateTotalProfitPreview === "function") {
			window.updateTotalProfitPreview({ applyDiscount: false });
		}
	}

	// 製品選択イベント
	document.addEventListener("change", function (e) {
		const select = e.target.closest(".product-select-custom");
		if (!select) return;
		const row = select.closest("tr");
		applyProductToRow(row, select.value);
	});

	// ==============================
	// updateGrandTotal
	// ==============================
	window.updateGrandTotal = window.updateGrandTotal || function updateGrandTotal() {
		try {
			const tbody = document.getElementById("detail-body");
			const rows = tbody ? Array.from(tbody.querySelectorAll("tr")) : [];


			 let totalSell = 0;
			 let totalCost = 0;
			 for (const tr of rows) {
					 const upEl = tr.querySelector('input[name="unit_price[]"]');
					 const qtyEl = tr.querySelector('input[name="quantity[]"]');
					 const subEl = tr.querySelector('input[name="subtotal[]"]');
					 const costEl = tr.querySelector('input[name="cost[]"]');

					 const up = upEl ? window.safeParseFloat(String(upEl.value || "").replace(/,/g, "")) : 0;
					 const qty = qtyEl ? window.safeParseFloat(String(qtyEl.value || "").replace(/,/g, "")) : 0;
					 const sub = Math.round(up * qty);

					 if (subEl) subEl.value = sub > 0 ? sub.toLocaleString() : "";
					 totalSell += (Number.isFinite(sub) ? sub : 0);
					 // 原価集計: cost[]列があれば使う、なければ売価と同じ（仮）
					 let cost = costEl ? window.safeParseFloat(costEl.value) * qty : up * qty;
					 totalCost += (Number.isFinite(cost) ? cost : 0);
			 }

// 合計値をwindow.QUOTE_TOTALSに保存（0の場合は既存値を維持）
				 if (totalSell > 0 || totalCost > 0 || !window.QUOTE_TOTALS) {
					 window.QUOTE_TOTALS = {
						 sellBeforeDiscount: Math.round(totalSell || 0),
						 costTotal: Math.round(totalCost || 0)
					 };
				 }

			   const setTextIf = (id, v) => {
				   const el = document.getElementById(id);
				   if (!el) return;
				   if ("value" in el) el.value = v;
				   else el.textContent = v;
			   };

			   const totalSellStr = Math.round(totalSell).toLocaleString();
			   const totalCostStr = Math.round(totalCost).toLocaleString();
			   setTextIf("grand_total_sell", totalSellStr);
			   setTextIf("grand_total_cost", totalCostStr);
			   // 旧互換
			   setTextIf("preview-total-sell", totalSellStr);
			   setTextIf("grand_total", totalSellStr);
			   setTextIf("grandTotal", totalSellStr);
			   setTextIf("total_amount", totalSellStr);
			   setTextIf("total_sell", totalSellStr);

			   // 新profit-summary-section用
			   setTextIf("sum_sell_before_discount", totalSellStr);
			   setTextIf("sum_cost_total", totalCostStr);

			// profit_preview:updateイベント発火
			if (typeof window.updateTotalProfitPreview === "function") window.updateTotalProfitPreview();
			document.dispatchEvent(new CustomEvent("profit_preview:update"));
			return totalSell;
		} catch (e) {
			console.warn("[updateGrandTotal] failed:", e);
			return 0;
		}
	};

	// ==============================
	// createDetailRow / addDetailRow
	// ==============================
	window.createDetailRow = window.createDetailRow || function () {
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
				opt.textContent = p.name || p.id;
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
		descInput.className = "form-control description-input";
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
		unitPriceInput.className = "form-control text-end unit-price-input";
		unitPriceInput.min = "0";
		unitPriceInput.step = "1";
		unitPriceInput.readOnly = false;
		tdUnitPrice.appendChild(unitPriceInput);
		row.appendChild(tdUnitPrice);

		// 数量
		const tdQty = document.createElement("td");
		const qtyInput = document.createElement("input");
		qtyInput.type = "number";
		qtyInput.name = "quantity[]";
		qtyInput.className = "form-control text-end quantity-input";
		qtyInput.min = "0";
		qtyInput.step = "1";
		tdQty.appendChild(qtyInput);
		row.appendChild(tdQty);

		// 小計
		const tdSubtotal = document.createElement("td");
		const subtotalInput = document.createElement("input");
		subtotalInput.type = "text";
		subtotalInput.name = "subtotal[]";
		subtotalInput.className = "form-control text-end subtotal-input";
		subtotalInput.readOnly = true;
		tdSubtotal.appendChild(subtotalInput);
		// 原価hidden
		const costInput = document.createElement("input");
		costInput.type = "hidden";
		costInput.name = "cost[]";
		costInput.className = "cost-input";
		costInput.value = "";
		tdSubtotal.appendChild(costInput);
		row.appendChild(tdSubtotal);

		// 追加/削除ボタン
		const tdRemove = document.createElement("td");
		const addBtn = document.createElement("button");
		addBtn.type = "button";
		addBtn.className = "btn btn-outline-secondary btn-sm add-row";
		addBtn.textContent = "＋";
		tdRemove.appendChild(addBtn);
		const removeBtn = document.createElement("button");
		removeBtn.type = "button";
		removeBtn.className = "btn btn-outline-danger btn-sm remove-row";
		removeBtn.textContent = "－";
		tdRemove.appendChild(removeBtn);
		row.appendChild(tdRemove);

		// 行イベントをバインド
		if (typeof window.bindDetailRowEvents === "function") {
			window.bindDetailRowEvents(row);
		}

		return row;
	};

	window.addDetailRow = window.addDetailRow || function () {
		const tbody = document.getElementById("detail-body");
		if (!tbody || typeof window.createDetailRow !== "function") return;
		const row = window.createDetailRow();
		tbody.appendChild(row);
		window.updateGrandTotal?.();
	};

	// ==============================
	// init bindings (delegation)
	// ==============================
	window.initDetailsTableBindings = function initDetailsTableBindings() {
		if (window.__detailsTableBound) return;
		window.__detailsTableBound = true;

		const table = document.getElementById("details-table");
		const tbody = document.getElementById("detail-body");
		const delegateTarget = tbody || table;

		// change delegation
		if (!window.__quotationDetailDelegated && delegateTarget) {
			window.__quotationDetailDelegated = true;
			delegateTarget.addEventListener("change", function (e) {
				const sel = e.target.closest('select[name="product_id[]"]');
				if (sel) {
					const tr = sel.closest("tr");
					if (!tr) return;
					const productId = sel.value;

					const unitPriceEl = tr.querySelector('input[name="unit_price[]"]');
					const qtyEl = tr.querySelector('input[name="quantity[]"]');
					const subtotalEl = tr.querySelector('input[name="subtotal[]"]');
					const codeEl = tr.querySelector('input[name="code[]"]');
					const descEl = tr.querySelector('input[name="description[]"]');

					let p = null;
					if (Array.isArray(window.products)) {
						p = window.products.find((x) => String(x.id) === String(productId));
					}

					if (p) {
						if (descEl && !descEl.value) descEl.value = p.name || descEl.value;
						if (codeEl) codeEl.value = p.code || p.id || "";
						if (unitPriceEl) unitPriceEl.value = String(Math.round(Number(p.price || 0)));
					} else {
						if (codeEl) codeEl.value = "";
						if (unitPriceEl) unitPriceEl.value = unitPriceEl.value || "";
					}

					if (unitPriceEl && qtyEl && subtotalEl) {
						const subtotal = window.safeParseFloat(unitPriceEl.value) * window.safeParseFloat(qtyEl.value);
						subtotalEl.value = subtotal > 0 ? Math.round(subtotal).toLocaleString() : "";
					}

					window.updateGrandTotal?.();
					return;
				}

				const unitPriceEl2 = e.target.closest('input[name="unit_price[]"]');
				const qtyEl2 = e.target.closest('input[name="quantity[]"]');
				if (unitPriceEl2 || qtyEl2) {
					const tr = (unitPriceEl2 || qtyEl2).closest("tr");
					if (!tr) return;

					const up = tr.querySelector('input[name="unit_price[]"]');
					const qty = tr.querySelector('input[name="quantity[]"]');
					const subtotalEl = tr.querySelector('input[name="subtotal[]"]');

					if (up && qty && subtotalEl) {
						const subtotal = window.safeParseFloat(up.value) * window.safeParseFloat(qty.value);
						subtotalEl.value = subtotal > 0 ? Math.round(subtotal).toLocaleString() : "";
					}
					window.updateGrandTotal?.();
				}
			});
		}

		// input delegation - 単価/数量変更時の小計更新
		if (delegateTarget) {
			delegateTarget.addEventListener("input", function (e) {
				if (e.target.classList.contains("unit-price-input") || e.target.classList.contains("quantity-input")) {
					const tr = e.target.closest("tr");
					if (!tr) return;
					const unit = tr.querySelector(".unit-price-input");
					const qty = tr.querySelector(".quantity-input");
					const subtotal = tr.querySelector(".subtotal-input");
					if (unit && qty && subtotal) {
						const u = n(unit.value);
						const q = n(qty.value);
						subtotal.value = Math.round(u * q);
					}
					window.updateGrandTotal?.();
				}
			});
		}

		// click delegation
		if (table && tbody) {
			table.addEventListener("click", (e) => {
				const addBtn = e.target.closest("button.add-row");
				if (addBtn) {
					e.preventDefault();
					const tr = addBtn.closest("tr");
					if (tr && tr.classList.contains("js-fixed-row")) return;
					const row = window.createDetailRow?.();
					if (row && tr && tr.parentNode === tbody) {
						tr.insertAdjacentElement("afterend", row);
					} else {
						window.addDetailRow?.();
					}
					window.updateGrandTotal?.();
					return;
				}

				const rmBtn = e.target.closest("button.remove-row, button.remove-row-btn");
				if (rmBtn) {
					e.preventDefault();
					const tr = rmBtn.closest("tr");
					if (!tr) return;
					if (tr.classList.contains("js-fixed-row")) return;

					const rows = Array.from(tbody.querySelectorAll("tr"));
					if (rows.length <= 1) {
						tr.querySelectorAll("input, select, textarea").forEach((el) => {
							if (el.type === "checkbox" || el.type === "radio") el.checked = false;
							else el.value = "";
						});
					} else {
						tr.remove();
					}
					window.updateGrandTotal?.();
				}
			});
		}

		// submit POST length diag
		if (!window.__postLenDiagBound) {
			window.__postLenDiagBound = true;
			const form = document.querySelector("form");
			if (form) {
				form.addEventListener("submit", () => {
					const len = (sel) => document.querySelectorAll(sel).length;
					console.log("[POST len]",
						"product_id[]:", len('select[name="product_id[]"]') + len('input[type="hidden"][name="product_id[]"]'),
						"desc[]:", len('input[name="description[]"]'),
						"unit_price[]:", len('input[name="unit_price[]"]'),
						"qty[]:", len('input[name="quantity[]"]'),
						"subtotal[]:", len('input[name="subtotal[]"]'),
					);
				});
			}
		}
	};
})();
// 明細テーブル生成・追加・削除・合計計算・イベント委譲
// 依存: common.js

// V2固定2行（設計費・現地セットアップ費）upsert
// 新仕様（v2_core_new.js）: designSellAmount, designCostAmount, setupSellAmount, setupCostAmount
// 旧仕様（互換性）: designSell, designCost, setupSell, setupCost
window.upsertV2FixedRows = function upsertV2FixedRows({ designSellAmount, designCostAmount, setupSellAmount, setupCostAmount, designSell, designCost, setupSell, setupCost }) {
	// 新仕様パラメータがなければ旧仕様パラメータを使用（後方互換性）
	const sell1 = designSellAmount || designSell || 0;
	const cost1 = designCostAmount || designCost || 0;
	const sell2 = setupSellAmount || setupSell || 0;
	const cost2 = setupCostAmount || setupCost || 0;

	const tbody = document.getElementById("detail-body");
	if (!tbody) return;

	function fmt(n) {
		return Math.round(Number(n || 0)).toLocaleString();
	}

	function raw(n) {
		return String(Math.round(Number(n || 0)));
	}

	function ensureRow(code, label, sell, cost) {
		let tr = tbody.querySelector(`tr[data-fixed-code="${code}"]`);

		if (!tr) {
			tr = document.createElement("tr");
			tr.classList.add("js-fixed-row");
			tr.setAttribute("data-fixed-code", code);

			// Prepare formatted values for HTML template
			const sellStr = raw(sell);
			const costStr = raw(cost);
			const sellFormatted = fmt(sell);

			tr.innerHTML = `
				<td>
					<input type="hidden" name="product_id[]" value="">
					<span class="badge bg-info">${label}</span>
				</td>
				<td>
					<input type="text" class="form-control description-input" name="description[]" value="${label}" readonly>
					<input type="hidden" name="code[]" value="${code}">
				</td>
				<td>
					<input type="number" class="form-control text-end unit-price-input" name="unit_price[]" value="${sellStr}" readonly>
				</td>
				<td>
					<input type="number" class="form-control text-end quantity-input" name="quantity[]" value="1" readonly>
				</td>
				<td>
					<input type="text" class="form-control text-end subtotal-input" name="subtotal[]" value="${sellFormatted}" readonly>
					<input type="hidden" name="cost[]" value="${costStr}">
				</td>
				<td class="text-center">
					<span class="text-muted small">固定</span>
				</td>
			`;

			tbody.insertBefore(tr, tbody.firstChild);
		}

		// 念のため、既存行の場合も値を再更新（セキュアネス重視）
		const unitPriceInput = tr.querySelector('input[name="unit_price[]"]');
		unitPriceInput.value = raw(sell);
		unitPriceInput.setAttribute('value', raw(sell)); // HTML属性も更新
		
		const qtyInput = tr.querySelector('input[name="quantity[]"]');
		qtyInput.value = "1";
		qtyInput.setAttribute('value', "1");
		
		const subtotalInput = tr.querySelector('input[name="subtotal[]"]');
		const subtotalFormatted = fmt(sell);
		subtotalInput.value = subtotalFormatted;
		subtotalInput.setAttribute('value', subtotalFormatted);
		
		const costInput = tr.querySelector('input[name="cost[]"]');
		const costRaw = raw(cost);
		costInput.value = costRaw;
		costInput.setAttribute('value', costRaw);

		// 集計対象から外れないよう disabled は使わない。readonlyのみ。
		tr.querySelectorAll("input").forEach(el => {
			el.disabled = false;
			el.readOnly = true;
		});

		return tr;
	}

	const trDesign = ensureRow("v2_design", "設計費（V2自動算出）", sell1, cost1);
	const trSetup = ensureRow("v2_setup", "現地セットアップ費（V2自動算出）", sell2, cost2);

	// 並び順：設計費 → 現地セットアップ費 → 通常明細
	if (trDesign && tbody.firstChild !== trDesign) {
		tbody.insertBefore(trDesign, tbody.firstChild);
	}
	if (trSetup && trDesign.nextSibling !== trSetup) {
		tbody.insertBefore(trSetup, trDesign.nextSibling);
	}

	if (typeof window.updateGrandTotal === "function") window.updateGrandTotal();
	if (typeof window.updateTotalProfitPreview === "function") window.updateTotalProfitPreview();
};
