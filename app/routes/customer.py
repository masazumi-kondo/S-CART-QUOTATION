


from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app
from sqlalchemy import or_

from app import db
from app.decorators import login_required, roles_required
from app.models.customer import Customer, CustomerStatus
from app.models.customer_approval_log import CustomerApprovalLog
from app.models.user import User
from app.models.customer_credit import CustomerCredit
from app.models.quotation import Quotation
from app.services.notifications import notify_customer_status_changed
from app.services.customer_email_notification_service import (
    notify_customer_approval_request,
    notify_customer_approval_result,
)

# Blueprint定義は必ず先
customer_bp = Blueprint('customer', __name__)

# 顧客承認履歴（閲覧専用・管理者のみ）

# 新URL（正規）
@customer_bp.route('/customers/<int:customer_id>/approval_history')
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
        user_ids = {log.approved_by for log in logs if log.approved_by}
        users = User.query.filter(User.id.in_(user_ids)).all()
        user_map = {u.id: u.login_id for u in users}

    return render_template(
        'customer_approval_history.html',
        customer=customer,
        logs=logs,
        user_map=user_map
    )

# 旧URLは新URLへ301リダイレクト
@customer_bp.route('/customers/<int:customer_id>/approval-history')
@login_required
@roles_required('admin')
def customer_approval_history_legacy(customer_id):
    return redirect(url_for('customer.customer_approval_history', customer_id=customer_id), code=301)


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



@customer_bp.route('/customers/pending')
@login_required
@roles_required('admin')
def customer_pending_list():
    q = request.args.get('q', '').strip()
    query = Customer.query.filter(Customer.status == CustomerStatus.PENDING.value)
    if q:
        query = query.filter(or_(Customer.name.contains(q), Customer.name_kana.contains(q)))
    customers = query.order_by(Customer.name).all()

    # 申請者（requested_by_user_id）のlogin_idを引く（最小）
    user_map = {}
    try:
        ids = {c.requested_by_user_id for c in customers if getattr(c, "requested_by_user_id", None)}
        if ids:
            users = User.query.filter(User.id.in_(ids)).all()
            user_map = {u.id: u.login_id for u in users}
    except Exception:
        user_map = {}

    return render_template(
        'customer_pending_list.html',
        customers=customers,
        q=q,
        current_user=g.current_user,
        user_map=user_map
    )

@customer_bp.route('/customers')
@login_required
def customer_list():
    current_app.logger.info("[ROUTE] /customers called")
    q = request.args.get('q', '').strip()
    query = Customer.query
    if q:
        query = query.filter(or_(Customer.name.contains(q), Customer.name_kana.contains(q)))
    # 一般ユーザーはapprovedのみ、管理者は全件
    role = getattr(g.current_user, 'role', None)
    is_admin = role == 'admin'
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
                status=CustomerStatus.PENDING.value,  # 必ずpendingで保存
                requested_by_user_id=g.current_user.id,
                # approved_by, approved_at, rejected_reasonは触らない
            )
            db.session.add(customer)
            db.session.flush()  # Allocate customer.id without committing

            # 与信3項目はupsert_customer_creditsで保存（空欄はNoneになる）
            duplicate_years = upsert_customer_credits(customer.id, request.form)
            db.session.commit()
            
            # Send approval request email to admins
            mail_ok = notify_customer_approval_request(customer)
            
            if duplicate_years:
                flash(f'同じ年度が複数入力されています: {sorted(list(duplicate_years))}', 'warning')
            
            if mail_ok:
                flash('顧客を登録しました（承認待ち）。管理者へ承認依頼メールを送信しました。', 'success')
            else:
                flash('顧客を登録しました（承認待ち）。承認依頼メールは送信されていない可能性があります。', 'warning')
            
            # For mailto provider, show completion screen with mailto URL
            if current_app.config.get("MAIL_PROVIDER") == "mailto":
                from app.services.customer_mailto_service import build_customer_approval_request_mailto
                mailto_url = build_customer_approval_request_mailto(customer)
                return render_template(
                    "customers/customer_created.html",
                    customer=customer,
                    approval_request_mailto_url=mailto_url
                )
            
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
    role = getattr(g.current_user, "role", None)
    is_admin = role == "admin"
    requested_by = getattr(customer, "requested_by_user_id", None)
    is_owner = (requested_by is not None) and (requested_by == getattr(g.current_user, "id", None))
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
    latest_log = None
    requester_login_id = None
    if is_admin:
        latest_log = (
            CustomerApprovalLog.query
            .filter(CustomerApprovalLog.customer_id == customer.id)
            .order_by(CustomerApprovalLog.approved_at.desc())
            .first()
        )
        rid = getattr(customer, "requested_by_user_id", None)
        if rid:
            u = db.session.get(User, rid)
            requester_login_id = (u.login_id if u else None)
    return render_template(
        'customer_form.html',
        customer=customer,
        credit_rows=get_credit_rows(customer.id),
        is_admin=is_admin,
        current_user=g.current_user,
        latest_log=latest_log,
        requester_login_id=requester_login_id
    )

@customer_bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
@roles_required('admin')
def customer_delete(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    used_by_fk = None
    used_by_name = None
    try:
        if hasattr(Quotation, "customer_id"):
            used_by_fk = Quotation.query.filter(Quotation.customer_id == customer.id).first()
        if hasattr(Quotation, "company_name"):
            used_by_name = Quotation.query.filter(Quotation.company_name == customer.name).first()
    except Exception as e:
        current_app.logger.exception("[DELETE] quotation relation check failed: %s", e)
        flash("見積との関連確認に失敗しました（管理者に確認してください）", "danger")
        return redirect(url_for("customer.customer_list"))
    if (hasattr(Quotation, "customer_id") and used_by_fk) or (hasattr(Quotation, "company_name") and used_by_name):
        flash('見積に使用されているため削除できません', 'danger')
        return redirect(url_for('customer.customer_list'))
    db.session.delete(customer)
    db.session.commit()
    flash('顧客を削除しました', 'success')
    return redirect(url_for('customer.customer_list'))




# --- robust approval log insert (model-diff-absorbing) ---
def _safe_add_approval_log(**kwargs) -> bool:
    try:
        table = getattr(CustomerApprovalLog, "__table__", None)
        if table is None:
            return False
        cols = {c.name for c in table.columns}
        data = {k: v for k, v in kwargs.items() if k in cols}
        if data:
            db.session.add(CustomerApprovalLog(**data))
            return True
    except Exception:
        pass
    return False

@customer_bp.route('/customers/<int:customer_id>/approve', methods=['POST'])
@login_required
@roles_required('admin')
def customer_approve(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    if customer.status != CustomerStatus.PENDING.value:
        flash('この顧客は承認待ちではありません', 'warning')
        return redirect(url_for('customer.customer_pending_list'))

    customer.status = CustomerStatus.APPROVED.value
    customer.approved_by = g.current_user.id
    customer.approved_at = datetime.utcnow().isoformat()
    customer.rejected_reason = None

    # 先に顧客の更新だけ commit（ここは必ず通したい）
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("[APPROVE] customer update commit failed: %s", e)
        flash("承認処理に失敗しました（DB更新）。", "danger")
        return redirect(url_for("customer.customer_pending_list"))

    # 監査ログは別トランザクションで、失敗しても承認は成功扱いにする
    try:
        added = _safe_add_approval_log(
            customer_id=customer.id,
            user_id=getattr(customer, "requested_by_user_id", None) or g.current_user.id,
            approved_by=g.current_user.id,
            approved_at=datetime.utcnow(),
            action="approve",
            comment=None,
            actor_user_id=g.current_user.id,
            actor_username=getattr(g.current_user, "login_id", None),
            actor_role=getattr(g.current_user, "role", None),
            ip_addr=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        if added:
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("[APPROVE] approval log commit failed (ignored): %s", e)

    try:
        customer = db.session.get(Customer, customer.id)
        if customer:
            try:
                notify_customer_status_changed(customer)
            except TypeError:
                # 多引数版だった場合のフォールバック
                notify_customer_status_changed(customer, "approve", g.current_user, None)
    except Exception:
        pass

    # Send approval result email to applicant
    mail_ok = notify_customer_approval_result(customer, "承認", None)
    
    if mail_ok:
        flash(f'顧客を承認しました（企業名: {customer.name}）。申請者へ承認結果メールを送信しました。', 'success')
    else:
        flash(f'顧客を承認しました（企業名: {customer.name}）。承認結果メールは送信されていない可能性があります。', 'warning')
    
    # For mailto provider, show completion screen with mailto URL
    mail_provider = current_app.config.get("MAIL_PROVIDER")
    current_app.logger.info(f"[APPROVE] MAIL_PROVIDER={mail_provider}, checking for mailto rendering")
    
    if mail_provider == "mailto":
        current_app.logger.info(f"[APPROVE] Using mailto provider, rendering completion screen")
        from app.services.customer_mailto_service import build_customer_approval_result_mailto
        mailto_url = build_customer_approval_result_mailto(customer, "承認", None)
        current_app.logger.info(f"[APPROVE] mailto_url={mailto_url}")
        return render_template(
            "customers/customer_approval_completed.html",
            customer=customer,
            result_label="承認",
            result_comment=None,
            result_mailto_url=mailto_url
        )
    
    current_app.logger.info(f"[APPROVE] Not using mailto provider, redirecting to pending list")
    return redirect(url_for('customer.customer_pending_list'))

@customer_bp.route('/customers/<int:customer_id>/reject', methods=['POST'])
@login_required
@roles_required('admin')
def customer_reject(customer_id):
    comment = (request.form.get('reason') or '').strip()
    if not comment:
        flash('却下理由は必須です。', 'danger')
        return redirect(url_for('customer.customer_pending_list'))

    customer = Customer.query.get_or_404(customer_id)

    if customer.status != CustomerStatus.PENDING.value:
        flash('この顧客は承認待ちではありません', 'warning')
        return redirect(url_for('customer.customer_pending_list'))

    customer.status = CustomerStatus.REJECTED.value
    customer.rejected_reason = comment
    customer.approved_by = g.current_user.id
    customer.approved_at = datetime.utcnow().isoformat()

    # 先に顧客の更新だけ commit（ここは必ず通したい）
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("[REJECT] customer update commit failed: %s", e)
        flash("却下処理に失敗しました（DB更新）。", "danger")
        return redirect(url_for("customer.customer_pending_list"))

    # 監査ログは別トランザクションで、失敗しても却下は成功扱いにする
    try:
        added = _safe_add_approval_log(
            customer_id=customer.id,
            user_id=getattr(customer, "requested_by_user_id", None) or g.current_user.id,
            approved_by=g.current_user.id,
            approved_at=datetime.utcnow(),
            action="reject",
            comment=comment,
            actor_user_id=g.current_user.id,
            actor_username=getattr(g.current_user, "login_id", None),
            actor_role=getattr(g.current_user, "role", None),
            ip_addr=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        if added:
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("[REJECT] approval log commit failed (ignored): %s", e)

    try:
        customer = db.session.get(Customer, customer.id)
        if customer:
            try:
                notify_customer_status_changed(customer)
            except TypeError:
                # 多引数版だった場合のフォールバック
                notify_customer_status_changed(customer, "reject", g.current_user, comment)
    except Exception:
        pass

    # Send rejection result email to applicant
    mail_ok = notify_customer_approval_result(customer, "却下", comment)
    
    if mail_ok:
        flash(f'顧客を却下しました（企業名: {customer.name}）。申請者へ却下結果メールを送信しました。', 'success')
    else:
        flash(f'顧客を却下しました（企業名: {customer.name}）。却下結果メールは送信されていない可能性があります。', 'warning')
    
    # For mailto provider, show completion screen with mailto URL
    if current_app.config.get("MAIL_PROVIDER") == "mailto":
        from app.services.customer_mailto_service import build_customer_approval_result_mailto
        mailto_url = build_customer_approval_result_mailto(customer, "却下", comment)
        return render_template(
            "customers/customer_approval_completed.html",
            customer=customer,
            result_label="却下",
            result_comment=comment,
            result_mailto_url=mailto_url
        )
    
    return redirect(url_for('customer.customer_pending_list'))


# 顧客マスタ検索・選択画面（見積作成時に使用）
@customer_bp.route('/customers/select', methods=['GET'])
def customer_select():
    """
    顧客マスタ検索・選択画面
    - キーワード検索で承認済み顧客をフィルタリング
    - 選択時に見積作成画面に戻り、customer_id・company_name・payment_terms を渡す
    """
    keyword = request.args.get('q', '').strip()

    # ベースクエリ: 承認済み顧客のみ
    query = Customer.query.filter(Customer.status == CustomerStatus.APPROVED.value)

    # キーワード検索
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                Customer.name.ilike(like),
                Customer.name_kana.ilike(like)
            )
        )

    # 顧客マスタの支払条件関連をロード
    from sqlalchemy.orm import joinedload
    query = query.options(joinedload(Customer.payment_term_ref))
    
    customers = query.order_by(Customer.name.asc()).limit(50).all()

    # 見積作成画面から持ってきた値を保持（選択時に引き継ぐ）
    carry_params = dict(request.args)
    carry_params.pop('q', None)

    return render_template(
        'customer_select.html',
        customers=customers,
        keyword=keyword,
        carry_params=carry_params
    )

