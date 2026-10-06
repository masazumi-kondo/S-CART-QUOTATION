import json
import os
import tempfile

import pytest

from app import sim_import

SAMPLE = {
    "schema": "scart-sim-result/1",
    "sim_project": "Test03",
    "sim_version": "2.9.8",
    "generated_at": "2026-10-06T09:00:00",
    "vehicles": {"model": "S-CART-V500", "count": 4, "spec_text": "自動充電あり／リフタ移載"},
    "layout": {"total_distance_m": 120.5, "intersection_patterns": 18},
    "performance": {"ct_s": 95.2, "throughput_per_h": 150},
    "notes": "机上条件での概算",
    "effort": {
        "design": [
            {"id": "D1", "item": "コース・ノードリンク設計", "hours": 5, "basis": "ノード13/リンク17"},
            {"id": "D3", "item": "交差点・排他ロジック作成", "hours": 5.5, "basis": "P=18"},
        ],
        "setup": [
            {"id": "S1", "item": "実機マッピング・コース登録", "hours": 8, "basis": "1枚"},
            {"id": "S8", "item": "現場デッドロック検証試験", "hours": 0, "basis": "なし"},
        ],
    },
}


def test_parse_ok():
    result, warnings = sim_import.parse_sim_result(json.dumps(SAMPLE, ensure_ascii=False))
    assert result["vehicles"]["count"] == 4
    assert len(result["effort"]["design"]) == 2
    assert warnings == []


@pytest.mark.parametrize("mutate,msg", [
    (lambda d: d.update(schema="other/9"), "スキーマ"),
    (lambda d: d["effort"]["design"][0].update(hours="abc"), "数値"),
    (lambda d: d["effort"]["design"][0].update(hours=-1), "0以上"),
    (lambda d: d["effort"]["design"][0].update(item=""), "項目名"),
    (lambda d: d.update(effort={"design": [], "setup": []}), "1件もありません"),
    (lambda d: d.pop("effort"), "effort"),
])
def test_parse_rejects(mutate, msg):
    d = json.loads(json.dumps(SAMPLE))
    mutate(d)
    with pytest.raises(sim_import.SimImportError) as e:
        sim_import.parse_sim_result(json.dumps(d))
    assert msg in str(e.value)


def test_parse_rejects_non_json_and_empty():
    for bad in ("", "   ", "not json", "[1,2]"):
        with pytest.raises(sim_import.SimImportError):
            sim_import.parse_sim_result(bad)


def test_build_lines_and_totals():
    result, _ = sim_import.parse_sim_result(json.dumps(SAMPLE))
    lines = sim_import.build_effort_lines(result, cost_rate=6820, sell_rate=12000)
    assert len(lines) == 3  # 0h の行は出さない
    d1 = lines[0]
    assert d1["price"] == 60000 and d1["cost"] == 34100
    assert d1["description"].startswith("設計費｜D1 ")
    assert d1["item"] == "コース・ノードリンク設計" and d1["item_id"] == "D1"
    assert lines[2]["description"].startswith("現地セットアップ費｜S1 ")
    t = sim_import.totals(lines)
    assert t["design_hours"] == 10.5 and t["setup_hours"] == 8
    assert t["design_price"] == 126000 and t["setup_price"] == 96000


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("SCART_DB_PATH", os.path.join(tempfile.mkdtemp(), "t.db"))
    monkeypatch.setenv("FLASK_DEBUG", "1")
    from app import create_app, db
    from app.models.product import Product
    app = create_app()
    with app.app_context():
        db.session.add(Product(name="BASE：S-CART-V500", unit_price=5000000, cost=2194361))
        db.session.commit()
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_id"] = 1  # 起動時に作られる admin
    return app, c


def test_preview_endpoint(client):
    app, c = client
    r = c.post("/quotation/sim-import/preview", data=json.dumps(SAMPLE, ensure_ascii=False).encode("utf-8"),
               content_type="text/plain; charset=utf-8")
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j["ok"] and len(j["lines"]) == 3
    assert j["rates"] == {"cost": 6820.0, "sell": 12000.0}
    assert "base_line" not in j  # 機種・台数の自動反映はしない（製品は手動選択）
    assert j["totals"]["design_price"] == 126000


def test_preview_endpoint_error_and_auth(client):
    app, c = client
    r = c.post("/quotation/sim-import/preview", data="garbage", content_type="text/plain")
    assert r.status_code == 400 and r.get_json()["ok"] is False
    anon = app.test_client()
    r2 = anon.post("/quotation/sim-import/preview", data=json.dumps(SAMPLE), content_type="text/plain")
    assert r2.status_code in (301, 302, 401, 403)  # 未ログインは通さない


def test_save_and_reload_keeps_sim_json(client):
    app, c = client
    prev = c.post("/quotation/sim-import/preview", data=json.dumps(SAMPLE).encode(), content_type="text/plain").get_json()
    form = {
        "company_name": "テスト株式会社", "project_name": "シミュ連携テスト", "save_action": "stay",
        "sim_result_json": json.dumps(prev["result"], ensure_ascii=False),
        "product_id[]": [""] * len(prev["lines"]), "code[]": [""] * len(prev["lines"]),
        "description[]": [ln["description"] for ln in prev["lines"]],
        "unit_price[]": [str(ln["price"]) for ln in prev["lines"]],
        "quantity[]": ["1"] * len(prev["lines"]),
        "subtotal[]": [str(ln["price"]) for ln in prev["lines"]],
        "cost[]": [str(ln["cost"]) for ln in prev["lines"]],
    }
    r = c.post("/quotation/new", data=form)
    assert r.status_code == 302, r.get_data(as_text=True)[:500]
    from app.models.quotation import Quotation
    with app.app_context():
        q = Quotation.query.filter_by(project_name="シミュ連携テスト").one()
        saved = json.loads(q.v2_input_json)
        assert saved["source"] == "simulator" and saved["sim"]["sim_project"] == "Test03"
        assert round(sum(d.subtotal for d in q.details)) == 126000 + 96000
        qid = q.id
    page = c.get(f"/quotation/{qid}/edit").get_data(as_text=True)
    assert 'id="sim_result_json"' in page and "Test03" in page


# ---------------- 工数行の調整・手入力・前提表示 ----------------
def _lines_payload(lines, rates=None):
    return json.dumps({"rates": rates or {"cost": 6820, "sell": 12000}, "lines": lines}, ensure_ascii=False)


def _sim_line(**kw):
    base = {"kind": "design", "item_id": "D1", "item": "コース・ノードリンク設計", "hours": 5, "basis": "",
            "orig_hours": 5, "reason": "", "source": "sim"}
    base.update(kw)
    return base


def test_validate_lines_override_requires_reason():
    data, err = sim_import.validate_effort_lines(_lines_payload([_sim_line(hours=6)]))
    assert data is None and "理由" in err
    data, err = sim_import.validate_effort_lines(_lines_payload([_sim_line(hours=6, reason="特殊な床面")]))
    assert err is None and data["lines"][0]["reason"] == "特殊な床面" and data["lines"][0]["orig_hours"] == 5


def test_validate_lines_unchanged_drops_reason_and_direct_needs_none():
    data, err = sim_import.validate_effort_lines(_lines_payload([
        _sim_line(reason="不要な理由"),
        {"kind": "setup", "item": "特注治具の調整", "hours": 3, "source": "direct", "reason": "x", "orig_hours": 1},
    ]))
    assert err is None
    assert data["lines"][0]["reason"] == ""
    assert data["lines"][1]["source"] == "direct" and data["lines"][1]["orig_hours"] is None


@pytest.mark.parametrize("bad", [
    {"kind": "x", "item": "a", "hours": 1},
    {"kind": "design", "item": "", "hours": 1},
    {"kind": "design", "item": "a", "hours": -1},
    {"kind": "design", "item": "a", "hours": "zz"},
    {"kind": "design", "item": "a", "hours": 10000},
])
def test_validate_lines_rejects_bad(bad):
    data, err = sim_import.validate_effort_lines(_lines_payload([bad]))
    assert data is None and err


def test_validate_lines_empty_and_broken():
    assert sim_import.validate_effort_lines("") == (None, None)
    assert sim_import.validate_effort_lines("{broken")[1]


def test_premise_lines_excludes_money_and_reason():
    raw = json.dumps({"source": "simulator", "sim": json.loads(json.dumps(SAMPLE))})
    out = sim_import.premise_lines(raw)
    text = "\n".join(out)
    assert "Test03" in text and "S-CART-V500" in text and "自動充電あり" in text and "概算" in text
    assert "円" not in text
    assert sim_import.premise_lines(None) == [] and sim_import.premise_lines('{"source":"manual"}') == []


def _post_quote(c, name, lines, sim=None):
    form = {
        "company_name": "テスト株式会社", "project_name": name, "save_action": "stay",
        "effort_lines_json": _lines_payload(lines),
        "product_id[]": [""] * len(lines), "code[]": [""] * len(lines),
        "description[]": [f"設計費｜{l['item']}" for l in lines],
        "unit_price[]": [str(int(l["hours"] * 12000)) for l in lines],
        "quantity[]": ["1"] * len(lines),
        "subtotal[]": [str(int(l["hours"] * 12000)) for l in lines],
        "cost[]": [str(int(l["hours"] * 6820)) for l in lines],
    }
    if sim:
        form["sim_result_json"] = json.dumps(sim, ensure_ascii=False)
    return c.post("/quotation/new", data=form)


def test_save_rejects_override_without_reason_and_keeps_with_reason(client):
    app, c = client
    r = _post_quote(c, "理由なし", [_sim_line(hours=6)])
    assert r.status_code == 200 and "理由" in r.get_data(as_text=True)  # 保存されずフォームに戻る
    from app.models.quotation import Quotation
    with app.app_context():
        assert Quotation.query.filter_by(project_name="理由なし").count() == 0

    r = _post_quote(c, "理由あり", [_sim_line(hours=6, reason="床面が特殊")])
    assert r.status_code == 302
    with app.app_context():
        q = Quotation.query.filter_by(project_name="理由あり").one()
        saved = json.loads(q.v2_input_json)
        assert saved["source"] == "manual"  # sim無しで工数行のみ → manual
        ln = saved["lines"][0]
        assert ln["hours"] == 6 and ln["orig_hours"] == 5 and ln["reason"] == "床面が特殊"
        assert saved["rates"] == {"cost": 6820.0, "sell": 12000.0}
        qid = q.id
    page = c.get(f"/quotation/{qid}/edit").get_data(as_text=True)
    assert 'id="effort_lines_json"' in page and "床面が特殊" in page


def test_premise_shown_in_print_view_and_pdf_but_not_reason(client):
    app, c = client
    r = _post_quote(c, "前提表示", [_sim_line(hours=6, reason="社外秘の理由")], sim=SAMPLE)
    assert r.status_code == 302
    from app.models.quotation import Quotation
    with app.app_context():
        qid = Quotation.query.filter_by(project_name="前提表示").one().id
    html = c.get(f"/quotation/{qid}/print").get_data(as_text=True)
    assert "シミュレーション前提" in html and "Test03" in html
    assert "社外秘の理由" not in html  # 顧客向け書面に調整理由は出さない
    pdf = c.get(f"/quotation/{qid}/pdf")
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"


def test_aggregate_effort_details_merges_only_import_lines():
    from types import SimpleNamespace as NS
    rows = [
        NS(id=1, description="BASE：S-CART-V500", label=None, subtotal=5_000_000, cost=2_000_000),
        NS(id=2, description="設計費｜D1 コース設計（5h）", label=None, subtotal=60000, cost=34100),
        NS(id=3, description="設計費｜D3 排他ロジック（5.5h）", label=None, subtotal=66000, cost=37510),
        NS(id=4, description="現地セットアップ費｜S1 マッピング（8h）", label=None, subtotal=96000, cost=54560),
        NS(id=5, description="設計費（V2自動算出）", label=None, subtotal=1000, cost=500),  # 旧ウィザード行は触らない
    ]
    out = sim_import.aggregate_effort_details(rows)
    assert [getattr(r, "description") for r in out] == ["BASE：S-CART-V500", "設計費", "現地セットアップ費", "設計費（V2自動算出）"]
    assert out[1].subtotal == 126000 and out[1].quantity == 1 and out[1].price == 126000
    assert out[2].subtotal == 96000
    assert sum(r.subtotal for r in out) == sum(r.subtotal for r in rows)  # 合計は不変


def test_print_view_aggregates_and_shows_names(client):
    app, c = client
    lines = [_sim_line(hours=5), _sim_line(item_id="D3", item="排他ロジック", hours=5.5, orig_hours=5.5),
             _sim_line(kind="setup", item_id="S1", item="マッピング", hours=8, orig_hours=8)]
    form_lines = [dict(l) for l in lines]
    r = _post_quote(c, "集約確認", form_lines, sim=SAMPLE)
    assert r.status_code == 302
    from app.models.quotation import Quotation
    with app.app_context():
        qid = Quotation.query.filter_by(project_name="集約確認").one().id
    html = c.get(f"/quotation/{qid}/print").get_data(as_text=True)
    assert "コース・ノードリンク設計" not in html  # 項目別の内訳は書面に出さない
    assert ">設計費<" in html
    pdf = c.get(f"/quotation/{qid}/pdf")
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"
