// 起動・バインドのみ（100行以内目標）
// 依存: 他のjsを先に読み込むこと


// ---- V2 boot (run after all defer scripts loaded) ----
(function () {
	function bootV2() {
		console.log("[V2_BOOT] start",
			"has __v2=", !!window.__v2,
			"initV2WizardBindings=", typeof window.initV2WizardBindings,
			"initV2LiveSummaryBindings=", typeof window.initV2LiveSummaryBindings,
			"v2UpdateLiveSummary=", typeof window.v2UpdateLiveSummary
		);

		try { window.initDetailsTableBindings?.(); } catch (e) { console.warn("[V2_BOOT] initDetailsTableBindings failed", e); }
		try { window.initV2WizardBindings?.(); } catch (e) { console.warn("[V2_BOOT] initV2WizardBindings failed", e); }
		try { window.initV2LiveSummaryBindings?.(); } catch (e) { console.warn("[V2_BOOT] initV2LiveSummaryBindings failed", e); }
		try { window.v2UpdateLiveSummary?.(); } catch (e) { console.warn("[V2_BOOT] v2UpdateLiveSummary failed", e); }

		console.log("[V2_BOOT] done");
	}

	// defer scripts run before DOMContentLoaded; either is fine
	if (document.readyState === "loading") {
		window.addEventListener("load", bootV2, { once: true });
	} else {
		bootV2();
	}
})();
