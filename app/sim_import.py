"""シミュレーター結果（クリップボードJSON）の検証と、見積明細行への換算。

方針: 工数・仕様はシミュレーターだけが算出する。このモジュールは工数(h)に賃率を掛けるだけで、
係数計算は行わない。シミュレーターは金額を持たず、金額換算は見積アプリ側のみで行う。

契約 schema "scart-sim-result/1" の概要:
{
  "schema": "scart-sim-result/1", "sim_project": str, "sim_version": str, "generated_at": str,
  "vehicles": {"model": "S-CART-V500", "count": 4, "spec_text": "文章（自動連携しない）"},
  "layout": {...任意の数値...},
  "effort": {"design": [{"id","item","hours","basis"}...], "setup": [...]},
  "performance": {"ct_s": 0, "throughput_per_h": 0}, "notes": str
}
"""
import json

SCHEMA = "scart-sim-result/1"
MAX_ITEMS = 60  # 想定外に巨大なJSONを弾く

DESIGN_PREFIX = "設計費"                 # routes.quotation.is_design_fee_line が判定に使う語
SETUP_PREFIX = "現地セットアップ費"       # 同 is_setup_fee_line


class SimImportError(ValueError):
    """取り込みできない入力（メッセージはそのまま画面に出す）"""


def _num(v, label):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise SimImportError(f"{label} が数値ではありません: {v!r}")
    if x != x or x in (float("inf"), float("-inf")):
        raise SimImportError(f"{label} が不正な数値です")
    if x < 0:
        raise SimImportError(f"{label} は0以上にしてください: {x}")
    return x


def parse_sim_result(text):
    """JSON文字列 → 正規化dict。不正なら SimImportError。 (result, warnings) を返す。"""
    if not text or not str(text).strip():
        raise SimImportError("貼り付け内容が空です")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SimImportError(f"JSONとして読み取れません: {e.msg}（{e.lineno}行目）")
    if not isinstance(data, dict):
        raise SimImportError("JSONのトップはオブジェクトである必要があります")

    schema = data.get("schema")
    if schema != SCHEMA:
        raise SimImportError(f"対応していないスキーマです: {schema!r}（対応: {SCHEMA}）")

    warnings = []
    effort = data.get("effort")
    if not isinstance(effort, dict):
        raise SimImportError("effort（工数明細）がありません")

    items = {"design": [], "setup": []}
    for kind in ("design", "setup"):
        rows = effort.get(kind) or []
        if not isinstance(rows, list):
            raise SimImportError(f"effort.{kind} は配列である必要があります")
        for i, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                raise SimImportError(f"effort.{kind}[{i}] はオブジェクトである必要があります")
            name = str(row.get("item") or "").strip()
            if not name:
                raise SimImportError(f"effort.{kind}[{i}] の item（項目名）が空です")
            hours = _num(row.get("hours"), f"effort.{kind}[{i}].hours")
            items[kind].append({
                "id": str(row.get("id") or "").strip(),
                "item": name,
                "hours": hours,
                "basis": str(row.get("basis") or "").strip(),
            })
    if len(items["design"]) + len(items["setup"]) > MAX_ITEMS:
        raise SimImportError(f"工数明細が多すぎます（最大{MAX_ITEMS}件）")
    if not items["design"] and not items["setup"]:
        raise SimImportError("工数明細が1件もありません")

    veh = data.get("vehicles") if isinstance(data.get("vehicles"), dict) else {}
    count = None
    if veh.get("count") not in (None, ""):
        count = int(_num(veh.get("count"), "vehicles.count"))
    result = {
        "schema": SCHEMA,
        "sim_project": str(data.get("sim_project") or "").strip(),
        "sim_version": str(data.get("sim_version") or "").strip(),
        "generated_at": str(data.get("generated_at") or "").strip(),
        "vehicles": {
            "model": str(veh.get("model") or "").strip(),
            "count": count,
            "spec_text": str(veh.get("spec_text") or "").strip(),
        },
        "layout": data.get("layout") if isinstance(data.get("layout"), dict) else {},
        "performance": data.get("performance") if isinstance(data.get("performance"), dict) else {},
        "notes": str(data.get("notes") or "").strip(),
        "effort": items,
    }
    if not result["sim_project"]:
        warnings.append("sim_project（シミュレーション案件名）がありません")
    return result, warnings


def _line_description(prefix, row):
    label = f'{row["id"]} {row["item"]}'.strip()
    return f'{prefix}｜{label}（{row["hours"]:g}h）'


def build_effort_lines(result, cost_rate, sell_rate):
    """工数明細 → 見積明細行。既存のV2固定行と同じ形式（数量1、金額・原価は合計）。

    数量は整数に丸められて保存されるため、時間は数量に入れず説明文に含める。
    """
    lines = []
    for kind, prefix in (("design", DESIGN_PREFIX), ("setup", SETUP_PREFIX)):
        for row in result["effort"][kind]:
            if row["hours"] <= 0:
                continue
            lines.append({
                "kind": kind,
                "item_id": row["id"],
                "item": row["item"],
                "description": _line_description(prefix, row),
                "hours": row["hours"],
                "basis": row["basis"],
                "price": int(round(row["hours"] * sell_rate)),
                "cost": int(round(row["hours"] * cost_rate)),
            })
    return lines


def totals(lines):
    t = {"design_hours": 0.0, "setup_hours": 0.0, "design_price": 0, "setup_price": 0,
         "design_cost": 0, "setup_cost": 0}
    for ln in lines:
        k = ln["kind"]
        t[f"{k}_hours"] += ln["hours"]
        t[f"{k}_price"] += ln["price"]
        t[f"{k}_cost"] += ln["cost"]
    return t


# ---------------------------------------------------------------
# 工数行（取り込み＋手入力＋理由付き調整）の検証・保存形式
# ---------------------------------------------------------------
MAX_LINES = 80
MAX_HOURS = 9999.0


def validate_effort_lines(raw):
    """フォームの effort_lines_json（{"rates":{cost,sell},"lines":[...]}）を検証して正規化する。

    戻り値: (data or None, error or None)。raw が空なら (None, None)。
    ルール: sim由来の行は元の値(orig_hours)から変えたら理由が必須。手入力(direct)行は理由不要。
    """
    if not raw or not str(raw).strip():
        return None, None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, "工数明細のデータが壊れています。画面を開き直してください"
    if not isinstance(data, dict) or not isinstance(data.get("lines"), list):
        return None, "工数明細のデータ形式が不正です"
    if len(data["lines"]) > MAX_LINES:
        return None, f"工数明細が多すぎます（最大{MAX_LINES}件）"

    rates = data.get("rates") if isinstance(data.get("rates"), dict) else {}
    try:
        rates = {"cost": float(rates.get("cost", 0)), "sell": float(rates.get("sell", 0))}
    except (TypeError, ValueError):
        return None, "賃率が不正です"

    lines = []
    for i, ln in enumerate(data["lines"], 1):
        if not isinstance(ln, dict):
            return None, f"工数明細{i}行目の形式が不正です"
        kind = ln.get("kind")
        if kind not in ("design", "setup"):
            return None, f"工数明細{i}行目の区分が不正です"
        item = str(ln.get("item") or "").strip()
        if not item or len(item) > 80:
            return None, f"工数明細{i}行目の項目名を入力してください（80文字以内）"
        try:
            hours = float(ln.get("hours"))
        except (TypeError, ValueError):
            return None, f"工数明細{i}行目（{item}）の時間が数値ではありません"
        if not (0 <= hours <= MAX_HOURS) or hours != hours:
            return None, f"工数明細{i}行目（{item}）の時間は0〜{MAX_HOURS:g}で入力してください"
        source = "sim" if ln.get("source") == "sim" else "direct"
        orig = ln.get("orig_hours")
        reason = str(ln.get("reason") or "").strip()
        if source == "sim" and orig is not None:
            try:
                orig = float(orig)
            except (TypeError, ValueError):
                return None, f"工数明細{i}行目（{item}）の元の値が不正です"
            if abs(hours - orig) > 1e-9:
                if not reason:
                    return None, f"工数明細{i}行目（{item}）: 元の値({orig:g}h)から変更する場合は理由が必要です"
            else:
                reason = ""
        else:
            orig = None
            reason = ""
        lines.append({
            "kind": kind, "item_id": str(ln.get("item_id") or "").strip(), "item": item,
            "hours": hours, "basis": str(ln.get("basis") or "").strip(),
            "orig_hours": orig, "reason": reason, "source": source,
        })
    return {"rates": rates, "lines": lines}, None


def load_v2_input(raw):
    """保存済み v2_input_json を dict で返す（壊れていれば空dict）。"""
    if not raw:
        return {}
    try:
        d = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return d if isinstance(d, dict) else {}


def premise_lines(raw_v2_input):
    """見積書に載せる『シミュレーション前提』の行（無ければ空リスト）。金額・調整理由は含めない。"""
    d = load_v2_input(raw_v2_input)
    sim = d.get("sim") if isinstance(d.get("sim"), dict) else None
    if not sim:
        return []
    out = ["【シミュレーション前提】本見積はシミュレーション結果に基づく概算です。"]
    head = []
    if sim.get("sim_project"):
        head.append(f'案件: {sim["sim_project"]}')
    veh = sim.get("vehicles") or {}
    if veh.get("model") or veh.get("count"):
        head.append(f'{veh.get("model") or ""} × {veh.get("count") if veh.get("count") is not None else "-"}台'.strip())
    if head:
        out.append(" / ".join(head))
    if veh.get("spec_text"):
        out.extend(str(veh["spec_text"]).splitlines())
    perf = sim.get("performance") or {}
    if perf.get("ct_s") is not None or perf.get("throughput_per_h") is not None:
        out.append(f'CT {perf.get("ct_s", "-")}秒 / 処理量 {perf.get("throughput_per_h", "-")}回/h')
    if sim.get("notes"):
        out.extend(str(sim["notes"]).splitlines())
    return [s for s in (x.strip() for x in out) if s]


def aggregate_effort_details(details):
    """お客様向け書面（印刷・PDF）用: 取り込み由来の項目別工数行を『設計費』『現地セットアップ費』の2行にまとめる。

    項目別の工数・根拠は社内画面にのみ出す。書面の行数（15行）を超えて明細が欠けるのも防ぐ。
    取り込み行は『設計費｜…』『現地セットアップ費｜…』の形式で判定するので、旧ウィザードの行は変更しない。
    """
    from types import SimpleNamespace

    out, agg = [], {}
    for d in details:
        desc = (getattr(d, "description", None) or getattr(d, "label", None) or "").strip()
        if desc.startswith(DESIGN_PREFIX + "｜"):
            key, name = "design", DESIGN_PREFIX
        elif desc.startswith(SETUP_PREFIX + "｜"):
            key, name = "setup", SETUP_PREFIX
        else:
            out.append(d)
            continue
        a = agg.get(key)
        if a is None:
            a = SimpleNamespace(id=getattr(d, "id", 0), product=None, product_id=None, label=name,
                                description=name, quantity=1, price=0, subtotal=0, cost=0, unit="式")
            agg[key] = a
            out.append(a)
        sub = int(round(getattr(d, "subtotal", 0) or 0))
        a.price += sub
        a.subtotal += sub
        a.cost += int(round(getattr(d, "cost", 0) or 0))
    return out
