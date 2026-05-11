def _form_bool(form, name: str) -> bool:
    v = (form.get(name) or "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")

def _form_int(form, name: str):
    v = form.get(name)
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None

def _form_float(form, name: str):
    v = form.get(name)
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def _norm_calc_mode(v: str) -> str:
    s = (v or "").strip().lower()
    # official/rough regime（旧値は official に吸収）
    if s in ("official", "new_v1", "legacy", ""):
        return "official"
    if s in ("rough", "estimate", "approx"):
        return "rough"
    return "official"

def _norm_difficulty(v: str):
    s = (v or "").strip().lower()
    return s if s in ("medium", "high") else None

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from app import db
from app.models.quotation import Quotation
from app.models.quotation_detail import QuotationDetail
from app.models.product import Product
from app.models.customer import Customer, CustomerStatus
from sqlalchemy.orm import joinedload
from datetime import datetime
from app.cost_utils import calc_design_setup_for_quotation
from sqlalchemy import func

quotation_bp = Blueprint("quotation", __name__)


# 見積No.の採番関数
def generate_quotation_no():
    """
    見積No.を採番する: Q-YYYYMMDD-連番
    例: Q-20260510-001
    """
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"Q-{today}-"

    latest = (
        Quotation.query
        .filter(Quotation.quotation_no.like(f"{prefix}%"))
        .order_by(Quotation.quotation_no.desc())
        .first()
    )

    if not latest or not latest.quotation_no:
        seq = 1
    else:
        try:
            # 最後の - 以降を取得（RXなし前提）
            parts = latest.quotation_no.split("-")
            # Q-20260510-001 の場合、parts = ['Q', '20260510', '001']
            base = parts[-1].split("R")[0]  # R付きなら除去
            seq = int(base) + 1
        except (ValueError, IndexError):
            seq = 1

    return f"{prefix}{seq:03d}"


## --- ここに quotation_revise を移動 ---

@quotation_bp.route("/quotations/<int:quotation_id>/revise", methods=["GET"])
def quotation_revise(quotation_id):
    orig = Quotation.query.get_or_404(quotation_id)
    details = QuotationDetail.query.filter_by(quotation_id=orig.id).all()
    # values: id, created_at, updated_at, original_id, revision_no を除外
    values = {c.name: getattr(orig, c.name) for c in Quotation.__table__.columns if c.name not in ("id", "created_at", "updated_at", "original_id", "revision_no")}
    # customer_idをvaluesに追加（テンプレ互換のため str に揃える）
    cust_id = getattr(orig, "customer_id", None)
    values["customer_id"] = str(cust_id) if cust_id else ""
    # customer_idがあればcompany_nameをCustomer.nameで上書き（int変換ガード、valuesから一貫して参照）
    cust_id_int = None
    try:
        cust_id_int = int(values["customer_id"]) if values["customer_id"] else None
    except Exception:
        cust_id_int = None
    if cust_id_int:
        cust = Customer.query.get(cust_id_int)
        if cust:
            values["company_name"] = cust.name

    # 顧客リスト（approvedのみ、未承認顧客は選択不可）
    customers_query = Customer.query.options(joinedload(Customer.payment_term_ref)).filter(Customer.status == CustomerStatus.APPROVED.value).order_by(Customer.name).all()
    # details: id, quotation_id, created_at, updated_at を除外
    detail_dicts = []
    for d in details:
        dct = {c.name: getattr(d, c.name) for c in QuotationDetail.__table__.columns if c.name not in ("id", "quotation_id", "created_at", "updated_at")}
        detail_dicts.append(dct)
    # product_list: 新規作成と同じ形式
    products_query = Product.query.order_by(Product.name).all()
    product_list = [
        {
            "id": p.id,
            "name": p.name,
            "unit_price": p.unit_price,
            "cost": p.cost,
            "note": p.note,
        }
        for p in products_query
    ]
    from app.cost_utils import LABOR_RATE, DESIGN_SELL_RATE, SETUP_SELL_RATE
    rates = {
        "LABOR_RATE": LABOR_RATE,
        "DESIGN_SELL_RATE": DESIGN_SELL_RATE,
        "SETUP_SELL_RATE": SETUP_SELL_RATE,
    }
    return render_template(
        "quotation_form.html",
        error=None,
        products=product_list,
        values=values,
        details=detail_dicts,
        revise_source_id=orig.id,
        rates=rates
    )

# 印刷用見積書の明細並び順ヘルパー
def sort_details_for_display(details):
    design_labels = ("設計費", "設計費（パラメータ）")
    setup_labels = ("現地セットアップ", "現地セットアップ（パラメータ）")

    normal = [
        d for d in details
        if getattr(d, "label", None) not in design_labels + setup_labels
    ]
    design = [
        d for d in details
        if getattr(d, "label", None) in design_labels
    ]
    setup = [
        d for d in details
        if getattr(d, "label", None) in setup_labels
    ]
    return normal + design + setup

@quotation_bp.route("/quotation/<int:quotation_id>/view")
def quotation_view(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    details = sort_details_for_display(quotation.details)
    # 合計金額
    if hasattr(quotation, 'total_amount') and quotation.total_amount is not None:
        total = quotation.total_amount
    else:
        total = sum([getattr(d, 'subtotal', 0) or 0 for d in details])

    # --- 新ロジックで設計/セットアップ費用計算 ---

    import json
    logger = current_app.logger
    DEFAULT_DESIGN_SETUP = {
        "design_hours": 0,
        "design_cost": 0,
        "design_fee": 0,
        "design_profit_rate": 0,
        "setup_hours": 0,
        "setup_cost": 0,
        "setup_fee": 0,
        "setup_profit_rate": 0,
    }
    def _ensure_dict_design_setup(value):
        if value is None:
            return DEFAULT_DESIGN_SETUP.copy()
        if isinstance(value, dict):
            out = DEFAULT_DESIGN_SETUP.copy()
            out.update(value)
            return out
        if isinstance(value, (bytes, bytearray)):
            try:
                value = value.decode("utf-8", errors="ignore")
            except Exception:
                return DEFAULT_DESIGN_SETUP.copy()
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return DEFAULT_DESIGN_SETUP.copy()
            # JSONの可能性
            if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict):
                        out = DEFAULT_DESIGN_SETUP.copy()
                        out.update(obj)
                        return out
                    return DEFAULT_DESIGN_SETUP.copy()
                except Exception as e:
                    logger.warning("[quotation_view] design_setup json parse failed: %s", e)
                    return DEFAULT_DESIGN_SETUP.copy()
            # 旧形式等はここでは解釈しない（落とさない）
            return DEFAULT_DESIGN_SETUP.copy()
        # その他型
        return DEFAULT_DESIGN_SETUP.copy()


    calc_ok = False
    try:
        design_setup_raw = calc_design_setup_for_quotation(quotation)
        calc_ok = True
        logger.info(
            "[quotation_view] calc_design_setup_for_quotation return type=%s value=%r",
            type(design_setup_raw).__name__, design_setup_raw
        )
    except Exception:
        logger.exception("failed to calc design/setup amounts for quotation %s", quotation_id)
        design_setup_raw = None

    # どちらの経路でも必ずdict正規化（キー埋め）
    design_setup = _ensure_dict_design_setup(design_setup_raw)

    # フォールバック理由を判定し、発動時は理由をwarningログ
    fallback_reason = None
    if not calc_ok:
        fallback_reason = "calc_exception"
    elif design_setup_raw is None:
        fallback_reason = "raw_is_none"
    elif isinstance(design_setup_raw, dict) and not design_setup_raw:
        fallback_reason = "raw_empty_dict"
    elif isinstance(design_setup_raw, (list, tuple)) and len(design_setup_raw) == 0:
        fallback_reason = "raw_empty_list"
    elif isinstance(design_setup_raw, str) and design_setup_raw.strip().lower() in ("", "null", "none"):
        fallback_reason = "raw_empty_or_null_string"

    if fallback_reason:
        def _pick_amount(label_prefix):
            for d in details:
                if getattr(d, "label", "") == label_prefix:
                    val = getattr(d, "subtotal", None) or getattr(d, "price", None) or 0
                    try:
                        return float(val)
                    except Exception:
                        return 0
            return 0

        picked_design = _pick_amount("設計費（パラメータ）")
        picked_setup  = _pick_amount("現地セットアップ（パラメータ）")

        # 証跡ログ: 1行で全情報を出す
        logger.warning(
            "[quotation_view] fallback: qid=%s orig=%s rev=%s reason=%s raw_type=%s raw_val=%r picked_design=%s picked_setup=%s",
            getattr(quotation, "id", None),
            getattr(quotation, "original_id", None),
            getattr(quotation, "revision_no", None),
            fallback_reason,
            type(design_setup_raw).__name__,
            design_setup_raw,
            picked_design,
            picked_setup
        )

        design_setup["design_fee"] = picked_design
        design_setup["setup_fee"]  = picked_setup
        design_setup = _ensure_dict_design_setup(design_setup)

    # 値引き額と値引き後合計を計算
    discount_amount = getattr(quotation, "discount_amount", 0) or 0
    total_after_discount = max(0, total - discount_amount)

    return render_template(
        "quotation_view.html",
        quotation=quotation,
        details=details,
        total_amount=total,
        discount_amount=discount_amount,
        total_after_discount=total_after_discount,
        design_setup=design_setup,
    )


@quotation_bp.route("/quotation/<int:quotation_id>/print")
def print_view(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    details = sort_details_for_display(quotation.details)
    
    total_amount = sum((getattr(d, "subtotal", 0) or 0) for d in details)
    discount_amount = getattr(quotation, "discount_amount", 0) or 0
    total_after_discount = max(0, total_amount - discount_amount)
    
    return render_template(
        "quotation_view.html",
        quotation=quotation,
        details=details,
        total_amount=total_amount,
        discount_amount=discount_amount,
        total_after_discount=total_after_discount,
        print_mode=True
    )


# original_id/revision_noのNULL補正（必要時のみ実行、bulk update）
def normalize_revision_fields():
    needs_update = False
    if db.session.query(Quotation).filter(Quotation.original_id == None).count() > 0:
        db.session.query(Quotation).filter(Quotation.original_id == None).update({Quotation.original_id: Quotation.id}, synchronize_session=False)
        needs_update = True
    if db.session.query(Quotation).filter(Quotation.revision_no == None).count() > 0:
        db.session.query(Quotation).filter(Quotation.revision_no == None).update({Quotation.revision_no: 0}, synchronize_session=False)
        needs_update = True
    if needs_update:
        db.session.commit()

@quotation_bp.route("/quotations")
def quotation_list():
    normalize_revision_fields()
    # originals: revision_no==0のみ
    originals = Quotation.query.filter(Quotation.revision_no == 0).order_by(Quotation.created_at.desc()).all()
    # original_idごとに最新改定（DBでmaxを取得）
    orig_ids = [o.id for o in originals]
    latest_rev_map = {}
    if orig_ids:
        subq = (
            db.session.query(
                Quotation.original_id,
                func.max(Quotation.revision_no).label("max_rev")
            )
            .filter(Quotation.original_id.in_(orig_ids), Quotation.revision_no > 0)
            .group_by(Quotation.original_id)
            .subquery()
        )
        latests = (
            db.session.query(Quotation)
            .join(subq, (Quotation.original_id == subq.c.original_id) & (Quotation.revision_no == subq.c.max_rev))
            .all()
        )
        for row in latests:
            latest_rev_map[row.original_id] = row
    quotations = []
    for orig in originals:
        quotations.append(orig)
        if orig.id in latest_rev_map:
            quotations.append(latest_rev_map[orig.id])
    
    # Convert Quotation objects to dictionaries with calculated totals
    def get_total_after_discount(q):
        total_sell = sum((d.subtotal or 0) for d in q.details) if q.details else 0
        discount_amount = (q.discount_amount or 0) if q.discount_amount else 0
        return max(0, total_sell - discount_amount)
    
    quotations_data = []
    for q in quotations:
        quotations_data.append({
            'quotation_no': q.quotation_no or f"{q.original_id or q.id}-R{q.revision_no}",
            'original_id': q.original_id,
            'revision_no': q.revision_no,
            'company_name': q.company_name,
            'project_name': q.project_name,
            'created_at': q.created_at.strftime('%Y-%m-%d') if q.created_at else '',
            'total_after_discount': get_total_after_discount(q),
            'id': q.id
        })
    
    return render_template("quotation_list.html", quotations=quotations_data)


@quotation_bp.route("/quotation/new", methods=["GET", "POST"])

def quotation_new():
    import logging
    logging.info("[quotation_new] method=%s path=%s url=%s referrer=%s revise_source_id=%s", request.method, request.path, request.url, request.referrer, request.form.get("revise_source_id"))
    error = None
    # Product モデルのリストを取得し、JSONシリアライズ可能な辞書リストに変換
    products_query = Product.query.order_by(Product.name).all()
    product_list = [
        {
            "id": p.id,
            "name": p.name,
            "unit_price": p.unit_price,
            "cost": p.cost,
            "note": p.note,
        }
        for p in products_query
    ]

    # ヘッダ入力値保持用
    values = {
        "company_name": "",
        "contact_name": "",
        "project_name": "",
        "delivery_date": "",
        "delivery_terms": "",
        "payment_terms": "",
        "valid_until": "",
        "valid_days": 30,  # 見積期限（日数）
        "remarks": "",
        "estimator_name": "",  # 作成担当
        # 走行条件パラメーター入力保持用
        "distance_m": "",
        "intersection_count": "",
        "station_count": "",
        "vehicle_count": "",
        "equipment_count": "",
        "circuit_difficulty": "",
        "customer_id": "",
        "discount_rate": 0.0,
        "discount_amount": 0
    }

    # GET時: クエリパラメータから値を反映（顧客選択画面から戻ってきた場合）
    if request.method == "GET":
        values["customer_id"] = request.args.get("customer_id", "").strip()
        values["company_name"] = request.args.get("company_name", "").strip()
        values["contact_name"] = request.args.get("contact_name", "").strip()
        values["project_name"] = request.args.get("project_name", "").strip()
        values["delivery_date"] = request.args.get("delivery_date", "").strip()
        values["delivery_terms"] = request.args.get("delivery_terms", "").strip()
        values["payment_terms"] = request.args.get("payment_terms", "").strip()
        values["valid_days"] = request.args.get("valid_days", "30").strip()
        values["remarks"] = request.args.get("remarks", "").strip()
        
        # valid_days の型変換
        try:
            n = int(values["valid_days"]) if values["valid_days"] else 30
            values["valid_days"] = n if n > 0 else 30
        except ValueError:
            values["valid_days"] = 30



    if request.method == "POST":
        # ヘッダ項目取得
        values["company_name"] = request.form.get("company_name", "").strip()
        values["contact_name"] = request.form.get("contact_name", "").strip()
        values["project_name"] = request.form.get("project_name", "").strip()
        values["delivery_date"] = request.form.get("delivery_date", "").strip()
        values["delivery_terms"] = request.form.get("delivery_terms", "").strip()
        values["payment_terms"] = request.form.get("payment_terms", "").strip()
        values["valid_until"] = request.form.get("valid_until", "").strip()
        
        # 見積期限（日数）取得
        valid_days_raw = request.form.get("valid_days", "").strip()
        if valid_days_raw == "":
            values["valid_days"] = None
        else:
            try:
                n = int(valid_days_raw)
                values["valid_days"] = n if n > 0 else None
            except ValueError:
                values["valid_days"] = None
        
        values["remarks"] = request.form.get("remarks", "").strip()
        values["estimator_name"] = request.form.get("estimator_name", "").strip()
        values["customer_id"] = request.form.get("customer_id", "").strip()

        # 走行条件パラメーター取得
        values["distance_m"] = request.form.get("distance_m", "").strip()
        values["intersection_count"] = request.form.get("intersection_count", "").strip()
        values["station_count"] = request.form.get("station_count", "").strip()
        values["vehicle_count"] = request.form.get("vehicle_count", "").strip()
        values["equipment_count"] = request.form.get("equipment_count", "").strip()
        values["circuit_difficulty"] = request.form.get("circuit_difficulty", "").strip()

        # 値引率取得
        discount_rate_raw = request.form.get("discount_rate", "0").replace(",", "")
        try:
            values["discount_rate"] = float(discount_rate_raw)
        except ValueError:
            values["discount_rate"] = 0.0

        # 値引き額取得
        discount_amount_raw = request.form.get("discount_amount", "0").replace(",", "")
        try:
            values["discount_amount"] = int(float(discount_amount_raw))
        except ValueError:
            values["discount_amount"] = 0

        # --- デバッグログ追加 ---
        current_app.logger.info("quotation_new POST: product_id=%s", request.form.getlist("product_id[]"))
        current_app.logger.info("quotation_new POST: code=%s", request.form.getlist("code[]"))
        current_app.logger.info("quotation_new POST: description=%s", request.form.getlist("description[]"))
        current_app.logger.info("quotation_new POST: unit_price=%s", request.form.getlist("unit_price[]"))
        current_app.logger.info("quotation_new POST: quantity=%s", request.form.getlist("quantity[]"))
        current_app.logger.info("quotation_new POST: subtotal=%s", request.form.getlist("subtotal[]"))
        current_app.logger.info("quotation_new POST: discount_amount=%s discount_rate=%s",
            request.form.get("discount_amount"),
            request.form.get("discount_rate")
        )

        # --- 明細行の取得（新しいname属性に対応）---
        product_ids = request.form.getlist("product_id[]")
        codes = request.form.getlist("code[]")
        descs = request.form.getlist("description[]")
        unit_prices = request.form.getlist("unit_price[]")
        quantities = request.form.getlist("quantity[]")
        subtotals = request.form.getlist("subtotal[]")
        costs = request.form.getlist("cost[]")



        # --- 明細行の取得: 各配列の最大長でループし、product_idが空でも他があれば保存 ---
        details = []
        total = 0
        row_count = max(len(product_ids), len(codes), len(descs), len(unit_prices), len(quantities), len(subtotals), len(costs))
        for idx in range(row_count):
            product_id_raw = (product_ids[idx] if idx < len(product_ids) else '').strip()
            code = (codes[idx] if idx < len(codes) else '').strip()
            desc = (descs[idx] if idx < len(descs) else '').strip()
            unit_price_raw = (unit_prices[idx] if idx < len(unit_prices) else '').replace(',', '').strip()
            quantity_raw = (quantities[idx] if idx < len(quantities) else '').replace(',', '').strip()
            subtotal_raw = (subtotals[idx] if idx < len(subtotals) else '').replace(',', '').strip()
            cost_raw = (costs[idx] if idx < len(costs) else '').replace(',', '').strip()

            # 完全空行はスキップ（subtotal_rawも含めて厳密化）
            if (not product_id_raw) and (not desc) and (not unit_price_raw) and (not quantity_raw) and (not subtotal_raw):
                continue

            # 型変換
            try:
                unit_price_val = float(unit_price_raw) if unit_price_raw else 0
            except (ValueError, TypeError):
                unit_price_val = 0
            try:
                quantity_val = int(quantity_raw) if quantity_raw else 0
            except (ValueError, TypeError):
                quantity_val = 0
            try:
                cost_val = float(cost_raw) if cost_raw else 0
            except (ValueError, TypeError):
                cost_val = 0

            # subtotalの型変換（例外/空は再計算）
            try:
                subtotal_val = float(subtotal_raw) if subtotal_raw else unit_price_val * quantity_val
            except (ValueError, TypeError):
                subtotal_val = unit_price_val * quantity_val

            # (1) quantityが0/空でもsubtotal>0なら quantity=1 扱いで採用
            if quantity_val <= 0 and subtotal_val <= 0:
                continue
            if quantity_val <= 0 and subtotal_val > 0:
                quantity_val = 1

            # product_idのint変換（空ならNone）
            if product_id_raw:
                try:
                    product_id = int(product_id_raw)
                except ValueError:
                    product_id = None
            else:
                product_id = None

            # descriptionが空でproduct_idが指定されている場合はProduct.nameをセット
            if not desc and product_id is not None:
                product = Product.query.get(product_id)
                if product:
                    desc = product.name

            # QuotationDetailインスタンス生成
            detail_kwargs = dict(
                product_id=product_id,
                label=None,
                quantity=quantity_val,
                price=unit_price_val,
                subtotal=subtotal_val
            )
            if hasattr(QuotationDetail, 'code'):
                detail_kwargs['code'] = code
            if hasattr(QuotationDetail, 'description'):
                detail_kwargs['description'] = desc
            if hasattr(QuotationDetail, 'cost'):
                detail_kwargs['cost'] = cost_val

            detail = QuotationDetail(**detail_kwargs)
            details.append(detail)
            total += subtotal_val


        # --- 明細件数と内容をログ出力 ---
        current_app.logger.info("quotation_new: details count = %s", len(details))
        for d in details:
            current_app.logger.info(
                "quotation_new detail: product_id=%s, code=%s, description=%s, quantity=%s, price=%s, subtotal=%s",
                getattr(d, "product_id", None),
                getattr(d, "code", None),
                getattr(d, "description", None),
                getattr(d, "quantity", None),
                getattr(d, "price", None),
                getattr(d, "subtotal", None),
            )

        # --- 設計費/現地セットアップ費の明細が無い場合は0円で自動追加し、警告flash ---
        def _has_row(desc):
            for d in details:
                if hasattr(d, "description") and getattr(d, "description", "").strip() == desc:
                    return True
            return False
        def _make_fixed(desc_text):
            kwargs = dict(product_id=None, label=None, quantity=1, price=0, subtotal=0)
            if hasattr(QuotationDetail, "description"):
                kwargs["description"] = desc_text
            return QuotationDetail(**kwargs)
        added_fixed = False
        if not _has_row("設計費（V2自動算出）"):
            details.append(_make_fixed("設計費（V2自動算出）"))
            added_fixed = True
        if not _has_row("現地セットアップ費（V2自動算出）"):
            details.append(_make_fixed("現地セットアップ費（V2自動算出）"))
            added_fixed = True
        if added_fixed:
            flash("設計費/現地セットアップ費が明細に無かったため、0円で自動追加しました。", "warning")

        # --- 設計費・現地セットアップ費の自動計算（パラメーター優先） ---

        from app.cost_utils import calc_design_and_setup_amounts

        # パラメータ入力値をdictでまとめて渡す（new_v1拡張対応）
        param_dict = {
            "distance_m": values["distance_m"],
            "intersection_count": values["intersection_count"],
            "station_count": values["station_count"],
            "vehicle_count": values["vehicle_count"],
            "equipment_count": values["equipment_count"],
            "circuit_difficulty": values["circuit_difficulty"],
            # new_v1 fields
            "avg_entry_dirs": request.form.get("avg_entry_dirs"),
            "station_auto": request.form.get("station_auto"),
            "station_manual": request.form.get("station_manual"),
            "station_relay": request.form.get("station_relay"),
            "station_charge": request.form.get("station_charge"),
            "wait_position_count": request.form.get("wait_position_count"),
            "has_swap_operation": _form_bool(request.form, "has_swap_operation"),
            "has_plc_handshake": _form_bool(request.form, "has_plc_handshake"),
            "has_ev_integration": _form_bool(request.form, "has_ev_integration"),
            "difficulty_design": request.form.get("difficulty_design"),
            "difficulty_setup": request.form.get("difficulty_setup"),
        }

        calc_mode = _norm_calc_mode(request.form.get("calc_mode"))

        # パラメータがすべて未入力なら設計費・現地セットアップ費は追加しない（official regime: 公式入力も判定）
        has_any_param = any([
            param_dict.get("distance_m"),
            param_dict.get("intersection_count"),
            param_dict.get("station_count"),
            param_dict.get("vehicle_count"),
            param_dict.get("equipment_count"),
            param_dict.get("avg_entry_dirs"),
            param_dict.get("station_auto"),
            param_dict.get("station_manual"),
            param_dict.get("station_relay"),
            param_dict.get("station_charge"),
            param_dict.get("wait_position_count"),
            param_dict.get("has_swap_operation"),
            param_dict.get("has_plc_handshake"),
            param_dict.get("has_ev_integration"),
            param_dict.get("difficulty_design"),
            param_dict.get("difficulty_setup"),
        ])
        if not has_any_param:
            pass
        else:
            design_fee, design_cost, design_hours, setup_fee, setup_cost, setup_hours = calc_design_and_setup_amounts(param_dict, calc_mode=calc_mode)
            # 設計費
            if design_fee > 0:
                design_kwargs = dict(
                    product_id=None,
                    label="設計費（パラメータ）",
                    quantity=1,
                    price=design_fee,
                    subtotal=design_fee
                )
                if hasattr(QuotationDetail, "code"):
                    design_kwargs["code"] = ""
                if hasattr(QuotationDetail, "description"):
                    design_kwargs["description"] = "設計費（走行条件/動作パターン）"
                details.append(QuotationDetail(**design_kwargs))
                total += design_fee
            # 現地セットアップ費
            if setup_fee > 0:
                setup_kwargs = dict(
                    product_id=None,
                    label="現地セットアップ（パラメータ）",
                    quantity=1,
                    price=setup_fee,
                    subtotal=setup_fee
                )
                if hasattr(QuotationDetail, "code"):
                    setup_kwargs["code"] = ""
                if hasattr(QuotationDetail, "description"):
                    setup_kwargs["description"] = "現地セットアップ費（走行条件/動作パターン）"
                details.append(QuotationDetail(**setup_kwargs))
                total += setup_fee

        if not error and not details:
            error = "明細行が1つ以上必要です。"

        # 必須項目チェック（既存ロジック）
        if not values["company_name"] or not values["project_name"]:
            error = "「宛先企業名」と「案件名」は必須です。"


        if not error:
            revise_source_id = request.form.get("revise_source_id")
            # customer_idの整合性処理
            cust_id = values["customer_id"]
            try:
                cust_id_int = int(cust_id) if cust_id else None
            except Exception:
                cust_id_int = None
            cust_obj = Customer.query.get(cust_id_int) if cust_id_int else None

            if cust_obj:
                # 顧客IDがある場合のみ承認チェック
                if not getattr(cust_obj, "is_approved", False):
                    error = "未承認の顧客は見積作成できません。承認後に再度お試しください。"
                    current_app.logger.warning("[quotation_new] rejected unapproved customer_id=%s", cust_id_int)
                    return render_template(
                        "quotation_form.html",
                        error=error,
                        products=product_list,
                        values=values,
                        rates=rates
                    )

                # 顧客IDがある場合のみマスタ名で上書き
                values["company_name"] = cust_obj.name
            else:
                # customer_id がなくても、会社名が入力されていれば保存を許可
                cust_id_int = None
                if not values.get("company_name"):
                    error = "顧客名（宛先）を入力してください。"
                    current_app.logger.warning("[quotation_new] company_name missing")
                    return render_template(
                        "quotation_form.html",
                        error=error,
                        products=product_list,
                        values=values,
                        rates=rates
                    )

            if revise_source_id:
                # 改定保存: 系列max(revision_no)+1を採番
                src = Quotation.query.get_or_404(int(revise_source_id))
                original_id = src.original_id or src.id
                max_rev = db.session.query(func.max(Quotation.revision_no)).filter(Quotation.original_id == original_id).scalar() or 0
                revision_no = int(max_rev) + 1
                
                # 見積No.の生成（元見積をベースに -R{revision_no} を付与）
                base_quotation_no = src.quotation_no or f"{src.original_id or src.id}-R0"
                if "-R" in base_quotation_no:
                    base_quotation_no = base_quotation_no.split("-R")[0]
                revised_quotation_no = f"{base_quotation_no}-R{revision_no}"
                
                quotation = Quotation(
                    company_name=values["company_name"],
                    contact_name=values["contact_name"],
                    project_name=values["project_name"],
                    delivery_date=values["delivery_date"],
                    delivery_terms=values["delivery_terms"],
                    payment_terms=values["payment_terms"],
                    valid_until=values["valid_until"],
                    valid_days=values.get("valid_days"),  # 見積期限（日数）
                    remarks=values["remarks"],
                    estimator_name=values.get("estimator_name", ""),
                    discount_rate=values.get("discount_rate", 0.0),
                    discount_amount=values.get("discount_amount", 0),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    original_id=original_id,
                    revision_no=revision_no,
                    quotation_no=revised_quotation_no,
                    customer_id=cust_id_int
                )
            else:
                # 新規保存
                from datetime import datetime as dt
                today = dt.now().strftime("%Y%m%d")
                prefix = f"Q-{today}-"
                
                # 今日の最後の見積No.を取得
                latest = (
                    Quotation.query
                    .filter(Quotation.quotation_no.like(f"{prefix}%"))
                    .order_by(Quotation.quotation_no.desc())
                    .first()
                )
                
                if not latest or not latest.quotation_no:
                    seq = 1
                else:
                    try:
                        base = latest.quotation_no.split("-")[-1].split("R")[0]
                        seq = int(base) + 1
                    except:
                        seq = 1
                
                quotation_no = f"{prefix}{seq:03d}"
                current_app.logger.info(f"[quotation_new] Generating quotation_no: {quotation_no}")
                quotation = Quotation(
                    company_name=values["company_name"],
                    contact_name=values["contact_name"],
                    project_name=values["project_name"],
                    delivery_date=values["delivery_date"],
                    delivery_terms=values["delivery_terms"],
                    payment_terms=values["payment_terms"],
                    valid_until=values["valid_until"],
                    valid_days=values.get("valid_days"),  # 見積期限（日数）
                    remarks=values["remarks"],
                    estimator_name=values.get("estimator_name", ""),
                    discount_rate=values.get("discount_rate", 0.0),
                    discount_amount=values.get("discount_amount", 0),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    quotation_no=quotation_no,
                    customer_id=cust_id_int
                )

            # ---- calc_mode + new_v1 fields ----
            quotation.calc_mode = _norm_calc_mode(request.form.get("calc_mode"))
            quotation.avg_entry_dirs = _form_float(request.form, "avg_entry_dirs")
            quotation.station_auto = _form_int(request.form, "station_auto")
            quotation.station_manual = _form_int(request.form, "station_manual")
            quotation.station_relay = _form_int(request.form, "station_relay")
            quotation.station_charge = _form_int(request.form, "station_charge")
            quotation.wait_position_count = _form_int(request.form, "wait_position_count")
            quotation.has_swap_operation = _form_bool(request.form, "has_swap_operation")
            quotation.has_plc_handshake = _form_bool(request.form, "has_plc_handshake")
            quotation.has_ev_integration = _form_bool(request.form, "has_ev_integration")
            quotation.difficulty_design = _norm_difficulty(request.form.get("difficulty_design"))
            quotation.difficulty_setup = _norm_difficulty(request.form.get("difficulty_setup"))

            current_app.logger.info(
                "[quotation_new] ready to save action=%s company_name=%s customer_id=%s details=%s total=%s",
                request.form.get("action"),
                values.get("company_name"),
                cust_id_int,
                len(details),
                total
            )

            db.session.add(quotation)
            db.session.flush()  # quotation.id を確定

            if not revise_source_id:
                quotation.original_id = quotation.id
                quotation.revision_no = 0

            for d in details:
                d.quotation_id = quotation.id
                db.session.add(d)

            # 合計金額をQuotationにセット（total_amount列があれば）
            if hasattr(quotation, 'total_amount'):
                quotation.total_amount = total

            db.session.commit()
            current_app.logger.info(
                "[quotation_new] saved quotation_id=%s action=%s",
                quotation.id,
                request.form.get("action")
            )
            flash("見積を登録しました。", "success")
            
            # action値に応じた遷移先を分岐
            action = request.form.get("action", "")
            if action == "save_and_print":
                return redirect(url_for("quotation.print_view", quotation_id=quotation.id))
            else:
                return redirect(url_for("quotation.quotation_view", quotation_id=quotation.id))

        # エラー時：ヘッダ入力値をテンプレートに渡す
        from app.cost_utils import LABOR_RATE, DESIGN_SELL_RATE, SETUP_SELL_RATE
        rates = {
            "LABOR_RATE": LABOR_RATE,
            "DESIGN_SELL_RATE": DESIGN_SELL_RATE,
            "SETUP_SELL_RATE": SETUP_SELL_RATE,
        }
        return render_template(
            "quotation_form.html",
            error=error,
            products=product_list,
            values=values,
            rates=rates
        )

    # GET 時：ヘッダ初期値と products, customers を渡す
    from app.cost_utils import LABOR_RATE, DESIGN_SELL_RATE, SETUP_SELL_RATE
    rates = {
        "LABOR_RATE": LABOR_RATE,
        "DESIGN_SELL_RATE": DESIGN_SELL_RATE,
        "SETUP_SELL_RATE": SETUP_SELL_RATE,
    }
    return render_template(
        "quotation_form.html",
        error=error,
        products=product_list,
        values=values,
        rates=rates
    )

# 見積削除（例: /quotation/<int:quotation_id>/delete）
@quotation_bp.route("/quotation/<int:quotation_id>/delete", methods=["POST"])
def quotation_delete(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    # グループID（original_idがあればそれ、なければ自分）
    group_id = quotation.original_id or quotation.id
    targets = Quotation.query.filter((Quotation.id == group_id) | (Quotation.original_id == group_id)).all()
    for qq in targets:
        QuotationDetail.query.filter_by(quotation_id=qq.id).delete(synchronize_session=False)
        db.session.delete(qq)
    db.session.commit()
    flash("見積を削除しました。", "success")
    return redirect(url_for("quotation.quotation_list"))
