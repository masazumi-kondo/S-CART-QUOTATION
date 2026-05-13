from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models.product import Product
from app.decorators import login_required, roles_required
from app.csv_utils import create_csv_response

product_bp = Blueprint("product", __name__)

# --- 製品マスタ削除 ---
@product_bp.route("/products/<int:id>/delete", methods=["POST", "GET"])
@login_required
@roles_required("admin")
def product_delete(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash("製品を削除しました。", "success")
    return redirect(url_for("product.product_list"))

# --- 既存: 製品マスタ一覧 ---
@product_bp.route("/products")
def product_list():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("product_list.html", products=products)

@product_bp.route("/products/export-csv")
@login_required
@roles_required("admin")
def product_export_csv():
    """製品マスタをCSV形式で出力"""
    products = Product.query.order_by(Product.id).all()
    
    headers = ['製品ID', '製品名', '単価', '原価', '利益率（%）', '備考', '作成日', '更新日']
    rows = []
    
    for p in products:
        profit_rate = ((p.unit_price - (p.cost or 0)) / p.unit_price * 100) if p.unit_price and p.unit_price > 0 else 0
        
        rows.append([
            p.id or '',
            p.name or '',
            int(p.unit_price) if p.unit_price else 0,
            int(p.cost or 0),
            f'{profit_rate:.1f}',
            p.note or '',
            p.created_at.strftime('%Y/%m/%d %H:%M') if p.created_at else '',
            p.updated_at.strftime('%Y/%m/%d %H:%M') if p.updated_at else '',
        ])
    
    return create_csv_response('製品マスタ', headers, rows)

# --- 新規追加: 製品マスタ新規登録 ---
@product_bp.route("/products/new", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def product_new():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        unit_price_raw = request.form.get("unit_price", "").replace(",", "").strip()
        cost_raw = request.form.get("cost", "").replace(",", "").strip()
        note = request.form.get("note", "").strip()

        if not name:
            error = "製品名は必須です。"
        elif not unit_price_raw:
            error = "単価は必須です。"
        else:
            try:
                unit_price = float(unit_price_raw)
            except ValueError:
                unit_price = 0.0
            try:
                cost = float(cost_raw) if cost_raw else 0.0
            except ValueError:
                cost = 0.0

            product = Product(
                name=name,
                unit_price=unit_price,
                cost=cost,
                note=note or None,
            )
            db.session.add(product)
            db.session.commit()
            flash("製品を登録しました。", "success")
            return redirect(url_for("product.product_list"))

        # バリデーション NG の場合はここで values を再構築
        values = {
            "name": name,
            "unit_price": unit_price_raw,
            "cost": cost_raw,
            "note": note,
        }
        return render_template("product_form.html", error=error, values=values)

    # GET の場合
    values = {
        "name": "",
        "unit_price": 0,
        "cost": 0,
        "note": "",
    }
    return render_template("product_form.html", error=None, values=values)

# --- 既存: 製品マスタ編集 ---
@product_bp.route("/products/<int:id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def product_edit(id):
    error = None
    product = Product.query.get_or_404(id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        unit_price_raw = request.form.get("unit_price", "").replace(",", "").strip()
        cost_raw = request.form.get("cost", "").replace(",", "").strip()
        note = request.form.get("note", "").strip()

        if not name:
            error = "製品名は必須です。"
        elif not unit_price_raw:
            error = "単価は必須です。"
        else:
            try:
                unit_price = float(unit_price_raw)
            except ValueError:
                unit_price = 0.0
            try:
                cost = float(cost_raw)
            except ValueError:
                cost = 0.0
            product.cost = cost

            product.name = name
            product.unit_price = unit_price
            product.cost = cost
            product.note = note or None
            db.session.commit()
            flash("製品情報を更新しました。", "success")
            return redirect(url_for("product.product_list"))

    # GET時: values辞書にcostを含める
    values = {
        "name": product.name or "",
        "unit_price": product.unit_price or 0,
        "cost": product.cost or 0,
        "note": product.note or ""
    }
    return render_template("product_form.html", error=error, values=values)
