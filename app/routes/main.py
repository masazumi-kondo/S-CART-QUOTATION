

from flask import Blueprint, render_template, session, redirect, url_for, g
from app.decorators import login_required
from app.models.customer import Customer


main_bp = Blueprint('main', __name__)


@main_bp.route("/")
@login_required
def index():
    pending_count = 0
    if g.current_user and g.current_user.role == "admin":
        pending_count = Customer.query.filter(Customer.status == "pending").count()
        return render_template("main_menu.html")
