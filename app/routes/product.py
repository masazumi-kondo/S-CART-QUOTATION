from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models.product import Product

product_bp = Blueprint("product", __name__)

# --- 製品マスタ削除 ---
@product_bp.route("/products/<int:id>/delete", methods=["POST", "GET"])
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

# --- 新規追加: 製品マスタ新規登録 ---
@product_bp.route("/products/new", methods=["GET", "POST"])
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
