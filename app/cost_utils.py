

import math
from typing import Any, Dict, Tuple

# -----------------------------
# Common rates (current policy)
# -----------------------------
LABOR_RATE = 7920
DESIGN_SELL_RATE = 15000
SETUP_SELL_RATE = 15000


# -----------------------------
# Safe parsers
# -----------------------------
def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        s = str(value).strip()
        if s == "":
            return default
        return float(s)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        s = str(value).strip()
        if s == "":
            return default
        return int(float(s))
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any) -> bool:
    s = ("" if value is None else str(value)).strip().lower()
    return s in ("1", "true", "yes", "y", "on")


def _norm_calc_mode(v: Any) -> str:
    s = ("" if v is None else str(v)).strip().lower()
    # official/rough regime（旧値は official に吸収）
    if s in ("official", "new_v1", "legacy", ""):
        return "official"
    if s in ("rough", "estimate", "approx"):
        return "rough"
    return "official"


def _norm_difficulty(v: Any, default: str = "medium") -> str:
    s = ("" if v is None else str(v)).strip().lower()
    return s if s in ("medium", "high") else default




# -----------------------------
# new_v1 (pattern-weighted v1)
#  - calibration will tune COEF_V1 later
# -----------------------------
COEF_V1: Dict[str, float] = {
    # Design baseline / weights
    "design_base_hours": 8.0,                 # fixed overhead
    "design_per_intersection": 1.4,           # per intersection per vehicle/zone concept
    "design_per_station": 0.7,                # per station block
    "design_per_vehicle": 1.2,                # per vehicle integration
    "design_distance_per_100m": 0.2,          # routing config overhead
    "design_high_multiplier": 1.35,           # difficulty=high

    # Setup baseline / test-case weights
    "setup_base_hours": 10.0,                 # travel/setup overhead
    "test_case_time_hours": 0.18,             # hours per test case (10.8min) (will be calibrated)
    "bugfix_per_case_hours": 0.06,            # hours per case (3.6min)
    "record_per_case_hours": 0.02,            # hours per case (1.2min)
    "safety_factor": 1.10,

    # Pattern weights (relative)
    "w_intersection_case": 1.00,              # per (vehicle x entry-dir) x intersection
    "w_station_auto": 1.00,
    "w_station_manual": 1.80,                 # human handover heavier
    "w_station_relay": 1.30,
    "w_station_charge": 0.60,
    "w_wait_position": 0.40,

    # Feature multipliers
    "mult_swap_operation": 1.20,
    "mult_plc_handshake": 1.15,
    "mult_ev_integration": 1.10,
    "setup_high_multiplier": 1.30,            # difficulty=high

    # Workers scaling (kept compatible style; can be tuned)
    "workers_default": 3.0,
    "workers_small": 1.0,
    "workers_mid": 2.0,
}


def _workers_from_legacy_like(distance_m: float, vehicle_count: int) -> float:
    # Keep existing behavior to avoid surprises (tune later if needed)
    workers = COEF_V1["workers_default"]
    if vehicle_count <= 1 and distance_m <= 50:
        workers = COEF_V1["workers_small"]
    elif 2 <= vehicle_count <= 5 and distance_m <= 100:
        workers = COEF_V1["workers_mid"]
    return float(workers)


def calc_design_hours_v1(params: Dict[str, Any]) -> float:
    distance_m = _safe_float(params.get("distance_m", 0))
    intersections = _safe_int(params.get("intersection_count", 0))
    # station_count is display-level; prefer sum of station_* if present
    st_auto = _safe_int(params.get("station_auto", 0))
    st_manual = _safe_int(params.get("station_manual", 0))
    st_relay = _safe_int(params.get("station_relay", 0))
    st_charge = _safe_int(params.get("station_charge", 0))
    stations_total = st_auto + st_manual + st_relay + st_charge
    if stations_total <= 0:
        stations_total = _safe_int(params.get("station_count", 0))

    vehicle_count = _safe_int(params.get("vehicle_count", 0))
    difficulty = _norm_difficulty(params.get("difficulty_design"), default="medium")

    base = COEF_V1["design_base_hours"]
    base += COEF_V1["design_per_vehicle"] * max(vehicle_count, 0)
    base += COEF_V1["design_per_intersection"] * max(intersections, 0) * max(vehicle_count, 1)
    base += COEF_V1["design_per_station"] * max(stations_total, 0)
    base += COEF_V1["design_distance_per_100m"] * (max(distance_m, 0.0) / 100.0)

    if difficulty == "high":
        base *= COEF_V1["design_high_multiplier"]

    # safety factor
    return base * COEF_V1["safety_factor"]


def estimate_test_cases_v1(params: Dict[str, Any]) -> float:
    """
    Pattern-weighted test case count.
    Emphasis: intersection patterns (vehicle x entry-dir combinations) and station types/human handover.
    """
    vehicle_count = _safe_int(params.get("vehicle_count", 0))
    intersections = _safe_int(params.get("intersection_count", 0))

    avg_entry_dirs = _safe_float(params.get("avg_entry_dirs", 3.0), default=3.0)
    if avg_entry_dirs <= 0:
        avg_entry_dirs = 3.0

    st_auto = _safe_int(params.get("station_auto", 0))
    st_manual = _safe_int(params.get("station_manual", 0))
    st_relay = _safe_int(params.get("station_relay", 0))
    st_charge = _safe_int(params.get("station_charge", 0))
    wait_pos = _safe_int(params.get("wait_position_count", 0))

    # Intersection patterns: (vehicles x entry directions) per intersection
    # Weight is key per your instruction.
    intersection_cases = (
        max(vehicle_count, 0)
        * max(intersections, 0)
        * max(avg_entry_dirs, 1.0)
        * COEF_V1["w_intersection_case"]
    )

    # Station patterns
    station_cases = 0.0
    station_cases += st_auto * COEF_V1["w_station_auto"]
    station_cases += st_manual * COEF_V1["w_station_manual"]
    station_cases += st_relay * COEF_V1["w_station_relay"]
    station_cases += st_charge * COEF_V1["w_station_charge"]
    station_cases += wait_pos * COEF_V1["w_wait_position"]

    cases = intersection_cases + station_cases

    # Feature multipliers
    if _safe_bool(params.get("has_swap_operation")):
        cases *= COEF_V1["mult_swap_operation"]
    if _safe_bool(params.get("has_plc_handshake")):
        cases *= COEF_V1["mult_plc_handshake"]
    if _safe_bool(params.get("has_ev_integration")):
        cases *= COEF_V1["mult_ev_integration"]

    return max(cases, 0.0)


def calc_setup_hours_v1(params: Dict[str, Any]) -> float:
    distance_m = _safe_float(params.get("distance_m", 0))
    vehicle_count = _safe_int(params.get("vehicle_count", 0))
    difficulty = _norm_difficulty(params.get("difficulty_setup"), default="medium")

    cases = estimate_test_cases_v1(params)

    base = COEF_V1["setup_base_hours"]
    base += cases * COEF_V1["test_case_time_hours"]
    base += cases * COEF_V1["bugfix_per_case_hours"]
    base += cases * COEF_V1["record_per_case_hours"]

    if difficulty == "high":
        base *= COEF_V1["setup_high_multiplier"]

    base *= COEF_V1["safety_factor"]

    workers = _workers_from_legacy_like(distance_m=distance_m, vehicle_count=vehicle_count)
    return base * workers


def _hours_to_money(hours_raw: float, sell_rate: float) -> Tuple[int, int, int]:
    """
    returns (fee, cost, hours_int)
    """
    h = int(math.ceil(max(hours_raw, 0.0)))
    cost = int(h * LABOR_RATE)
    fee = int(h * sell_rate)
    return fee, cost, h


# -----------------------------
# Public APIs used by quotation.py
# -----------------------------
def calc_design_and_setup_amounts(param_dict: Dict[str, Any], calc_mode: str = "official"):
    """
    設計費・現地セットアップ費の計算本体
    - official: 現行 new_v1 ロジック（動作パターン/ST種別）をここで実装・維持
    - rough: 未実装のため当面 official を流用（将来ここに概算ロジックを追加）
    戻り値: (design_fee, design_cost, design_hours, setup_fee, setup_cost, setup_hours)
    """
    mode = _norm_calc_mode(calc_mode)

    # --- rough は未実装：当面 official にフォールバック ---
    if mode == "rough":
        mode = "official"

    # ここから先は「official」＝現行ロジックのまま
    # 入力正規化
    def _to_int(v):
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        try:
            return int(float(s))
        except Exception:
            return None

    def _to_float(v):
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        try:
            return float(s)
        except Exception:
            return None

    def _to_bool(v):
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "y", "on")

    def _norm_difficulty(v):
        s = (v or "").strip().lower()
        return s if s in ("medium", "high") else None

    distance_m = _to_float(param_dict.get("distance_m"))
    intersection_count = _to_int(param_dict.get("intersection_count"))
    station_count = _to_int(param_dict.get("station_count"))
    vehicle_count = _to_int(param_dict.get("vehicle_count"))
    equipment_count = _to_int(param_dict.get("equipment_count"))
    circuit_difficulty = _to_int(param_dict.get("circuit_difficulty"))

    avg_entry_dirs = _to_float(param_dict.get("avg_entry_dirs"))
    station_auto = _to_int(param_dict.get("station_auto"))
    station_manual = _to_int(param_dict.get("station_manual"))
    station_relay = _to_int(param_dict.get("station_relay"))
    station_charge = _to_int(param_dict.get("station_charge"))
    wait_position_count = _to_int(param_dict.get("wait_position_count"))
    has_swap_operation = _to_bool(param_dict.get("has_swap_operation"))
    has_plc_handshake = _to_bool(param_dict.get("has_plc_handshake"))
    has_ev_integration = _to_bool(param_dict.get("has_ev_integration"))
    difficulty_design = _norm_difficulty(param_dict.get("difficulty_design"))
    difficulty_setup = _norm_difficulty(param_dict.get("difficulty_setup"))

    params = {
        "distance_m": distance_m,
        "intersection_count": intersection_count,
        "station_auto": station_auto,
        "station_manual": station_manual,
        "station_relay": station_relay,
        "station_charge": station_charge,
        "vehicle_count": vehicle_count,
        "avg_entry_dirs": avg_entry_dirs,
        "wait_position_count": wait_position_count,
        "has_swap_operation": has_swap_operation,
        "has_plc_handshake": has_plc_handshake,
        "has_ev_integration": has_ev_integration,
        "difficulty_design": difficulty_design,
        "difficulty_setup": difficulty_setup,
    }
    design_hours_raw = calc_design_hours_v1(params)
    design_fee, design_cost, design_hours = _hours_to_money(design_hours_raw, DESIGN_SELL_RATE)

    setup_hours_raw = calc_setup_hours_v1(params)
    setup_fee, setup_cost, setup_hours = _hours_to_money(setup_hours_raw, SETUP_SELL_RATE)

    return (design_fee, design_cost, design_hours, setup_fee, setup_cost, setup_hours)


def calc_design_setup_for_quotation(quotation) -> Dict[str, Any]:
    """
    Must return dict:
      design_hours, design_cost, design_fee, design_profit_rate,
      setup_hours,  setup_cost,  setup_fee,  setup_profit_rate
    """
    mode = _norm_calc_mode(getattr(quotation, "calc_mode", None))

    param_dict = {
        # 既存（走行条件）
        "distance_m": getattr(quotation, "distance_m", None),
        "intersection_count": getattr(quotation, "intersection_count", None),
        "station_count": getattr(quotation, "station_count", None),
        "vehicle_count": getattr(quotation, "vehicle_count", None),
        "equipment_count": getattr(quotation, "equipment_count", None),
        "circuit_difficulty": getattr(quotation, "circuit_difficulty", None),

        # 正式版（旧 new_v1）入力
        "avg_entry_dirs": getattr(quotation, "avg_entry_dirs", None),
        "station_auto": getattr(quotation, "station_auto", None),
        "station_manual": getattr(quotation, "station_manual", None),
        "station_relay": getattr(quotation, "station_relay", None),
        "station_charge": getattr(quotation, "station_charge", None),
        "wait_position_count": getattr(quotation, "wait_position_count", None),
        "has_swap_operation": getattr(quotation, "has_swap_operation", None),
        "has_plc_handshake": getattr(quotation, "has_plc_handshake", None),
        "has_ev_integration": getattr(quotation, "has_ev_integration", None),
        "difficulty_design": getattr(quotation, "difficulty_design", None),
        "difficulty_setup": getattr(quotation, "difficulty_setup", None),
    }

    design_fee, design_cost, design_hours, setup_fee, setup_cost, setup_hours = calc_design_and_setup_amounts(
        param_dict, calc_mode=mode
    )

    # 利益率（0除算ガード）
    def _profit_rate(fee, cost):
        try:
            fee = float(fee or 0)
            cost = float(cost or 0)
            if fee <= 0:
                return 0
            return (fee - cost) / fee * 100
        except Exception:
            return 0

    return {
        "design_hours": float(design_hours or 0),
        "design_cost": float(design_cost or 0),
        "design_fee": float(design_fee or 0),
        "design_profit_rate": float(_profit_rate(design_fee, design_cost)),
        "setup_hours": float(setup_hours or 0),
        "setup_cost": float(setup_cost or 0),
        "setup_fee": float(setup_fee or 0),
        "setup_profit_rate": float(_profit_rate(setup_fee, setup_cost)),
        "calc_mode": mode,
    }
