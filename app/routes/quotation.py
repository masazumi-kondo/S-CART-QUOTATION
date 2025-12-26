
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
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
    customers_json = [
        {"id": c.id, "name": c.name, "name_kana": c.name_kana} for c in customers_query
    ]
    customers_meta = {
        str(c.id): {
            "name": c.name or "",
            "payment_term_name": (c.payment_term_ref.name if c.payment_term_ref else "") or "",
            "payment_terms_legacy": c.payment_terms or ""
        }
        for c in customers_query
    }
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
    return render_template(
        "quotation_form.html",
        error=None,
        products=product_list,
        values=values,
        details=detail_dicts,
        revise_source_id=orig.id,
        customers=customers_json,
        customers_meta=customers_meta
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
    try:
        design_setup = calc_design_setup_for_quotation(quotation)
        if not isinstance(design_setup, dict):
            raise ValueError("design_setup is not dict")
    except Exception:
        from flask import current_app
        current_app.logger.exception("failed to calc design/setup amounts for quotation %s", quotation_id)
        design_setup = {
            "design_hours": 0,
            "design_cost": 0,
            "design_fee": 0,
            "design_profit_rate": 0,
            "setup_hours": 0,
            "setup_cost": 0,
            "setup_fee": 0,
            "setup_profit_rate": 0,
        }

    return render_template(
        "quotation_view.html",
        quotation=quotation,
        details=details,
        total_amount=total,
        design_setup=design_setup,
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
    return render_template("quotation_list.html", quotations=quotations)


@quotation_bp.route("/quotation/new", methods=["GET", "POST"])

def quotation_new():
    import logging
    logging.info("[quotation_new] method=%s path=%s url=%s referrer=%s revise_source_id=%s", request.method, request.path, request.url, request.referrer, request.form.get("revise_source_id"))
    error = None
    # Productモデルのリストを取得し、JSONシリアライズ可能な辞書リストに変換
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

    # Customerリスト: approvedのみ（admin/一般共通、未承認顧客は選択不可）
    customers_query = Customer.query.options(joinedload(Customer.payment_term_ref)).filter(Customer.status == CustomerStatus.APPROVED.value).order_by(Customer.name).all()
    customers_json = [
        {"id": c.id, "name": c.name, "name_kana": c.name_kana} for c in customers_query
    ]
    customers_meta = {
        str(c.id): {
            "name": c.name or "",
            "payment_term_name": (c.payment_term_ref.name if c.payment_term_ref else "") or "",
            "payment_terms_legacy": c.payment_terms or ""
        }
        for c in customers_query
    }
    # ヘッダ入力値保持用
    values = {
        "company_name": "",
        "contact_name": "",
        "project_name": "",
        "delivery_date": "",
        "delivery_terms": "",
        "payment_terms": "",
        "valid_until": "",
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
        "discount_rate": 0.0
    }


    if request.method == "POST":
        # ヘッダ項目取得
        values["company_name"] = request.form.get("company_name", "").strip()
        values["contact_name"] = request.form.get("contact_name", "").strip()
        values["project_name"] = request.form.get("project_name", "").strip()
        values["delivery_date"] = request.form.get("delivery_date", "").strip()
        values["delivery_terms"] = request.form.get("delivery_terms", "").strip()
        values["payment_terms"] = request.form.get("payment_terms", "").strip()
        values["valid_until"] = request.form.get("valid_until", "").strip()
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

        # --- デバッグログ追加 ---
        from flask import current_app
        current_app.logger.info("quotation_new POST: product_id=%s", request.form.getlist("product_id[]"))
        current_app.logger.info("quotation_new POST: code=%s", request.form.getlist("code[]"))
        current_app.logger.info("quotation_new POST: description=%s", request.form.getlist("description[]"))
        current_app.logger.info("quotation_new POST: unit_price=%s", request.form.getlist("unit_price[]"))
        current_app.logger.info("quotation_new POST: quantity=%s", request.form.getlist("quantity[]"))
        current_app.logger.info("quotation_new POST: subtotal=%s", request.form.getlist("subtotal[]"))

        # --- 明細行の取得（新しいname属性に対応） ---
        product_ids = request.form.getlist("product_id[]")
        codes = request.form.getlist("code[]")
        descs = request.form.getlist("description[]")
        unit_prices = request.form.getlist("unit_price[]")
        quantities = request.form.getlist("quantity[]")
        subtotals = request.form.getlist("subtotal[]")


        details = []
        total = 0
        for idx in range(len(product_ids)):
            # 1) raw文字列取得
            product_id_raw = (product_ids[idx] if idx < len(product_ids) else '').strip()
            code = (codes[idx] if idx < len(codes) else '').strip()
            desc = (descs[idx] if idx < len(descs) else '').strip()
            unit_price_raw = (unit_prices[idx] if idx < len(unit_prices) else '').replace(',', '').strip()
            quantity_raw = (quantities[idx] if idx < len(quantities) else '').replace(',', '').strip()
            subtotal_raw = (subtotals[idx] if idx < len(subtotals) else '').replace(',', '').strip()

            # 2) 完全空行チェック
            if not code and not desc and not unit_price_raw and not quantity_raw:
                continue

            # 3) 型変換（例外は0扱い）
            try:
                unit_price_val = float(unit_price_raw) if unit_price_raw else 0
            except (ValueError, TypeError):
                unit_price_val = 0
            try:
                quantity_val = int(quantity_raw) if quantity_raw else 0
            except (ValueError, TypeError):
                quantity_val = 0

            # 4) 数量0以下はスキップ
            if quantity_val <= 0:
                continue

            # 5) subtotalの型変換（例外/空は再計算）
            try:
                subtotal_val = float(subtotal_raw) if subtotal_raw else unit_price_val * quantity_val
            except (ValueError, TypeError):
                subtotal_val = unit_price_val * quantity_val

            # 6) product_idのint変換
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

            # 7) QuotationDetailインスタンス生成
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

            detail = QuotationDetail(**detail_kwargs)
            details.append(detail)
            total += subtotal_val

        # --- 明細件数と内容をログ出力 ---
        from flask import current_app
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

        # --- 設計費・現地セットアップ費の自動計算（パラメーター優先） ---

        from app.cost_utils import calc_design_and_setup_amounts

        # パラメータ入力値をdictでまとめて渡す
        param_dict = {
            "distance_m": values["distance_m"],
            "intersection_count": values["intersection_count"],
            "station_count": values["station_count"],
            "vehicle_count": values["vehicle_count"],
            "equipment_count": values["equipment_count"],
            "circuit_difficulty": values["circuit_difficulty"],
        }

        # パラメータがすべて未入力なら設計費・現地セットアップ費は追加しない
        if not (param_dict["distance_m"] or param_dict["intersection_count"] or param_dict["station_count"]):
            pass
        else:
            design_fee, design_cost, design_hours, setup_fee, setup_cost, setup_hours = calc_design_and_setup_amounts(param_dict)
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
                    design_kwargs["description"] = "設計費（走行条件）"
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
                    setup_kwargs["description"] = "現地セットアップ費（走行条件）"
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
            cust_obj = Customer.query.get_or_404(cust_id_int) if cust_id_int else None
            # 顧客未承認ガード（pending/rejectedは不可）
            if not cust_obj.is_approved:
                flash("未承認の顧客は見積作成できません。承認後に再度お試しください。", "warning")
                return redirect(url_for("quotation.quotation_new"))
            # 顧客IDがある場合はcompany_nameをCustomer.nameで上書き
            values["company_name"] = cust_obj.name
            # 顧客IDが空の場合はcompany_nameはそのまま
            if revise_source_id:
                # 改定保存: 系列max(revision_no)+1を採番
                src = Quotation.query.get_or_404(int(revise_source_id))
                original_id = src.original_id or src.id
                max_rev = db.session.query(func.max(Quotation.revision_no)).filter(Quotation.original_id == original_id).scalar() or 0
                revision_no = int(max_rev) + 1
                quotation = Quotation(
                    company_name=values["company_name"],
                    contact_name=values["contact_name"],
                    project_name=values["project_name"],
                    delivery_date=values["delivery_date"],
                    delivery_terms=values["delivery_terms"],
                    payment_terms=values["payment_terms"],
                    valid_until=values["valid_until"],
                    remarks=values["remarks"],
                    estimator_name=values.get("estimator_name", ""),
                    discount_rate=values.get("discount_rate", 0.0),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    original_id=original_id,
                    revision_no=revision_no,
                    customer_id=cust_id_int
                )
            else:
                # 新規保存
                quotation = Quotation(
                    company_name=values["company_name"],
                    contact_name=values["contact_name"],
                    project_name=values["project_name"],
                    delivery_date=values["delivery_date"],
                    delivery_terms=values["delivery_terms"],
                    payment_terms=values["payment_terms"],
                    valid_until=values["valid_until"],
                    remarks=values["remarks"],
                    estimator_name=values.get("estimator_name", ""),
                    discount_rate=values.get("discount_rate", 0.0),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    customer_id=cust_id_int
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
            flash("見積を登録しました。", "success")
            return redirect(url_for("quotation.quotation_view", quotation_id=quotation.id))

        # エラー時：ヘッダ入力値をテンプレートに渡す
        return render_template(
            "quotation_form.html",
            error=error,
            products=product_list,
            values=values,
            customers=customers_json,
            customers_meta=customers_meta
        )

    # GET 時：ヘッダ初期値と products, customers を渡す
    return render_template(
        "quotation_form.html",
        error=error,
        products=product_list,
        values=values,
        customers=customers_json,
        customers_meta=customers_meta
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
