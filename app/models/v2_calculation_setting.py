from datetime import datetime
from app import db


class V2CalculationSetting(db.Model):
    __tablename__ = "v2_calculation_settings"

    id = db.Column(db.Integer, primary_key=True)

    # 賃率
    cost_hourly_rate = db.Column(db.Float, nullable=False, default=17760)
    sell_hourly_rate = db.Column(db.Float, nullable=False, default=29600)

    # 基本工数
    design_base_hours = db.Column(db.Float, nullable=False, default=8)
    setup_base_hours = db.Column(db.Float, nullable=False, default=8)

    # AGV台数
    design_vehicle_hours = db.Column(db.Float, nullable=False, default=2)
    setup_vehicle_hours = db.Column(db.Float, nullable=False, default=4)

    # パターンスコア
    design_pattern_hours = db.Column(db.Float, nullable=False, default=3)
    setup_pattern_hours = db.Column(db.Float, nullable=False, default=4)

    # レイアウト規模
    setup_layout_scale_hours = db.Column(db.Float, nullable=False, default=1.5)

    # 搬送ルート複雑さ係数
    route_factor_simple = db.Column(db.Float, nullable=False, default=1.0)
    route_factor_standard = db.Column(db.Float, nullable=False, default=1.5)
    route_factor_complex = db.Column(db.Float, nullable=False, default=2.3)
    route_factor_unknown = db.Column(db.Float, nullable=False, default=1.6)

    # すれ違い・合流係数
    merge_factor_low = db.Column(db.Float, nullable=False, default=0.8)
    merge_factor_standard = db.Column(db.Float, nullable=False, default=1.3)
    merge_factor_high = db.Column(db.Float, nullable=False, default=2.0)
    merge_factor_unknown = db.Column(db.Float, nullable=False, default=1.4)

    # AGV台数補正
    vehicle_factor_one = db.Column(db.Float, nullable=False, default=1.0)
    vehicle_factor_two = db.Column(db.Float, nullable=False, default=1.4)
    vehicle_factor_three = db.Column(db.Float, nullable=False, default=1.8)
    vehicle_factor_four_or_more = db.Column(db.Float, nullable=False, default=2.2)

    # 現地設置・補正
    design_charger_hours = db.Column(db.Float, nullable=False, default=1.0)
    setup_charger_hours = db.Column(db.Float, nullable=False, default=2.0)
    design_magnetic_stop_hours = db.Column(db.Float, nullable=False, default=0.5)
    setup_magnetic_stop_hours = db.Column(db.Float, nullable=False, default=1.0)

    # ランドマーク係数
    landmark_factor_small = db.Column(db.Float, nullable=False, default=1.0)
    landmark_factor_medium = db.Column(db.Float, nullable=False, default=1.8)
    landmark_factor_large = db.Column(db.Float, nullable=False, default=2.8)
    landmark_factor_full = db.Column(db.Float, nullable=False, default=4.0)
    landmark_factor_unknown = db.Column(db.Float, nullable=False, default=2.2)

    # ランドマーク工数換算
    design_landmark_hours = db.Column(db.Float, nullable=False, default=1.0)
    setup_landmark_hours = db.Column(db.Float, nullable=False, default=4.0)

    # 設備連携
    design_elevator_hours = db.Column(db.Float, nullable=False, default=4.0)
    setup_elevator_hours = db.Column(db.Float, nullable=False, default=5.0)
    design_auto_door_hours = db.Column(db.Float, nullable=False, default=2.0)
    setup_auto_door_hours = db.Column(db.Float, nullable=False, default=3.0)
    design_plc_signal_hours = db.Column(db.Float, nullable=False, default=1.2)
    setup_plc_signal_hours = db.Column(db.Float, nullable=False, default=1.5)

    # PLCレンジ
    plc_none_value = db.Column(db.Integer, nullable=False, default=0)

    plc_small_min = db.Column(db.Integer, nullable=False, default=1)
    plc_small_max = db.Column(db.Integer, nullable=False, default=5)
    plc_small_value = db.Column(db.Integer, nullable=False, default=3)

    plc_medium_min = db.Column(db.Integer, nullable=False, default=6)
    plc_medium_max = db.Column(db.Integer, nullable=False, default=15)
    plc_medium_value = db.Column(db.Integer, nullable=False, default=10)

    plc_large_min = db.Column(db.Integer, nullable=False, default=16)
    plc_large_max = db.Column(db.Integer, nullable=False, default=30)
    plc_large_value = db.Column(db.Integer, nullable=False, default=20)

    plc_unknown_value = db.Column(db.Integer, nullable=False, default=6)

    # 上位システム連携：なし/小/中/大
    design_host_system_none_hours = db.Column(db.Float, nullable=False, default=0.0)
    setup_host_system_none_hours = db.Column(db.Float, nullable=False, default=0.0)

    design_host_system_small_hours = db.Column(db.Float, nullable=False, default=4.0)
    setup_host_system_small_hours = db.Column(db.Float, nullable=False, default=4.0)

    design_host_system_medium_hours = db.Column(db.Float, nullable=False, default=8.0)
    setup_host_system_medium_hours = db.Column(db.Float, nullable=False, default=8.0)

    design_host_system_large_hours = db.Column(db.Float, nullable=False, default=16.0)
    setup_host_system_large_hours = db.Column(db.Float, nullable=False, default=16.0)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_v2_json(self):
        return {
            "costHourlyRate": self.cost_hourly_rate,
            "sellHourlyRate": self.sell_hourly_rate,
            "designBaseHours": self.design_base_hours,
            "setupBaseHours": self.setup_base_hours,
            "designVehicleHours": self.design_vehicle_hours,
            "setupVehicleHours": self.setup_vehicle_hours,
            "designPatternHours": self.design_pattern_hours,
            "setupPatternHours": self.setup_pattern_hours,
            "setupLayoutScaleHours": self.setup_layout_scale_hours,
            "routeComplexityFactors": {
                "simple": self.route_factor_simple,
                "standard": self.route_factor_standard,
                "complex": self.route_factor_complex,
                "unknown": self.route_factor_unknown,
            },
            "mergeFactors": {
                "low": self.merge_factor_low,
                "standard": self.merge_factor_standard,
                "high": self.merge_factor_high,
                "unknown": self.merge_factor_unknown,
            },
            "vehicleFactors": {
                "one": self.vehicle_factor_one,
                "two": self.vehicle_factor_two,
                "three": self.vehicle_factor_three,
                "fourOrMore": self.vehicle_factor_four_or_more,
            },
            "designChargerHours": self.design_charger_hours,
            "setupChargerHours": self.setup_charger_hours,
            "designMagneticStopHours": self.design_magnetic_stop_hours,
            "setupMagneticStopHours": self.setup_magnetic_stop_hours,
            "landmarkFactors": {
                "small": self.landmark_factor_small,
                "medium": self.landmark_factor_medium,
                "large": self.landmark_factor_large,
                "full": self.landmark_factor_full,
                "unknown": self.landmark_factor_unknown,
            },
            "designLandmarkHours": self.design_landmark_hours,
            "setupLandmarkHours": self.setup_landmark_hours,
            "designElevatorHours": self.design_elevator_hours,
            "setupElevatorHours": self.setup_elevator_hours,
            "designAutoDoorHours": self.design_auto_door_hours,
            "setupAutoDoorHours": self.setup_auto_door_hours,
            "designPlcSignalHours": self.design_plc_signal_hours,
            "setupPlcSignalHours": self.setup_plc_signal_hours,
            "plcSignalValues": {
                "none": self.plc_none_value,
                "small": self.plc_small_value,
                "medium": self.plc_medium_value,
                "large": self.plc_large_value,
                "unknown": self.plc_unknown_value,
            },
            "hostSystemDesignHours": {
                "none": self.design_host_system_none_hours,
                "small": self.design_host_system_small_hours,
                "medium": self.design_host_system_medium_hours,
                "large": self.design_host_system_large_hours,
            },
            "hostSystemSetupHours": {
                "none": self.setup_host_system_none_hours,
                "small": self.setup_host_system_small_hours,
                "medium": self.setup_host_system_medium_hours,
                "large": self.setup_host_system_large_hours,
            },
        }
