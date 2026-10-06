/**
 * sim_import.js - 工数明細（シミュレーター取り込み／手入力／理由付き調整）
 *
 * 状態(state.lines)を唯一の正とし、設計費・現地セットアップ費の表を毎回そこから描画する。
 * 時間→金額の換算は state.rates（取り込み時のサーバー賃率）を掛けるだけで、係数計算は行わない。
 * hidden: sim_result_json（取り込み元）, effort_lines_json（rates+lines。保存して再編集で復元）
 * 依存: details_table.js (updateGrandTotal / updateTotalProfitPreview)
 */
(function () {
	"use strict";
	if (window.__simImportLoaded) return;
	window.__simImportLoaded = true;

	const PREFIX = { design: "設計費", setup: "現地セットアップ費" };
	const KIND_LABEL = { design: "設計", setup: "現地" };
	const state = { rates: { cost: 0, sell: 0 }, lines: [], editing: -1 };

	const $ = (id) => document.getElementById(id);

	function esc(s) {
		return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
	}
	function yen(n) {
		return Math.round(Number(n || 0)).toLocaleString("ja-JP");
	}
	function setMsg(html, kind) {
		const el = $("sim_import_msg");
		if (!el) return;
		el.className = "small mt-2 " + (kind === "error" ? "text-danger" : kind === "warn" ? "text-warning-emphasis" : "text-muted");
		el.innerHTML = html || "";
	}

	function lineDescription(ln) {
		const label = `${ln.item_id || ""} ${ln.item}`.trim();
		return `${PREFIX[ln.kind]}｜${label}（${Number(ln.hours)}h）`;
	}
	function price(ln) { return Math.round(Number(ln.hours) * state.rates.sell); }
	function cost(ln) { return Math.round(Number(ln.hours) * state.rates.cost); }
	function isAdjusted(ln) {
		return ln.source === "sim" && ln.orig_hours != null && Math.abs(Number(ln.hours) - Number(ln.orig_hours)) > 1e-9;
	}

	// ---------------- 取り込み情報（仕様・前提）の表示 ----------------
	function renderInfo(result) {
		const box = $("sim_import_info");
		if (!box) return;
		if (!result) { box.classList.add("d-none"); box.innerHTML = ""; return; }
		const v = result.vehicles || {};
		const p = result.performance || {};
		const rows = [];
		rows.push(`<div><b>シミュレーション案件:</b> ${esc(result.sim_project || "-")} <span class="text-muted">(v${esc(result.sim_version || "-")} / ${esc(result.generated_at || "-")})</span></div>`);
		rows.push(`<div><b>機種・台数（参考）:</b> ${esc(v.model || "-")} × ${esc(v.count == null ? "-" : v.count)}台</div>`);
		if (v.spec_text) rows.push(`<div><b>シミュレーション時の仕様:</b> ${esc(v.spec_text).replace(/\n/g, "<br>")}</div>`);
		if (p.ct_s != null || p.throughput_per_h != null) {
			rows.push(`<div><b>性能:</b> CT ${esc(p.ct_s == null ? "-" : p.ct_s)} 秒 / 処理量 ${esc(p.throughput_per_h == null ? "-" : p.throughput_per_h)} 回/h</div>`);
		}
		if (result.notes) rows.push(`<div><b>前提条件:</b> ${esc(result.notes).replace(/\n/g, "<br>")}</div>`);
		rows.push('<div class="text-muted">※ 機種・台数・オプションは自動反映しません。上記を見て、製品を明細の「製品（マスタ）」から選んでください。</div>');
		box.innerHTML = rows.join("");
		box.classList.remove("d-none");
	}

	// ---------------- 工数表の描画 ----------------
	function badge(ln) {
		if (isAdjusted(ln)) return '<span class="badge bg-warning text-dark">調整</span>';
		if (ln.source === "sim") return '<span class="badge bg-info">SIM</span>';
		return '<span class="badge bg-secondary">手入力</span>';
	}

	function buildRow(ln, idx) {
		const code = ln.kind === "design" ? "v2_design" : "v2_setup";
		const tr = document.createElement("tr");
		tr.classList.add("js-fixed-row");
		tr.setAttribute("data-fixed-code", code);
		tr.setAttribute("data-sim-line", String(idx));
		const hint = [];
		if (ln.basis) hint.push(`根拠: ${esc(ln.basis)}`);
		if (isAdjusted(ln)) hint.push(`元 ${Number(ln.orig_hours)}h → ${Number(ln.hours)}h／理由: ${esc(ln.reason)}`);
		let actions;
		if (state.editing === idx) {
			actions = `<span class="text-muted small">編集中</span>`;
		} else if (ln.source === "sim") {
			actions = `<button type="button" class="btn btn-outline-secondary btn-sm" data-sim-act="adjust" data-i="${idx}">調整</button>`;
		} else {
			actions = `<button type="button" class="btn btn-outline-secondary btn-sm" data-sim-act="adjust" data-i="${idx}">修正</button> `
				+ `<button type="button" class="btn btn-outline-danger btn-sm" data-sim-act="remove" data-i="${idx}">－</button>`;
		}
		tr.innerHTML = `
			<td>${badge(ln)}</td>
			<td>
				<input type="text" class="form-control description-input" name="description[]" value="${esc(lineDescription(ln))}" readonly>
				<input type="hidden" name="product_id[]" value="">
				<input type="hidden" name="code[]" value="${code}">
				${hint.length ? `<div class="small text-muted mt-1">${hint.join("<br>")}</div>` : ""}
			</td>
			<td><input type="number" class="form-control text-end unit-price-input" name="unit_price[]" value="${price(ln)}" readonly></td>
			<td><input type="number" class="form-control text-end quantity-input" name="quantity[]" value="1" readonly></td>
			<td>
				<input type="text" class="form-control text-end subtotal-input" name="subtotal[]" value="${yen(price(ln))}" readonly>
				<input type="hidden" class="cost-input" name="cost[]" value="${cost(ln)}">
			</td>
			<td class="text-center text-nowrap">${actions}</td>`;
		return tr;
	}

	function buildEditRow(ln, idx) {
		const tr = document.createElement("tr");
		tr.classList.add("table-warning");
		const needReason = ln.source === "sim" && ln.orig_hours != null;
		tr.innerHTML = `
			<td colspan="6">
				<div class="row g-2 align-items-end">
					<div class="col-md-4"><div class="small fw-bold">${esc(lineDescription(ln))}</div>
						${needReason ? `<div class="small text-muted">元の値: ${Number(ln.orig_hours)}h</div>` : ""}</div>
					<div class="col-md-2"><label class="form-label small mb-0">時間(h)</label>
						<input type="number" class="form-control form-control-sm" id="sim_edit_hours" min="0" max="9999" step="0.5" value="${Number(ln.hours)}"></div>
					${needReason ? `<div class="col-md-4"><label class="form-label small mb-0">変更理由（必須）</label>
						<input type="text" class="form-control form-control-sm" id="sim_edit_reason" maxlength="200" value="${esc(ln.reason || "")}"></div>` : ""}
					<div class="col-md-2 text-nowrap">
						<button type="button" class="btn btn-primary btn-sm" data-sim-act="commit" data-i="${idx}">確定</button>
						<button type="button" class="btn btn-outline-secondary btn-sm" data-sim-act="cancel">取消</button>
					</div>
				</div>
				<div id="sim_edit_err" class="small text-danger mt-1"></div>
			</td>`;
		return tr;
	}

	function render() {
		const tbody = $("v2-detail-body");
		if (!tbody) return;
		// 旧ウィザード由来の既存行（data-sim-line なし）は残し、この画面で管理する行だけ描き直す
		tbody.querySelectorAll("tr[data-sim-line], tr.table-warning").forEach((tr) => tr.remove());
		state.lines.forEach((ln, i) => {
			tbody.appendChild(buildRow(ln, i));
			if (state.editing === i) tbody.appendChild(buildEditRow(ln, i));
		});
		const h = $("effort_lines_json");
		if (h) h.value = state.lines.length ? JSON.stringify({ rates: state.rates, lines: state.lines }) : "";
		if (typeof window.updateGrandTotal === "function") window.updateGrandTotal();
		if (typeof window.updateTotalProfitPreview === "function") window.updateTotalProfitPreview({ applyDiscount: false });
	}

	// ---------------- 操作 ----------------
	function commitEdit(i) {
		const ln = state.lines[i];
		const hours = parseFloat(($("sim_edit_hours") || {}).value);
		const reasonEl = $("sim_edit_reason");
		const err = $("sim_edit_err");
		if (!(hours >= 0) || hours > 9999) { err.textContent = "時間は0〜9999で入力してください"; return; }
		const needReason = ln.source === "sim" && ln.orig_hours != null;
		const reason = reasonEl ? reasonEl.value.trim() : "";
		if (needReason && Math.abs(hours - Number(ln.orig_hours)) > 1e-9 && !reason) {
			err.textContent = "元の値から変更する場合は理由を入力してください";
			return;
		}
		ln.hours = hours;
		ln.reason = needReason && Math.abs(hours - Number(ln.orig_hours)) > 1e-9 ? reason : "";
		state.editing = -1;
		render();
	}

	function addDirect() {
		const kind = ($("sim_direct_kind") || {}).value;
		const item = (($("sim_direct_item") || {}).value || "").trim();
		const hours = parseFloat(($("sim_direct_hours") || {}).value);
		if (!item) { setMsg("項目名を入力してください", "error"); return; }
		if (!(hours >= 0) || hours > 9999) { setMsg("時間は0〜9999で入力してください", "error"); return; }
		if (!state.rates.sell) loadDefaultRates();
		state.lines.push({ kind, item_id: "", item, hours, basis: "", orig_hours: null, reason: "", source: "direct" });
		$("sim_direct_item").value = "";
		$("sim_direct_hours").value = "";
		setMsg(`追加しました: ${KIND_LABEL[kind]} ${esc(item)} ${hours}h`, "info");
		render();
	}

	function loadDefaultRates() {
		try {
			const s = JSON.parse(($("v2-settings-json") || {}).textContent || "{}");
			state.rates = { cost: Number(s.costHourlyRate || 0), sell: Number(s.sellHourlyRate || 0) };
		} catch (e) { /* 賃率が取れない場合は取り込み時のサーバー値を使う */ }
	}

	async function onApply() {
		const ta = $("sim_import_text");
		setMsg("検証中…", "info");
		let res, data;
		try {
			res = await fetch("/quotation/sim-import/preview", {
				method: "POST", headers: { "Content-Type": "text/plain; charset=utf-8" },
				body: ta ? ta.value : "", credentials: "same-origin",
			});
			data = await res.json();
		} catch (e) { setMsg("通信に失敗しました。もう一度お試しください。", "error"); return; }
		if (!res.ok || !data.ok) { setMsg(esc((data && data.error) || "取り込みに失敗しました"), "error"); return; }

		// 取り込みは SIM 行を置き換える（手入力行は残す）
		const keep = state.lines.filter((l) => l.source !== "sim");
		// 取り込みは設計費・現地セットアップ費を置き換えるので、旧ウィザード由来の行は二重計上を避けて除去
		const body = $("v2-detail-body");
		if (body) body.querySelectorAll("tr:not([data-sim-line]):not(.table-warning)").forEach((tr) => tr.remove());
		state.rates = { cost: Number(data.rates.cost), sell: Number(data.rates.sell) };
		const simLines = data.lines.map((l) => ({
			kind: l.kind, item_id: l.item_id || "", item: l.item, hours: Number(l.hours), basis: l.basis || "",
			orig_hours: Number(l.hours), reason: "", source: "sim",
		}));
		state.lines = simLines.concat(keep);
		state.editing = -1;
		const hidden = $("sim_result_json");
		if (hidden) hidden.value = JSON.stringify(data.result);
		renderInfo(data.result);
		render();

		const t = data.totals;
		let html = `反映しました: 設計 ${t.design_hours}h／現地 ${t.setup_hours}h`
			+ ` <span class="text-muted">賃率 販売${yen(data.rates.sell)}円/h・原価${yen(data.rates.cost)}円/h</span>`;
		if (keep.length) html += `（手入力 ${keep.length}件は残しています）`;
		if (data.warnings && data.warnings.length) html += "<br>" + data.warnings.map((w) => "⚠ " + esc(w)).join("<br>");
		setMsg(html, data.warnings && data.warnings.length ? "warn" : "info");
		if (ta) ta.value = "";
	}

	function onTableClick(e) {
		const b = e.target.closest("[data-sim-act]");
		if (!b) return;
		e.preventDefault();
		const act = b.getAttribute("data-sim-act");
		const i = parseInt(b.getAttribute("data-i"), 10);
		if (act === "adjust") { state.editing = i; render(); }
		else if (act === "cancel") { state.editing = -1; render(); }
		else if (act === "commit") commitEdit(i);
		else if (act === "remove") { state.lines.splice(i, 1); state.editing = -1; render(); }
	}

	function init() {
		loadDefaultRates();
		const apply = $("sim_import_apply");
		if (apply && !apply.__bound) { apply.__bound = true; apply.addEventListener("click", (e) => { e.preventDefault(); onApply(); }); }
		const add = $("sim_direct_add");
		if (add && !add.__bound) { add.__bound = true; add.addEventListener("click", (e) => { e.preventDefault(); addDirect(); }); }
		const body = $("v2-detail-body");
		if (body && !body.__simBound) { body.__simBound = true; body.addEventListener("click", onTableClick); }

		// 編集・改訂時: 保存済みの取り込み情報と工数明細を復元（保存時の賃率を使う）
		const sim = $("sim_result_json");
		if (sim && sim.value) {
			try { renderInfo(JSON.parse(sim.value)); } catch (e) { console.warn("[sim_import] stored sim json parse failed", e); }
		}
		const el = $("effort_lines_json");
		if (el && el.value) {
			try {
				const d = JSON.parse(el.value);
				if (Array.isArray(d.lines) && d.lines.length) {
					if (d.rates && d.rates.sell) state.rates = { cost: Number(d.rates.cost), sell: Number(d.rates.sell) };
					state.lines = d.lines;
					// サーバーが描画した同内容の行は取り除き、保存済み工数明細から描き直す（二重計上防止）
					const body0 = $("v2-detail-body");
					if (body0) body0.innerHTML = "";
					render();
				}
			} catch (e) { console.warn("[sim_import] stored lines parse failed", e); }
		}
	}

	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
	else init();
})();
