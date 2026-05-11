from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.models.user import User
from app.models.v2_calculation_setting import V2CalculationSetting
from app import db
from app.auth_utils import login_required, roles_required

admin_bp = Blueprint("admin", __name__)

# Watch fields for debugging V2 reset issues
WATCH_FIELDS = [
    "cost_hourly_rate",
    "sell_hourly_rate",
    "design_base_hours",
    "setup_base_hours",
    "design_vehicle_hours",
    "setup_vehicle_hours",
    "design_pattern_hours",
    "setup_pattern_hours",
    "setup_layout_scale_hours",
    "route_factor_simple",
    "route_factor_standard",
    "route_factor_complex",
    "route_factor_unknown",
    "merge_factor_low",
    "merge_factor_standard",
    "merge_factor_high",
    "merge_factor_unknown",
    "vehicle_factor_one",
    "vehicle_factor_two",
    "vehicle_factor_three",
    "vehicle_factor_four_or_more",
    "design_charger_hours",
    "setup_charger_hours",
    "design_magnetic_stop_hours",
    "setup_magnetic_stop_hours",
    "landmark_factor_small",
    "landmark_factor_medium",
    "landmark_factor_large",
    "landmark_factor_full",
    "landmark_factor_unknown",
    "design_landmark_hours",
    "setup_landmark_hours",
    "design_elevator_hours",
    "setup_elevator_hours",
    "design_auto_door_hours",
    "setup_auto_door_hours",
    "design_plc_signal_hours",
    "setup_plc_signal_hours",
    "plc_small_value",
    "plc_medium_value",
    "plc_large_value",
    "design_host_system_medium_hours",
    "setup_host_system_medium_hours",
]

def snapshot(setting):
    """Create a snapshot of watched fields for comparison"""
    return {f: getattr(setting, f, None) for f in WATCH_FIELDS}

def diff(before, after):
    """Find differences between two snapshots"""
    return {k: (before[k], after[k]) for k in before if before[k] != after[k]}


def _to_float(value, default):
    """Convert value to float safely"""
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def _to_int(value, default):
    """Convert value to int safely"""
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


@admin_bp.route("/admin/v2-parameters", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def v2_parameters():
    """Manage V2 calculation parameters (admin only)"""
    # Get or create default settings
    setting = V2CalculationSetting.query.get(1)
    if not setting:
        setting = V2CalculationSetting(id=1)
        db.session.add(setting)
        db.session.commit()

    # Debug logging: Show initial state
    print("[V2 PARAM GET START]", snapshot(setting))

    if request.method == "POST":
        # Normal save action only - reset is handled by dedicated route
        # 賃率
        setting.cost_hourly_rate = _to_float(request.form.get("cost_hourly_rate"), 17760)
        setting.sell_hourly_rate = _to_float(request.form.get("sell_hourly_rate"), 29600)

        # 基本工数
        setting.design_base_hours = _to_float(request.form.get("design_base_hours"), 8)
        setting.setup_base_hours = _to_float(request.form.get("setup_base_hours"), 8)

        # AGV台数
        setting.design_vehicle_hours = _to_float(request.form.get("design_vehicle_hours"), 2)
        setting.setup_vehicle_hours = _to_float(request.form.get("setup_vehicle_hours"), 4)

        # パターンスコア
        setting.design_pattern_hours = _to_float(request.form.get("design_pattern_hours"), 3)
        setting.setup_pattern_hours = _to_float(request.form.get("setup_pattern_hours"), 4)

        # レイアウト規模
        setting.setup_layout_scale_hours = _to_float(request.form.get("setup_layout_scale_hours"), 1.5)

        # 搬送ルート複雑さ係数
        setting.route_factor_simple = _to_float(request.form.get("route_factor_simple"), 1.0)
        setting.route_factor_standard = _to_float(request.form.get("route_factor_standard"), 1.5)
        setting.route_factor_complex = _to_float(request.form.get("route_factor_complex"), 2.3)
        setting.route_factor_unknown = _to_float(request.form.get("route_factor_unknown"), 1.6)

        # すれ違い・合流係数
        setting.merge_factor_low = _to_float(request.form.get("merge_factor_low"), 0.8)
        setting.merge_factor_standard = _to_float(request.form.get("merge_factor_standard"), 1.3)
        setting.merge_factor_high = _to_float(request.form.get("merge_factor_high"), 2.0)
        setting.merge_factor_unknown = _to_float(request.form.get("merge_factor_unknown"), 1.4)

        # AGV台数補正
        setting.vehicle_factor_one = _to_float(request.form.get("vehicle_factor_one"), 1.0)
        setting.vehicle_factor_two = _to_float(request.form.get("vehicle_factor_two"), 1.4)
        setting.vehicle_factor_three = _to_float(request.form.get("vehicle_factor_three"), 1.8)
        setting.vehicle_factor_four_or_more = _to_float(request.form.get("vehicle_factor_four_or_more"), 2.2)

        # 現地設置・補正
        setting.design_charger_hours = _to_float(request.form.get("design_charger_hours"), 1.0)
        setting.setup_charger_hours = _to_float(request.form.get("setup_charger_hours"), 2.0)
        setting.design_magnetic_stop_hours = _to_float(request.form.get("design_magnetic_stop_hours"), 0.5)
        setting.setup_magnetic_stop_hours = _to_float(request.form.get("setup_magnetic_stop_hours"), 1.0)

        # ランドマーク係数
        setting.landmark_factor_small = _to_float(request.form.get("landmark_factor_small"), 1.0)
        setting.landmark_factor_medium = _to_float(request.form.get("landmark_factor_medium"), 1.8)
        setting.landmark_factor_large = _to_float(request.form.get("landmark_factor_large"), 2.8)
        setting.landmark_factor_full = _to_float(request.form.get("landmark_factor_full"), 4.0)
        setting.landmark_factor_unknown = _to_float(request.form.get("landmark_factor_unknown"), 2.2)

        # ランドマーク工数換算
        setting.design_landmark_hours = _to_float(request.form.get("design_landmark_hours"), 1.0)
        setting.setup_landmark_hours = _to_float(request.form.get("setup_landmark_hours"), 4.0)

        # 設備連携
        setting.design_elevator_hours = _to_float(request.form.get("design_elevator_hours"), 4.0)
        setting.setup_elevator_hours = _to_float(request.form.get("setup_elevator_hours"), 5.0)
        setting.design_auto_door_hours = _to_float(request.form.get("design_auto_door_hours"), 2.0)
        setting.setup_auto_door_hours = _to_float(request.form.get("setup_auto_door_hours"), 3.0)
        setting.design_plc_signal_hours = _to_float(request.form.get("design_plc_signal_hours"), 1.2)
        setting.setup_plc_signal_hours = _to_float(request.form.get("setup_plc_signal_hours"), 1.5)

        # PLCレンジ
        setting.plc_none_value = _to_int(request.form.get("plc_none_value"), 0)
        setting.plc_small_min = _to_int(request.form.get("plc_small_min"), 1)
        setting.plc_small_max = _to_int(request.form.get("plc_small_max"), 5)
        setting.plc_small_value = _to_int(request.form.get("plc_small_value"), 3)
        setting.plc_medium_min = _to_int(request.form.get("plc_medium_min"), 6)
        setting.plc_medium_max = _to_int(request.form.get("plc_medium_max"), 15)
        setting.plc_medium_value = _to_int(request.form.get("plc_medium_value"), 10)
        setting.plc_large_min = _to_int(request.form.get("plc_large_min"), 16)
        setting.plc_large_max = _to_int(request.form.get("plc_large_max"), 30)
        setting.plc_large_value = _to_int(request.form.get("plc_large_value"), 20)
        setting.plc_unknown_value = _to_int(request.form.get("plc_unknown_value"), 6)

        # 上位システム連携
        setting.design_host_system_none_hours = _to_float(request.form.get("design_host_system_none_hours"), 0.0)
        setting.setup_host_system_none_hours = _to_float(request.form.get("setup_host_system_none_hours"), 0.0)
        setting.design_host_system_small_hours = _to_float(request.form.get("design_host_system_small_hours"), 4.0)
        setting.setup_host_system_small_hours = _to_float(request.form.get("setup_host_system_small_hours"), 4.0)
        setting.design_host_system_medium_hours = _to_float(request.form.get("design_host_system_medium_hours"), 8.0)
        setting.setup_host_system_medium_hours = _to_float(request.form.get("setup_host_system_medium_hours"), 8.0)
        setting.design_host_system_large_hours = _to_float(request.form.get("design_host_system_large_hours"), 16.0)
        setting.setup_host_system_large_hours = _to_float(request.form.get("setup_host_system_large_hours"), 16.0)

        db.session.commit()
        flash("見積パラメーターを保存しました。", "success")
        return redirect(url_for("admin.v2_parameters"))

    return render_template("admin/v2_parameters.html", setting=setting)


@admin_bp.route("/admin/v2-parameters/reset/<section_key>", methods=["POST"])
@login_required
@roles_required("admin")
def reset_v2_parameter_section(section_key):
    """Reset a specific V2 parameter section to defaults (admin only)"""
    setting = V2CalculationSetting.query.get(1)
    if not setting:
        setting = V2CalculationSetting(id=1)
        db.session.add(setting)
        db.session.commit()

    section_names = {
        "base_hours": "基本工数",
        "vehicle_hours": "AGV台数係数",
        "pattern_hours": "パターンスコア係数",
        "layout_scale": "走行エリア規模係数",
        "route_factors": "搬送ルート複雑さ係数",
        "merge_factors": "すれ違い・合流係数",
        "vehicle_factors": "AGV台数補正係数",
        "site_adjustment": "現地設置・補正係数",
        "landmark": "ランドマーク係数",
        "integration": "設備連携係数",
        "plc_ranges": "PLC/設備連携規模レンジ",
        "host_system": "上位システム連携係数",
    }

    # Debug logging: Before reset
    before = snapshot(setting)
    print(f"[V2 RESET] section_key = {section_key}")
    print(f"[V2 RESET] before = {before}")

    if setting.reset_section_to_defaults(section_key):
        db.session.commit()
        
        # Debug logging: After reset and commit
        after = snapshot(setting)
        diff_result = diff(before, after)
        print(f"[V2 RESET] after_commit = {after}")
        print(f"[V2 RESET] diff = {diff_result}")
        
        section_name = section_names.get(section_key, section_key)
        flash(f"{section_name}をデフォルト値に戻しました。", "success")
    else:
        flash("対象セクションが見つかりませんでした。", "danger")

    return redirect(url_for("admin.v2_parameters"))


