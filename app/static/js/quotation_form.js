
// app/static/js/quotation/quotation_form.js
(function () {
  if (window.__quotationBootLoaded) return;
  window.__quotationBootLoaded = true;

  document.addEventListener("DOMContentLoaded", function () {
    console.log("[quotation_boot] DOMContentLoaded");

    // Details table bindings
    if (typeof window.initDetailsTableBindings === "function") {
      window.initDetailsTableBindings();
    }
    window.updateGrandTotal?.();

    // V2 wizard bindings (run button / step nav)
    if (typeof window.initV2WizardBindings === "function") {
      window.initV2WizardBindings();
    }

    // V2 live summary bindings
    if (typeof window.initV2LiveSummaryBindings === "function") {
      window.initV2LiveSummaryBindings();
    }
  });
})();
});

