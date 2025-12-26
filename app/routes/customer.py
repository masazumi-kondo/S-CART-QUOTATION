

from app.services.notifications import notify_customer_status_changed
from sqlalchemy import text
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app, session, abort
from sqlalchemy import or_
from datetime import datetime
from app.decorators import login_required, roles_required
from app import db
from app.models.customer import Customer, CustomerStatus
from app.models.customer_approval_log import CustomerApprovalLog
from app.models.user import User
from app.models.quotation import Quotation
from app.models.customer_credit import CustomerCredit
import logging

# Blueprint定義は必ず先
customer_bp = Blueprint('customer', __name__)

# 顧客承認履歴（閲覧専用・管理者のみ）
@customer_bp.route('/customers/<int:customer_id>/approval-history')
@login_required
@roles_required('admin')
def customer_approval_history(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    logs = (
        CustomerApprovalLog.query
        .filter(CustomerApprovalLog.customer_id == customer_id)
        .order_by(CustomerApprovalLog.approved_at.desc())
        .all()
    )

    # 承認者ユーザー名を引く（最小構成）
    user_map = {}
    if logs:
        user_ids = {log.approved_by for log in logs}
        users = User.query.filter(User.id.in_(user_ids)).all()
        user_map = {u.id: u.login_id for u in users}

    return render_template(
        'customer_approval_history.html',
        customer=customer,
        logs=logs,
        user_map=user_map
    )


# 与信情報取得ヘルパー
def get_credit_rows(customer_id):
    credit_rows = list(CustomerCredit.query.filter_by(customer_id=customer_id).order_by(CustomerCredit.fiscal_year.desc()).limit(3))
    while len(credit_rows) < 3:
        credit_rows.append(None)
    credit_rows = sorted(credit_rows, key=lambda x: x.fiscal_year if x else 0, reverse=True)
    return credit_rows

# 与信情報upsertヘルパー
def upsert_customer_credits(customer_id, form):
    years = form.getlist('credit_year[]')
    sales = form.getlist('credit_sales[]')
    profits = form.getlist('credit_profit[]')
    equities = form.getlist('credit_equity[]')
    fiscal_years_seen = set()
    duplicate_years = set()
    def parse_float(val):
        try:
            return float(val.replace(',', '').strip()) if val and val.strip() else None
        except Exception:
            return None
    for i in range(3):
        fy_raw = years[i].strip() if i < len(years) and years[i] else ''
        if not fy_raw:
            continue
        try:
            fiscal_year_int = int(fy_raw)
        except ValueError:
            continue
        if fiscal_year_int in fiscal_years_seen:
            duplicate_years.add(fiscal_year_int)
            continue
        fiscal_years_seen.add(fiscal_year_int)
        sales_amount = parse_float(sales[i]) if i < len(sales) else None
        net_income = parse_float(profits[i]) if i < len(profits) else None
        equity = parse_float(equities[i]) if i < len(equities) else None
        credit = CustomerCredit.query.filter_by(customer_id=customer_id, fiscal_year=fiscal_year_int).first()
        if not credit:
            credit = CustomerCredit(customer_id=customer_id, fiscal_year=fiscal_year_int)
            db.session.add(credit)
        credit.sales_amount = sales_amount
        credit.net_income = net_income
        credit.equity = equity
    return duplicate_years



@customer_bp.route('/customers')
@login_required
def customer_list():
    current_app.logger.info("[ROUTE] /customers called")
    q = request.args.get('q', '').strip()
    query = Customer.query
    if q:
        query = query.filter(or_(Customer.name.contains(q), Customer.name_kana.contains(q)))
    # 一般ユーザーはapprovedのみ、管理者は全件
    is_admin = g.current_user and getattr(g.current_user, 'role', None) == 'admin'
    if not is_admin:
        query = query.filter(Customer.status == CustomerStatus.APPROVED.value)
    customers = query.order_by(Customer.name).all()
    return render_template('customer_list.html', customers=customers, q=q, is_admin=is_admin, current_user=g.current_user)

@customer_bp.route('/customers/new', methods=['GET', 'POST'])
@login_required
def customer_new():
    if request.method == 'POST':
        customer_code = request.form.get('customer_code', '').strip()
        name = request.form.get('name', '').strip()
        name_kana = request.form.get('name_kana', '').strip()
        postal_code = request.form.get('postal_code', '').strip()
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        transaction_type = request.form.get('transaction_type', '').strip()
        payment_terms = request.form.get('payment_terms', '').strip()
        note = request.form.get('note', '').strip()
        if not name:
            flash('顧客名は必須です', 'danger')
            return render_template('customer_form.html', customer=None, credit_rows=[None, None, None], is_admin=(g.current_user and getattr(g.current_user, 'role', None) == 'admin'), current_user=g.current_user)
        if Customer.query.filter_by(name=name).first():
            flash('同名の顧客が既に存在します', 'danger')
            return render_template('customer_form.html', customer=None, credit_rows=[None, None, None], is_admin=(g.current_user and getattr(g.current_user, 'role', None) == 'admin'), current_user=g.current_user)
        try:
            customer = Customer(
                customer_code=customer_code,
                name=name,
                name_kana=name_kana,
                postal_code=postal_code,
                address=address,
                phone=phone,
                transaction_type=transaction_type,
                payment_terms=payment_terms,
                note=note,
                status=CustomerStatus.PENDING.value,
                requested_by_user_id=getattr(g.current_user, "id", None)
            )
            db.session.add(customer)
            db.session.flush()  # Allocate customer.id without committing

            duplicate_years = upsert_customer_credits(customer.id, request.form)
            db.session.commit()
            if duplicate_years:
                flash(f'同じ年度が複数入力されています: {sorted(list(duplicate_years))}', 'warning')
            flash('顧客を登録しました（承認待ち）', 'success')
            return redirect(url_for('customer.customer_list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in customer_new: {e}")
            flash('保存に失敗しました。入力内容を確認してください。', 'danger')
            return render_template('customer_form.html', customer=None, credit_rows=[None, None, None], is_admin=(g.current_user and getattr(g.current_user, 'role', None) == 'admin'), current_user=g.current_user)
    return render_template('customer_form.html', customer=None, credit_rows=[None, None, None], is_admin=(g.current_user and getattr(g.current_user, 'role', None) == 'admin'), current_user=g.current_user)

@customer_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def customer_edit(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    is_admin = g.current_user and getattr(g.current_user, "role", None) == "admin"
    is_owner = customer.requested_by_user_id == getattr(g.current_user, "id", None)
    # アクセス制御: admin以外はapprovedのみ閲覧可。申請者もpendingは閲覧可（要件により変更可）
    if not is_admin:
        if customer.status == CustomerStatus.APPROVED.value:
            pass  # allow
        elif customer.status == CustomerStatus.PENDING.value and is_owner:
            pass  # allow (申請者はpending閲覧可)
        else:
            flash("この顧客は未承認のため閲覧できません。", "danger")
            return redirect(url_for("customer.customer_list"))
    if request.method == 'POST':
        customer_code = request.form.get('customer_code', '').strip()
        name = request.form.get('name', '').strip()
        name_kana = request.form.get('name_kana', '').strip()
        postal_code = request.form.get('postal_code', '').strip()
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        transaction_type = request.form.get('transaction_type', '').strip()
        payment_terms = request.form.get('payment_terms', '').strip()
        note = request.form.get('note', '').strip()
        if not name:
            flash('顧客名は必須です', 'danger')
            return render_template('customer_form.html', customer=customer, credit_rows=get_credit_rows(customer.id), is_admin=is_admin, current_user=g.current_user)
        exists = Customer.query.filter(Customer.id != customer.id, Customer.name == name).first()
        if exists:
            flash('同名の顧客が既に存在します', 'danger')
            return render_template('customer_form.html', customer=customer, credit_rows=get_credit_rows(customer.id), is_admin=is_admin, current_user=g.current_user)
        try:
            customer.customer_code = customer_code
            customer.name = name
            customer.name_kana = name_kana
            customer.postal_code = postal_code
            customer.address = address
            customer.phone = phone
            customer.transaction_type = transaction_type
            customer.payment_terms = payment_terms
            customer.note = note

            duplicate_years = upsert_customer_credits(customer.id, request.form)
            db.session.commit()
            if duplicate_years:
                flash(f'同じ年度が複数入力されています: {sorted(list(duplicate_years))}', 'warning')
            flash('顧客情報を更新しました', 'success')
            return redirect(url_for('customer.customer_list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in customer_edit: {e}")
            flash('保存に失敗しました。入力内容を確認してください。', 'danger')
            return render_template('customer_form.html', customer=customer, credit_rows=get_credit_rows(customer.id), is_admin=is_admin, current_user=g.current_user)
    # GET時もcredit_rows, is_admin, current_userを渡す
    return render_template('customer_form.html', customer=customer, credit_rows=get_credit_rows(customer.id), is_admin=is_admin, current_user=g.current_user)

@customer_bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
@roles_required('admin')
def customer_delete(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    used_by_fk = None
    used_by_name = None
    has_fk = hasattr(Quotation, 'customer_id')
    has_name = hasattr(Quotation, 'company_name')
    if has_fk:
        used_by_fk = Quotation.query.filter(Quotation.customer_id == customer.id).first()
    if has_name:
        used_by_name = Quotation.query.filter(Quotation.company_name == customer.name).first()
    if not has_fk and not has_name:
        flash('見積との紐付け情報が無いため安全のため削除できません（管理者に確認してください）', 'danger')
        return redirect(url_for('customer.customer_list'))
    if used_by_fk or used_by_name:
        flash('見積に使用されているため削除できません', 'danger')
        return redirect(url_for('customer.customer_list'))
    db.session.delete(customer)
    db.session.commit()
    flash('顧客を削除しました', 'success')
    return redirect(url_for('customer.customer_list'))


@customer_bp.route('/customers/<int:customer_id>/approve', methods=['POST'])
@login_required
@roles_required('admin')
def customer_approve(customer_id):

    customer = Customer.query.get_or_404(customer_id)
    user = User.query.get(customer.requested_by_user_id)
    if not user:
        abort(400)

    # ユーザー有効化
    user.is_active = 1

    # 承認ログ記録（最小構成）

    approved_by = session.get("user_id")
    if not approved_by:
        abort(401)
    approval_log = CustomerApprovalLog(
        customer_id=customer.id,
        user_id=user.id,
        approved_by=approved_by,
        approved_at=datetime.utcnow()
    )
    db.session.add(approval_log)

    # 顧客ステータス更新
    customer.status = CustomerStatus.APPROVED.value
    customer.approved_by_user_id = session["user_id"]
    customer.approved_at = datetime.utcnow()
    db.session.commit()

    flash('顧客を承認しました（承認ログ記録済み）', 'success')
    return redirect(url_for("customer.customer_list"))

@customer_bp.route('/customers/<int:customer_id>/reject', methods=['POST'])
@login_required
@roles_required('admin')
def customer_reject(customer_id):
    comment = (request.form.get('approval_comment') or request.form.get('comment') or '').strip()
    now = datetime.utcnow()
    # 原子的UPDATEでpending→rejectedのみ更新
    result = db.session.execute(
        text("""
            UPDATE customers SET status=:to_status, approval_comment=:comment, rejected_at=:now, approved_at=NULL, approved_by_user_id=NULL
            WHERE id=:id AND status=:from_status
        """),
        {
            "to_status": CustomerStatus.REJECTED.value,
            "comment": comment,
            "now": now,
            "id": customer_id,
            "from_status": CustomerStatus.PENDING.value
        }
    )
    if result.rowcount == 1:
        # 却下はDBログを取らず、loggerのみ（設計方針どおり）
        current_app.logger.info(f"[REJECT] user_id={g.current_user.id} customer_id={customer_id} pending->rejected")
        db.session.commit()
        # 最新状態取得（404安全化）
        customer = Customer.query.get_or_404(customer_id)
        notify_customer_status_changed(customer, 'reject', g.current_user, comment)
        flash(f"顧客を却下しました（企業名: {customer.name}）", "warning")
        return redirect(url_for('customer.customer_edit', customer_id=customer.id))
    else:
        db.session.rollback()
        flash("既に処理済み、または承認待ちではありません", "warning")
        return redirect(url_for('customer.customer_edit', customer_id=customer_id))

