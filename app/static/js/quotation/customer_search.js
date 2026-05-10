(function () {
  function readJson(id, fallback) {
    const el = document.getElementById(id);
    if (!el) return fallback;
    try {
      return JSON.parse(el.textContent || "null") || fallback;
    } catch (e) {
      console.error("[customer_search] JSON parse failed:", id, e);
      return fallback;
    }
  }

  function normalize(s) {
    return String(s || "")
      .toLowerCase()
      .replace(/\s+/g, "")
      .trim();
  }

  function setupCustomerSearch() {
    const input = document.getElementById("customer_search");
    const hidden = document.getElementById("customer_id");
    const box = document.getElementById("customer_candidates");
    const selectedLabel = document.getElementById("customer_selected_label");
    const selectedName = document.getElementById("customer_selected_name");
    const paymentTerms = document.getElementById("payment_terms");

    if (!input || !hidden || !box) return;

    const customers = readJson("customers-json", []);
    const meta = readJson("customers-meta-json", {});

    function hideCandidates() {
      box.classList.add("d-none");
      box.innerHTML = "";
    }

    function showSelected(name) {
      if (!selectedLabel || !selectedName) return;
      if (name) {
        selectedName.textContent = name;
        selectedLabel.classList.remove("d-none");
      } else {
        selectedName.textContent = "";
        selectedLabel.classList.add("d-none");
      }
    }

    function applyCustomer(c) {
      if (!c) return;

      hidden.value = c.id || "";
      input.value = c.name || "";

      const m = meta[String(c.id)] || {};
      if (paymentTerms) {
        paymentTerms.value =
          m.payment_term_name ||
          m.payment_terms_legacy ||
          paymentTerms.value ||
          "";
      }

      showSelected(c.name || "");
      hideCandidates();
    }

    function renderCandidates(keyword) {
      const q = normalize(keyword);

      if (q.length < 2) {
        hideCandidates();
        return;
      }

      const matched = customers
        .filter(c => {
          const name = normalize(c.name);
          const kana = normalize(c.name_kana);
          return name.includes(q) || kana.includes(q);
        })
        .slice(0, 20);

      if (matched.length === 0) {
        box.innerHTML = `
          <div class="list-group-item text-muted small">
            該当する顧客がありません。手入力で保存できます。
          </div>
        `;
        box.classList.remove("d-none");
        return;
      }

      box.innerHTML = matched.map(c => {
        const kana = c.name_kana ? `<div class="small text-muted">${c.name_kana}</div>` : "";
        return `
          <button type="button"
                  class="list-group-item list-group-item-action customer-candidate"
                  data-customer-id="${c.id}">
            <div class="fw-bold">${c.name || ""}</div>
            ${kana}
          </button>
        `;
      }).join("");

      box.classList.remove("d-none");
    }

    input.addEventListener("input", () => {
      hidden.value = "";
      showSelected("");
      renderCandidates(input.value);
    });

    input.addEventListener("focus", () => {
      renderCandidates(input.value);
    });

    box.addEventListener("click", e => {
      const btn = e.target.closest(".customer-candidate");
      if (!btn) return;

      const id = btn.dataset.customerId;
      const c = customers.find(x => String(x.id) === String(id));
      applyCustomer(c);
    });

    document.addEventListener("click", e => {
      if (e.target === input || box.contains(e.target)) return;
      hideCandidates();
    });

    // 初期表示時、customer_idが既にある場合は選択済み表示
    if (hidden.value) {
      const c = customers.find(x => String(x.id) === String(hidden.value));
      if (c) showSelected(c.name || input.value);
    }
  }

  document.addEventListener("DOMContentLoaded", setupCustomerSearch);
})();
