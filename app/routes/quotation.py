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

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, g
from app import db
from app.models.quotation import Quotation
from app.models.quotation_detail import QuotationDetail
from app.models.product import Product
from app.models.customer import Customer, CustomerStatus
from app.models.user import User
from sqlalchemy.orm import joinedload
from datetime import datetime
from app.cost_utils import calc_design_setup_for_quotation
from sqlalchemy import func
from app.auth_utils import login_required, roles_required
from app.csv_utils import create_csv_response
from app.approval_utils import get_approval_status_label, can_request_approval

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
    from app.models.v2_calculation_setting import V2CalculationSetting
    rates = {
        "LABOR_RATE": LABOR_RATE,
        "DESIGN_SELL_RATE": DESIGN_SELL_RATE,
        "SETUP_SELL_RATE": SETUP_SELL_RATE,
    }
    # Get V2 calculation settings
    v2_setting = V2CalculationSetting.query.get(1)
    if not v2_setting:
        v2_setting = V2CalculationSetting(id=1)
        db.session.add(v2_setting)
        db.session.commit()
    v2_settings = v2_setting.to_v2_json()
    
    # V2結果と合計値を復元（明細から再計算）
    v2_result = build_v2_result_from_details(details)
    summary = build_summary_from_details(orig)
    
    return render_template(
        "quotation_form.html",
        error=None,
        products=product_list,
        values=values,
        details=detail_dicts,
        revise_source_id=orig.id,
        rates=rates,
        v2_settings=v2_settings,
        v2_result=v2_result,  # V2結果復元
        summary=summary  # 合計値復元
    )


# --- Helper functions for detail processing ---

def get_detail_name(detail):
    """
    明細行の名称を複数候補から取得する。
    """
    candidates = [
        getattr(detail, "label", None),
        getattr(detail, "description", None),
    ]
    
    for value in candidates:
        if value:
            return str(value).strip()
    
    # productリレーションから取得を試みる
    product = getattr(detail, "product", None)
    if product:
        for attr in ["name", "product_name", "model_name"]:
            value = getattr(product, attr, None)
            if value:
                return str(value).strip()
    
    return ""


def is_design_fee_line(detail):
    """
    設計費行か判定する。
    """
    name = get_detail_name(detail)
    return "設計費" in name


def is_setup_fee_line(detail):
    """
    現地セットアップ費行か判定する。
    """
    name = get_detail_name(detail)
    return "現地セットアップ" in name or "セットアップ費" in name


def is_v2_line(detail):
    """
    V2関連行か判定する。
    """
    name = get_detail_name(detail)
    return "V2" in name or is_design_fee_line(detail) or is_setup_fee_line(detail)


def build_v2_result_from_details(details):
    """
    明細データから V2 結果値を復元する
    """
    result = {
        "design_hours": "",
        "setup_hours": "",
        "pattern_score": "",
        "area_score": "",
        "landmark_factor": "",
        "plc_signal_count": "",
        "design_price": 0,
        "setup_price": 0,
        "design_cost": 0,
        "setup_cost": 0,
    }

    for detail in details:
        amount = (
            getattr(detail, "amount", None)
            or getattr(detail, "subtotal", None)
            or getattr(detail, "total_price", None)
            or 0
        )

        cost = (
            getattr(detail, "cost", None)
            or getattr(detail, "unit_cost", None)
            or getattr(detail, "total_cost", None)
            or 0
        )

        if is_design_fee_line(detail):
            result["design_price"] = float(amount or 0)
            result["design_cost"] = float(cost or 0)

        if is_setup_fee_line(detail):
            result["setup_price"] = float(amount or 0)
            result["setup_cost"] = float(cost or 0)

    return result


def build_summary_from_details(quotation):
    """
    明細データから合計値を再計算する
    """
    details = quotation.details
    
    subtotal_price = 0
    subtotal_cost = 0

    for detail in details:
        amount = (
            getattr(detail, "amount", None)
            or getattr(detail, "subtotal", None)
            or getattr(detail, "total_price", None)
            or 0
        )

        cost = (
            getattr(detail, "cost", None)
            or getattr(detail, "unit_cost", None)
            or getattr(detail, "total_cost", None)
            or 0
        )

        quantity = getattr(detail, "quantity", 1) or 1

        # unit_costしかない場合は数量を掛ける
        if getattr(detail, "total_cost", None) is None and getattr(detail, "unit_cost", None) is not None:
            cost = float(cost) * float(quantity)

        subtotal_price += float(amount or 0)
        subtotal_cost += float(cost or 0)

    discount_amount = getattr(quotation, "discount_amount", 0) or 0
    final_total_price = subtotal_price - float(discount_amount or 0)

    profit_margin = 0
    if subtotal_price:
        profit_margin = (subtotal_price - subtotal_cost) / subtotal_price * 100

    final_profit_margin = 0
    if final_total_price:
        final_profit_margin = (final_total_price - subtotal_cost) / final_total_price * 100

    discount_rate = 0
    if subtotal_price:
        discount_rate = float(discount_amount or 0) / subtotal_price * 100

    return {
        "subtotal_price": subtotal_price,
        "subtotal_cost": subtotal_cost,
        "profit_margin": profit_margin,
        "discount_amount": discount_amount,
        "discount_rate": discount_rate,
        "final_total_price": final_total_price,
        "final_total_cost": subtotal_cost,
        "final_profit_margin": final_profit_margin,
    }


@quotation_bp.route("/quotation/<int:quotation_id>/edit", methods=["GET"])
def quotation_edit(quotation_id):
    """
    見積編集画面
    既存見積データを読み込んで、見積作成フォームを表示する。
    編集時に明細を修正して、保存時は同じ quotation.id で更新する。
    """
    quotation = Quotation.query.get_or_404(quotation_id)
    details = QuotationDetail.query.filter_by(quotation_id=quotation.id).all()
    
    # values: id, created_at, updated_at を除外
    values = {c.name: getattr(quotation, c.name) for c in Quotation.__table__.columns if c.name not in ("id", "created_at", "updated_at")}
    # customer_idをvaluesに追加（テンプレ互換のため str に揃える）
    cust_id = getattr(quotation, "customer_id", None)
    values["customer_id"] = str(cust_id) if cust_id else ""
    # customer_idがあればcompany_nameをCustomer.nameで上書き
    cust_id_int = None
    try:
        cust_id_int = int(values["customer_id"]) if values["customer_id"] else None
    except Exception:
        cust_id_int = None
    if cust_id_int:
        cust = Customer.query.get(cust_id_int)
        if cust:
            values["company_name"] = cust.name

    # 顧客リスト
    customers_query = Customer.query.options(joinedload(Customer.payment_term_ref)).filter(Customer.status == CustomerStatus.APPROVED.value).order_by(Customer.name).all()
    
    # details: id, quotation_id, created_at, updated_at を除外
    detail_dicts = []
    for d in details:
        dct = {c.name: getattr(d, c.name) for c in QuotationDetail.__table__.columns if c.name not in ("id", "quotation_id", "created_at", "updated_at")}
        detail_dicts.append(dct)
    
    # product_list
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
    from app.models.v2_calculation_setting import V2CalculationSetting
    rates = {
        "LABOR_RATE": LABOR_RATE,
        "DESIGN_SELL_RATE": DESIGN_SELL_RATE,
        "SETUP_SELL_RATE": SETUP_SELL_RATE,
    }
    # Get V2 calculation settings
    v2_setting = V2CalculationSetting.query.get(1)
    if not v2_setting:
        v2_setting = V2CalculationSetting(id=1)
        db.session.add(v2_setting)
        db.session.commit()
    v2_settings = v2_setting.to_v2_json()
    
    # V2結果と合計値を復元（明細から再計算）
    v2_result = build_v2_result_from_details(details)
    summary = build_summary_from_details(quotation)
    
    return render_template(
        "quotation_form.html",
        error=None,
        products=product_list,
        values=values,
        details=detail_dicts,
        edit_quotation_id=quotation.id,  # 編集モード用パラメータ
        rates=rates,
        v2_settings=v2_settings,
        v2_result=v2_result,  # V2結果復元
        summary=summary  # 合計値復元
    )

# 印刷用見積書の明細並び順ヘルパー

def sort_details_for_display(details):
    """
    見積書表示用に明細を並び替える。
    優先順位：
    1. V2自動算出行ではない通常製品（保存順を維持）
    2. 設計費（V2自動算出）
    3. 現地セットアップ費（V2自動算出）
    """
    def sort_key(detail):
        if is_design_fee_line(detail):
            return (2, 1, getattr(detail, "id", 0))
        if is_setup_fee_line(detail):
            return (2, 2, getattr(detail, "id", 0))
        return (1, 0, getattr(detail, "id", 0))
    
    return sorted(details, key=sort_key)


def get_customer_display_name(quotation):
    """
    見積書の宛名表示用に顧客名を取得する。
    優先順位：
    1. quotation.company_name
    2. quotation.customer.name
    3. "お客様"
    """
    if quotation.company_name:
        return quotation.company_name
    if quotation.customer and quotation.customer.name:
        return quotation.customer.name
    return "お客様"


def get_estimator_info(quotation, current_user=None):
    """
    見積作成担当者情報を取得する。
    優先順位：
    1. quotation.estimator_name
    2. current_user.display_name
    3. current_user.login_id
    4. "-"
    """
    if quotation.estimator_name:
        return quotation.estimator_name
    if current_user:
        if hasattr(current_user, 'display_name') and current_user.display_name:
            return current_user.display_name
        if hasattr(current_user, 'login_id') and current_user.login_id:
            return current_user.login_id
    return "-"


def get_unit_display(detail):
    """
    明細行の単位を取得する。
    ルール：
    - V2自動算出行（設計費、現地セットアップ費）：「式」
    - それ以外で product_id がある明細：「台」
    - それ以外で detail.unit が設定されている場合：detail.unit
    - 製品名から自動補正（S-CART, SmooV, AGV等）：「台」
    - デフォルト：「式」
    """
    name = get_detail_name(detail)
    
    # V2費用行は式
    if is_design_fee_line(detail) or is_setup_fee_line(detail):
        return "式"
    
    # 製品本体の判定
    # 1. product_id がある行は製品本体扱いで台
    if getattr(detail, "product_id", None):
        return "台"
    
    # 2. 製品名から補正
    if "S-CART" in name or "SmooV" in name or "AGV" in name or "AMR" in name:
        return "台"
    
    # 3. 明細に明示単位があり、かつ空でなければ優先
    unit = getattr(detail, "unit", None)
    if unit and str(unit).strip():
        return str(unit).strip()
    
    # デフォルト
    return "式"

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
    
    # 各明細に単位情報を追加
    for detail in details:
        detail.unit_display = get_unit_display(detail)
    
    # 見積書用の表示情報を準備
    customer_display_name = get_customer_display_name(quotation)
    estimator_info = get_estimator_info(quotation, g.get('current_user'))

    return render_template(
        "quotation_view.html",
        quotation=quotation,
        details=details,
        total_amount=total,
        discount_amount=discount_amount,
        total_after_discount=total_after_discount,
        design_setup=design_setup,
        customer_display_name=customer_display_name,
        estimator_info=estimator_info,
    )


@quotation_bp.route("/quotation/<int:quotation_id>/print")
def print_view(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    details = sort_details_for_display(quotation.details)
    
    # 各明細に単位情報を追加
    for detail in details:
        detail.unit_display = get_unit_display(detail)
    
    total_amount = sum((getattr(d, "subtotal", 0) or 0) for d in details)
    discount_amount = getattr(quotation, "discount_amount", 0) or 0
    total_after_discount = max(0, total_amount - discount_amount)
    
    # 見積書用の表示情報を準備
    customer_display_name = get_customer_display_name(quotation)
    estimator_info = get_estimator_info(quotation, g.get('current_user'))
    
    return render_template(
        "quotation_view.html",
        quotation=quotation,
        details=details,
        total_amount=total_amount,
        discount_amount=discount_amount,
        total_after_discount=total_after_discount,
        customer_display_name=customer_display_name,
        estimator_info=estimator_info,
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
    originals = Quotation.query.options(
        joinedload(Quotation.customer),
        joinedload(Quotation.estimator),
        joinedload(Quotation.details),
        joinedload(Quotation.approved_by_user),
        joinedload(Quotation.rejected_by_user)
    ).filter(Quotation.revision_no == 0).order_by(Quotation.created_at.desc()).all()
    
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
            .options(
                joinedload(Quotation.customer),
                joinedload(Quotation.estimator),
                joinedload(Quotation.details),
                joinedload(Quotation.approved_by_user),
                joinedload(Quotation.rejected_by_user)
            )
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
    
    return render_template("quotation_list.html", quotations=quotations)


@quotation_bp.route("/quotations/export-csv")
@login_required
@roles_required("admin")
def quotation_export_csv():
    """
    見積一覧をCSV形式でエクスポートします。
    フィールド: 見積ID, 見積No., 改定版No., 顧客名, 担当者名, プロジェクト名, 見積人名, 作成日時, 更新日時, 
               小計価格, 小計原価, 値引金額, 最終合計額, 利益率%, 承認状態, 承認者, 承認日時, 差戻し者, 差戻し日時, 備考
    """
    # All quotations with their customer and estimator info
    quotations = Quotation.query.options(
        joinedload(Quotation.customer),
        joinedload(Quotation.estimator),
        joinedload(Quotation.approved_by_user),
        joinedload(Quotation.rejected_by_user),
        joinedload(Quotation.details)
    ).all()
    
    headers = ['見積ID', '見積No.', '改定版No.', '顧客名', '担当者名', 'プロジェクト名', '見積人名', 
               '作成日時', '更新日時', '小計価格', '小計原価', '値引金額', '最終合計額', '利益率%', 
               '承認状態', '承認者', '承認日時', '差戻し者', '差戻し日時', '備考']
    
    rows = []
    for q in quotations:
        # Calculate subtotals from details
        subtotal_price = sum((d.subtotal or 0) for d in q.details) if q.details else 0
        subtotal_cost = sum((d.subtotal_cost or 0) for d in q.details) if q.details else 0
        discount_amount = q.discount_amount or 0
        final_total_price = max(0, subtotal_price - discount_amount)
        
        # Calculate profit margin
        if final_total_price > 0:
            profit_margin = ((final_total_price - subtotal_cost) / final_total_price * 100) if final_total_price > 0 else 0
        else:
            profit_margin = 0
        
        # Format dates
        created_at = q.created_at.strftime('%Y/%m/%d %H:%M') if q.created_at else ''
        updated_at = q.updated_at.strftime('%Y/%m/%d %H:%M') if q.updated_at else ''
        approved_at = q.approved_at.strftime('%Y/%m/%d %H:%M') if q.approved_at else ''
        rejected_at = q.rejected_at.strftime('%Y/%m/%d %H:%M') if q.rejected_at else ''
        
        # Approval status label
        approval_status_label = get_approval_status_label(q.approval_status)
        
        row = [
            q.id or '',
            q.quotation_no or f"{q.original_id or q.id}-R{q.revision_no}",
            q.revision_no or '',
            q.customer.name if q.customer else '',
            q.customer.contact_name if q.customer else '',
            q.project_name or '',
            q.estimator.display_name if q.estimator else '',
            created_at,
            updated_at,
            subtotal_price,
            subtotal_cost,
            discount_amount,
            final_total_price,
            f"{profit_margin:.1f}" if profit_margin else '0.0',
            approval_status_label,
            q.approved_by_user.display_name if q.approved_by_user else '',
            approved_at,
            q.rejected_by_user.display_name if q.rejected_by_user else '',
            rejected_at,
            q.remarks or ''
        ]
        rows.append(row)
    
    return create_csv_response('見積一覧', headers, rows)


@quotation_bp.route("/quotation/new", methods=["GET", "POST"])

def quotation_new():
    import logging
    logging.info("[quotation_new] method=%s path=%s url=%s referrer=%s revise_source_id=%s edit_quotation_id=%s", request.method, request.path, request.url, request.referrer, request.form.get("revise_source_id"), request.form.get("edit_quotation_id"))
    error = None
    
    # Initialize rates and v2_settings upfront for both GET and POST
    from app.cost_utils import LABOR_RATE, DESIGN_SELL_RATE, SETUP_SELL_RATE
    from app.models.v2_calculation_setting import V2CalculationSetting
    rates = {
        "LABOR_RATE": LABOR_RATE,
        "DESIGN_SELL_RATE": DESIGN_SELL_RATE,
        "SETUP_SELL_RATE": SETUP_SELL_RATE,
    }
    v2_setting = V2CalculationSetting.query.get(1)
    if not v2_setting:
        v2_setting = V2CalculationSetting(id=1)
        db.session.add(v2_setting)
        db.session.commit()
    v2_settings = v2_setting.to_v2_json()
    
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

            def parse_quantity(val):
                try:
                    return int(float(val or 1))
                except (ValueError, TypeError):
                    return 1

            try:
                unit_price_val = float(unit_price_raw) if unit_price_raw else 0
            except (ValueError, TypeError):
                unit_price_val = 0
            quantity_val = parse_quantity(quantity_raw)
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

        # 承認状態リセット判定用フラグの初期化
        approval_status_was_reset = False

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
                        rates=rates,
                        v2_settings=v2_settings,
                        v2_result={},
                        summary={}
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
                        rates=rates,
                        v2_settings=v2_settings,
                        v2_result={},
                        summary={}
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
                    valid_days=values.get("valid_days"),
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
            elif request.form.get("edit_quotation_id"):
                # 編集保存: 既存quotationを取得して基本項目を更新
                edit_id = int(request.form.get("edit_quotation_id"))
                quotation = Quotation.query.get_or_404(edit_id)
                
                # 承認状態がリセットされるかを記録（更新前）
                approval_status_was_reset = quotation.approval_status in ["pending", "approved", "rejected"]
                
                # 基本項目を更新
                quotation.company_name = values["company_name"]
                quotation.contact_name = values["contact_name"]
                quotation.project_name = values["project_name"]
                quotation.delivery_date = values["delivery_date"]
                quotation.delivery_terms = values["delivery_terms"]
                quotation.payment_terms = values["payment_terms"]
                quotation.valid_until = values["valid_until"]
                quotation.valid_days = values.get("valid_days")
                quotation.remarks = values["remarks"]
                quotation.estimator_name = values.get("estimator_name", "")
                quotation.discount_rate = values.get("discount_rate", 0.0)
                quotation.discount_amount = values.get("discount_amount", 0)
                quotation.updated_at = datetime.utcnow()
                quotation.customer_id = cust_id_int
                
                # 承認状態をリセット（pending/approved/rejected の場合）
                if approval_status_was_reset:
                    quotation.approval_status = "draft"
                    quotation.approval_requested_at = None
                    quotation.approved_at = None
                    quotation.approved_by_user_id = None
                    quotation.rejected_at = None
                    quotation.rejected_by_user_id = None
                    quotation.approval_comment = None
                
                # 既存明細を削除
                QuotationDetail.query.filter_by(quotation_id=quotation.id).delete(synchronize_session=False)
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

            # V2結果をJSON保存
            import json
            v2_result = {
                "design_hours": request.form.get("v2_design_hours", ""),
                "setup_hours": request.form.get("v2_setup_hours", ""),
                "pattern_score": request.form.get("v2_pattern_score", ""),
                "area_score": request.form.get("v2_area_score", ""),
                "landmark_factor": request.form.get("v2_landmark_factor", ""),
                "plc_signal_count": request.form.get("v2_plc_signal_count", ""),
                "design_price": request.form.get("v2_design_price", ""),
                "setup_price": request.form.get("v2_setup_price", "")
            }
            quotation.v2_result_json = json.dumps(v2_result, ensure_ascii=False)

            # 合計・利益率等をJSON保存
            summary = {
                "subtotal_price": request.form.get("subtotal_price", ""),
                "subtotal_cost": request.form.get("subtotal_cost", ""),
                "profit_margin": request.form.get("profit_margin", ""),
                "final_total_price": request.form.get("final_total_price", ""),
                "final_total_cost": request.form.get("final_total_cost", ""),
                "final_profit_margin": request.form.get("final_profit_margin", "")
            }
            quotation.summary_json = json.dumps(summary, ensure_ascii=False)

            db.session.commit()

            current_app.logger.info(
                "[quotation_new] saved quotation_id=%s save_action=%s",
                quotation.id,
                request.form.get("save_action")
            )

            save_action = request.form.get("save_action", "list")
            is_edit = bool(request.form.get("edit_quotation_id"))
            is_new = not is_edit and not revise_source_id

            if save_action == "stay":
                # 保存後も編集画面に残る
                if is_edit:
                    if approval_status_was_reset:
                        flash("見積を更新しました。内容変更のため承認状態を作成中に戻しました。", "success")
                    else:
                        flash("見積を更新しました。引き続き編集できます。", "success")
                    return redirect(url_for("quotation.quotation_edit", quotation_id=quotation.id))
                else:
                    flash("見積を保存しました。引き続き編集できます。", "success")
                    return redirect(url_for("quotation.quotation_edit", quotation_id=quotation.id))
            else:
                # 一覧へ
                if is_edit:
                    if approval_status_was_reset:
                        flash("見積を更新しました。内容変更のため承認状態を作成中に戻しました。", "success")
                    else:
                        flash("見積を更新しました。", "success")
                else:
                    flash("見積を保存しました。", "success")
                return redirect(url_for("quotation.quotation_list"))

        # エラー時：ヘッダ入力値をテンプレートに渡す
        return render_template(
            "quotation_form.html",
            error=error,
            products=product_list,
            values=values,
            rates=rates,
            v2_settings=v2_settings,
            v2_result={},  # 新規作成時は空
            summary={}  # 新規作成時は空
        )

    # GET 時：ヘッダ初期値と products, customers を渡す
    return render_template(
        "quotation_form.html",
        error=error,
        products=product_list,
        values=values,
        rates=rates,
        v2_settings=v2_settings,
        v2_result={},  # 新規作成時は空
        summary={}  # 新規作成時は空
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


@quotation_bp.route("/quotation/<int:quotation_id>/request-approval", methods=["POST"])
@login_required
def quotation_request_approval(quotation_id):
    """Request approval for a quotation"""
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Check if quotation can be submitted for approval
    can_request, error_msg = can_request_approval(quotation)
    if not can_request:
        flash(f"承認申請できません。{error_msg}", "danger")
        return redirect(url_for("quotation.quotation_list"))
    
    # Update approval status
    quotation.approval_status = "pending"
    quotation.approval_requested_at = datetime.utcnow()
    # Clear any previous rejection/approval
    quotation.approved_at = None
    quotation.approved_by_user_id = None
    quotation.rejected_at = None
    quotation.rejected_by_user_id = None
    quotation.approval_comment = None
    
    db.session.commit()
    flash("見積を承認申請しました。", "success")
    return redirect(url_for("quotation.quotation_list"))


@quotation_bp.route("/quotation/<int:quotation_id>/approve", methods=["POST"])
@login_required
@roles_required("admin")
def quotation_approve(quotation_id):
    """Approve a quotation (admin only)"""
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Only allow approving pending quotations
    if quotation.approval_status != "pending":
        flash("この見積は承認待ち状態ではありません。", "danger")
        return redirect(url_for("quotation.quotation_list"))
    
    # Update approval status
    quotation.approval_status = "approved"
    quotation.approved_at = datetime.utcnow()
    quotation.approved_by_user_id = g.current_user.id
    # Clear any previous rejection
    quotation.rejected_at = None
    quotation.rejected_by_user_id = None
    quotation.approval_comment = None
    
    db.session.commit()
    flash("見積を承認しました。", "success")
    return redirect(url_for("quotation.quotation_list"))


@quotation_bp.route("/quotation/<int:quotation_id>/reject", methods=["POST"])
@login_required
@roles_required("admin")
def quotation_reject(quotation_id):
    """Reject a quotation with optional comment (admin only)"""
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Only allow rejecting pending quotations
    if quotation.approval_status != "pending":
        flash("この見積は承認待ち状態ではありません。", "danger")
        return redirect(url_for("quotation.quotation_list"))
    
    # Get comment from form
    approval_comment = request.form.get("approval_comment", "").strip()
    
    # Update approval status
    quotation.approval_status = "rejected"
    quotation.rejected_at = datetime.utcnow()
    quotation.rejected_by_user_id = g.current_user.id
    quotation.approval_comment = approval_comment if approval_comment else None
    # Clear any previous approval
    quotation.approved_at = None
    quotation.approved_by_user_id = None
    
    db.session.commit()
    flash("見積を差戻しました。", "success")
    return redirect(url_for("quotation.quotation_list"))
