

# --- v6 JSロジックと同じ設計/セットアップ費用計算 ---
import math

LABOR_RATE = 7920
DESIGN_SELL_RATE = 15000
SETUP_SELL_RATE = 15000

def _safe_float(value):
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0

def calc_design_hours_from_params(distance, intersections, stations, vehicle_count):
    distance        = _safe_float(distance)
    intersections   = _safe_float(intersections)
    stations        = _safe_float(stations)
    vehicle_count   = _safe_float(vehicle_count)

    design_hours_base = (
        vehicle_count * intersections * 2.0
        + stations * 1.0
        + distance / 100.0
    )
    design_hours_raw = design_hours_base * 1.1  # 安全率
    return design_hours_raw

def calc_setup_hours_from_params(distance, intersections, stations, vehicle_count):
    distance        = _safe_float(distance)
    intersections   = _safe_float(intersections)
    stations        = _safe_float(stations)
    vehicle_count   = _safe_float(vehicle_count)

    # AGV速度・CT
    speed = 30.0  # m/min
    ct_min = distance / speed + 0.1 * stations

    # 試運転
    trial_count = 10.0 * vehicle_count
    trial_hours = (ct_min * trial_count) / 60.0

    # バグ修正
    bug_fix_hours = 1.0 * trial_count

    # インターロック
    interlock_hours = 0.1 * vehicle_count * intersections * stations

    base_hours = trial_hours + bug_fix_hours + interlock_hours
    base_hours_with_safety = base_hours * 1.1

    # 人数ロジック
    workers = 3.0
    if vehicle_count <= 1 and distance <= 50:
        workers = 1.0
    elif 2 <= vehicle_count <= 5 and distance <= 100:
        workers = 2.0

    setup_hours_raw = base_hours_with_safety * workers
    return setup_hours_raw

def calc_design_setup_for_quotation(quotation):
    """
    Quotation インスタンスから走行パラメータを読み取り、
    JS と同じロジックで設計/セットアップの工数・原価・売価・利益率を計算する。
    """
    distance      = getattr(quotation, "distance_m", 0)
    intersections = getattr(quotation, "intersection_count", 0)
    stations      = getattr(quotation, "station_count", 0)
    vehicle_count = getattr(quotation, "vehicle_count", 0)

    # 設計
    design_hours_raw = calc_design_hours_from_params(
        distance=distance,
        intersections=intersections,
        stations=stations,
        vehicle_count=vehicle_count,
    )
    design_hours = math.ceil(design_hours_raw)
    design_cost  = design_hours * LABOR_RATE
    design_fee   = design_hours * DESIGN_SELL_RATE
    design_profit_rate = (
        (design_fee - design_cost) / design_fee * 100.0 if design_fee > 0 else 0.0
    )

    # セットアップ
    setup_hours_raw = calc_setup_hours_from_params(
        distance=distance,
        intersections=intersections,
        stations=stations,
        vehicle_count=vehicle_count,
    )
    setup_hours = math.ceil(setup_hours_raw)
    setup_cost  = setup_hours * LABOR_RATE
    setup_fee   = setup_hours * SETUP_SELL_RATE
    setup_profit_rate = (
        (setup_fee - setup_cost) / setup_fee * 100.0 if setup_fee > 0 else 0.0
    )


# --- フォームパラメータから計算する用: JS v6ロジック互換 ---
def calc_design_and_setup_amounts(param_dict):
    """
    見積作成画面で使う「設計費・セットアップ費」を計算する。
    引数:
        param_dict: dict
            distance_m, intersection_count, station_count, vehicle_count
            などのキーを持つ辞書。
    戻り値:
        (design_fee, design_cost, design_hours,
         setup_fee,  setup_cost,  setup_hours)
    """

    # 呼び出し側のキー名の揺れを吸収
    distance      = param_dict.get("distance_m", param_dict.get("distance", 0))
    intersections = param_dict.get("intersection_count", param_dict.get("intersections", 0))
    stations      = param_dict.get("station_count", param_dict.get("stations", 0))
    vehicle_count = param_dict.get("vehicle_count", param_dict.get("vehicles", 0))

    distance_f      = _safe_float(distance)
    intersections_f = _safe_float(intersections)
    stations_f      = _safe_float(stations)
    vehicle_count_f = _safe_float(vehicle_count)

    # --- 設計 ---
    design_hours_raw = calc_design_hours_from_params(
        distance=distance_f,
        intersections=intersections_f,
        stations=stations_f,
        vehicle_count=vehicle_count_f,
    )
    design_hours = math.ceil(design_hours_raw)
    design_cost  = design_hours * LABOR_RATE
    design_fee   = design_hours * DESIGN_SELL_RATE

    # --- セットアップ ---
    setup_hours_raw = calc_setup_hours_from_params(
        distance=distance_f,
        intersections=intersections_f,
        stations=stations_f,
        vehicle_count=vehicle_count_f,
    )
    setup_hours = math.ceil(setup_hours_raw)
    setup_cost  = setup_hours * LABOR_RATE
    setup_fee   = setup_hours * SETUP_SELL_RATE

    # quotation_new 側のアンパックを壊さないため、この順序で返す
    return (
        design_fee,
        design_cost,
        design_hours,
        setup_fee,
        setup_cost,
        setup_hours,
    )

    return {
        "design_hours": design_hours,
        "design_cost": design_cost,
        "design_fee": design_fee,
        "design_profit_rate": design_profit_rate,
        "setup_hours": setup_hours,
        "setup_cost": setup_cost,
        "setup_fee": setup_fee,
        "setup_profit_rate": setup_profit_rate,
    }
