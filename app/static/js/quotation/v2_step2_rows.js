// app/static/js/quotation/v2_step2_rows.js
// Step2 テンプレごと行追加・削除UIロジック
(function(){
  if(window.__v2Step2RowsLoaded) return;
  window.__v2Step2RowsLoaded = true;

  function makeRow(tidx, rowIndex) {
    const tr = document.createElement('tr');
    tr.setAttribute('data-row-index', rowIndex);
    tr.innerHTML = `
      <td class="align-middle"><span class="v2-route-id">T${tidx}-${rowIndex}</span></td>
      <td><input type="number" class="form-control form-control-sm" id="v2_vehicle_T${tidx}_${rowIndex}" name="v2_vehicle_T${tidx}[]" min="0" step="1" value="0"></td>
      <td><input type="number" class="form-control form-control-sm" id="v2_station_T${tidx}_${rowIndex}" name="v2_station_T${tidx}[]" min="0" step="1" value="0"></td>
      <td><input type="number" class="form-control form-control-sm" id="v2_short_T${tidx}_${rowIndex}" name="v2_short_T${tidx}[]" min="0" step="0.1" value="0"></td>
      <td><input type="number" class="form-control form-control-sm" id="v2_long_T${tidx}_${rowIndex}" name="v2_long_T${tidx}[]" min="0" step="0.1" value="0"></td>
      <td><input type="number" class="form-control form-control-sm" id="v2_wait_T${tidx}_${rowIndex}" name="v2_wait_T${tidx}[]" min="0" step="1" value="0"></td>
      <td><input type="text" class="form-control form-control-sm" id="v2_memo_T${tidx}_${rowIndex}" name="v2_memo_T${tidx}[]" placeholder="例：搬送A→B、充電、待機など"></td>
      <td></td>
    `;
    return tr;
  }

  function renumberRows(tidx) {
    const tbody = document.getElementById(`v2_step2_tbody_T${tidx}`);
    if (!tbody) return;
    Array.from(tbody.querySelectorAll('tr')).forEach((tr, i) => {
      const rowIndex = i + 1;
      tr.setAttribute('data-row-index', rowIndex);
      const routeIdSpan = tr.querySelector('.v2-route-id');
      if(routeIdSpan) routeIdSpan.textContent = `T${tidx}-${rowIndex}`;
      // update all input IDs
      const vehicle = tr.querySelector('input[id^="v2_vehicle_T"]');
      const station = tr.querySelector('input[id^="v2_station_T"]');
      const short = tr.querySelector('input[id^="v2_short_T"]');
      const long = tr.querySelector('input[id^="v2_long_T"]');
      const memo = tr.querySelector('input[id^="v2_memo_T"]');
      if(vehicle) vehicle.id = `v2_vehicle_T${tidx}_${rowIndex}`;
      if(station) station.id = `v2_station_T${tidx}_${rowIndex}`;
      if(short) short.id = `v2_short_T${tidx}_${rowIndex}`;
      if(long) long.id = `v2_long_T${tidx}_${rowIndex}`;
      if(memo) memo.id = `v2_memo_T${tidx}_${rowIndex}`;
    });
  }

  function onAddRow(e) {
    const tidx = e.target.getAttribute('data-tidx');
    const tbody = document.getElementById(`v2_step2_tbody_T${tidx}`);
    if (!tbody) return;
    const rowIndex = tbody.querySelectorAll('tr').length + 1;
    tbody.appendChild(makeRow(tidx, rowIndex));
    renumberRows(tidx);
  }

  function onRemoveRow(e) {
    const tidx = e.target.getAttribute('data-tidx');
    const tbody = document.getElementById(`v2_step2_tbody_T${tidx}`);
    if (!tbody) return;
    const trs = tbody.querySelectorAll('tr');
    if (trs.length <= 1) return; // 最低1行は残す
    tbody.removeChild(trs[trs.length - 1]);
    renumberRows(tidx);
  }

  function bindStep2() {
    for(let i=1;i<=6;i++){
      // カードヘッダの＋/−ボタン
      document.querySelectorAll(`.v2-step2-add[data-tidx="${i}"]`).forEach(btn => {
        btn.addEventListener('click', onAddRow);
      });
      document.querySelectorAll(`.v2-step2-remove[data-tidx="${i}"]`).forEach(btn => {
        btn.addEventListener('click', onRemoveRow);
      });
      renumberRows(i);
    }
  }

  document.addEventListener('DOMContentLoaded', bindStep2);
})();
