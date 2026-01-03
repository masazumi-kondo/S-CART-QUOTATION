

from flask import Blueprint, render_template, session, redirect, url_for, g
from app.decorators import login_required
from app.models.customer import Customer


main_bp = Blueprint('main', __name__)


@main_bp.route("/")
@login_required
def index():
    # すべてのユーザーで index.html（中央メニュー統一）を表示
    return render_template("index.html", current_user=g.current_user)
