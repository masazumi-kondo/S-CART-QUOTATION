/**
 * v2_core_new.js
 * 新仕様：概算見積向けV2自動算出
 * 
 * 主な変更：
 * - T1-T6テンプレート廃止
 * - シンプルな入力項目へ整理
 * - すべての係数を V2_DEFAULT_SETTINGS に集約
 * - 計算ロジックを明確に分離
 */

// ============================================================
// V2設定値（すべての係数をここに集約）
// 後で管理画面化するときはこのオブジェクトを外部から注入可能にする
// ============================================================

const V2_DEFAULT_SETTINGS = {
  // 時間単価（万円/時間）
  costHourlyRate: 17760,      // ¥17,760/h
  sellHourlyRate: 29600,      // ¥29,600/h

  // 基本工数（時間）
  designBaseHours: 8,
  setupBaseHours: 8,

  // AGV台数による追加工数
  designVehicleHours: 2,      // AGV1台あたり設計追加時間
  setupVehicleHours: 4,       // AGV1台あたり現地追加時間

  // 推定走行パターン（スコアベース）
  designPatternHours: 3,      // パターンスコア1あたり設計時間
  setupPatternHours: 4,       // パターンスコア1あたり現地時間

  // レイアウト規模
  setupLayoutScaleHours: 1.5, // 走行エリア規模あたり現地時間

  // 充電器
  designChargerHours: 1.0,
  setupChargerHours: 2.0,

  // 磁気テープ停止
  designMagneticStopHours: 0.5,
  setupMagneticStopHours: 1.0,

  // ランドマーク
  designLandmarkHours: 1.0,
  setupLandmarkHours: 4.0,

  // 設備連携
  designElevatorHours: 4.0,
  setupElevatorHours: 5.0,
  designAutoDoorHours: 2.0,
  setupAutoDoorHours: 3.0,
  designPlcSignalHours: 1.2,
  setupPlcSignalHours: 1.5,

  // 上位システム
  designHostSystemYesHours: 8.0,
  setupHostSystemYesHours: 8.0,
  designHostSystemUnknownHours: 4.0,
  setupHostSystemUnknownHours: 4.0,

  // 搬送ルート複雑さ係数
  routeComplexityFactors: {
    simple: 1.0,
    standard: 1.5,
    complex: 2.3,
    unknown: 1.6
  },

  // すれ違い・合流係数
  mergeFactors: {
    low: 0.8,
    standard: 1.3,
    high: 2.0,
    unknown: 1.4
  },

  // AGV台数補正係数
  vehicleFactors: {
    one: 1.0,
    two: 1.4,
    three: 1.8,
    fourOrMore: 2.2
  },

  // ランドマーク係数
  landmarkFactors: {
    small: 1.0,
    medium: 1.8,
    large: 2.8,
    full: 4.0,
    unknown: 2.2
  },

  // PLC/設備連携規模の代表信号点数
  plcSignalValues: {
    none: 0,
    small: 3,
    medium: 10,
    large: 20,
    unknown: 6
  }
};

// ============================================================
// ユーティリティ関数
// ============================================================

/**
 * 値を0.5時間単位で切り上げる
 * 例：2.3 → 2.5、 2.5 → 2.5、 2.1 → 2.5
 */
function roundHalfHour(x) {
  if (x < 0) return 0;
  return Math.ceil(x * 2) / 2;
}

/**
 * IDからnumber値を安全に読み取る
 */
function getNumberValue(elementId, defaultVal = 0, min = null, max = null) {
  const el = document.getElementById(elementId);
  if (!el) return defaultVal;
  
  let val = parseFloat(el.value || defaultVal);
  if (isNaN(val)) val = defaultVal;
  if (min !== null && val < min) val = min;
  if (max !== null && val > max) val = max;
  return val;
}

/**
 * IDからselect値を安全に読み取る
 */
function getSelectValue(elementId, defaultVal = '') {
  const el = document.getElementById(elementId);
  if (!el) return defaultVal;
  return el.value || defaultVal;
}

// ============================================================
// パラメータ読み取り
// ============================================================

/**
 * V2ウィザードから入力値を読み取る
 * 新UIの簡潔な入力項目から値を読む
 */
function readParamsV2FromWizard() {
  return {
    vehicle_count: Math.max(1, getNumberValue('v2_vehicle_count', 1)),
    pickup_count: Math.max(1, getNumberValue('v2_pickup_count', 1)),
    dropoff_count: Math.max(1, getNumberValue('v2_dropoff_count', 1)),
    area_short_m: Math.max(1, getNumberValue('v2_area_short_m', 10)),
    area_long_m: Math.max(1, getNumberValue('v2_area_long_m', 20)),
    route_complexity: getSelectValue('v2_route_complexity', 'standard'),
    merge_level: getSelectValue('v2_merge_level', 'standard'),
    charger_count: Math.max(0, getNumberValue('v2_charger_count', 1)),
    magnetic_stop_count: Math.max(0, getNumberValue('v2_magnetic_stop_count', 0)),
    landmark_range: getSelectValue('v2_landmark_range', 'unknown'),
    elevator_count: Math.max(0, getNumberValue('v2_elevator_count', 0)),
    auto_door_count: Math.max(0, getNumberValue('v2_auto_door_count', 0)),
    plc_scale: getSelectValue('v2_plc_scale', 'none'),
    host_system: getSelectValue('v2_host_system', 'none')
  };
}

// ============================================================
// 複雑度・スコア計算
// ============================================================

/**
 * パラメータから複雑度メトリクスを計算する
 */
function deriveComplexityMetricsV2(params, settings = V2_DEFAULT_SETTINGS) {
  // 基本搬送パターン数
  const base_route_pattern_count = params.pickup_count * params.dropoff_count;

  // 搬送ルート複雑さ係数
  const route_complexity_factor = settings.routeComplexityFactors[params.route_complexity] || 1.5;

  // すれ違い・合流係数
  const merge_factor = settings.mergeFactors[params.merge_level] || 1.3;

  // AGV台数係数
  let vehicle_factor;
  if (params.vehicle_count <= 1) {
    vehicle_factor = settings.vehicleFactors.one;
  } else if (params.vehicle_count === 2) {
    vehicle_factor = settings.vehicleFactors.two;
  } else if (params.vehicle_count === 3) {
    vehicle_factor = settings.vehicleFactors.three;
  } else {
    vehicle_factor = settings.vehicleFactors.fourOrMore;
  }

  // 推定走行パターンスコア（複合係数）
  const estimated_pattern_score = Math.sqrt(
    base_route_pattern_count * route_complexity_factor * merge_factor
  ) * vehicle_factor;

  // 走行エリア規模スコア（短辺 × 長辺 の平方根 ÷ 10）
  const layout_scale_score = Math.sqrt(params.area_short_m * params.area_long_m) / 10;

  // ランドマーク係数
  const landmark_factor = settings.landmarkFactors[params.landmark_range] || 2.2;

  // PLC相当信号点数
  const plc_signal_count = settings.plcSignalValues[params.plc_scale] || 0;

  // 上位システム連携時間（設計）
  let host_system_design_hours = 0;
  if (params.host_system === 'yes') {
    host_system_design_hours = settings.designHostSystemYesHours;
  } else if (params.host_system === 'unknown') {
    host_system_design_hours = settings.designHostSystemUnknownHours;
  }

  // 上位システム連携時間（現地）
  let host_system_setup_hours = 0;
  if (params.host_system === 'yes') {
    host_system_setup_hours = settings.setupHostSystemYesHours;
  } else if (params.host_system === 'unknown') {
    host_system_setup_hours = settings.setupHostSystemUnknownHours;
  }

  // 統合スコア（連携の複雑さ）
  const integration_score =
    params.elevator_count * 3 +
    params.auto_door_count * 2 +
    plc_signal_count;

  return {
    base_route_pattern_count,
    route_complexity_factor,
    merge_factor,
    vehicle_factor,
    estimated_pattern_score,
    layout_scale_score,
    landmark_factor,
    plc_signal_count,
    host_system_design_hours,
    host_system_setup_hours,
    integration_score
  };
}

// ============================================================
// 工数計算
// ============================================================

/**
 * 設計工数を計算する
 */
function calcDesignHoursV2(params, metrics, settings = V2_DEFAULT_SETTINGS) {
  let design_hours =
    settings.designBaseHours +
    params.vehicle_count * settings.designVehicleHours +
    metrics.estimated_pattern_score * settings.designPatternHours +
    params.charger_count * settings.designChargerHours +
    params.magnetic_stop_count * settings.designMagneticStopHours +
    metrics.landmark_factor * settings.designLandmarkHours +
    params.elevator_count * settings.designElevatorHours +
    params.auto_door_count * settings.designAutoDoorHours +
    metrics.plc_signal_count * settings.designPlcSignalHours +
    metrics.host_system_design_hours;

  // 最低工数は designBaseHours 以上
  design_hours = Math.max(design_hours, settings.designBaseHours);

  // 0.5h単位で切り上げ
  return roundHalfHour(design_hours);
}

/**
 * 現地セットアップ工数を計算する
 */
function calcSetupHoursV2(params, metrics, settings = V2_DEFAULT_SETTINGS) {
  let setup_hours =
    settings.setupBaseHours +
    params.vehicle_count * settings.setupVehicleHours +
    metrics.estimated_pattern_score * settings.setupPatternHours +
    metrics.layout_scale_score * settings.setupLayoutScaleHours +
    params.charger_count * settings.setupChargerHours +
    params.magnetic_stop_count * settings.setupMagneticStopHours +
    metrics.landmark_factor * settings.setupLandmarkHours +
    params.elevator_count * settings.setupElevatorHours +
    params.auto_door_count * settings.setupAutoDoorHours +
    metrics.plc_signal_count * settings.setupPlcSignalHours +
    metrics.host_system_setup_hours;

  // 最低工数は setupBaseHours 以上
  setup_hours = Math.max(setup_hours, settings.setupBaseHours);

  // 0.5h単位で切り上げ
  return roundHalfHour(setup_hours);
}

// ============================================================
// 金額計算
// ============================================================

/**
 * 工数から金額を計算する
 */
function convertAmountsV2(designHours, setupHours, settings = V2_DEFAULT_SETTINGS) {
  const designCostAmount = Math.round(designHours * settings.costHourlyRate);
  const designSellAmount = Math.round(designHours * settings.sellHourlyRate);
  const setupCostAmount = Math.round(setupHours * settings.costHourlyRate);
  const setupSellAmount = Math.round(setupHours * settings.sellHourlyRate);

  return {
    designHours,
    designCostAmount,
    designSellAmount,
    setupHours,
    setupCostAmount,
    setupSellAmount
  };
}

// ============================================================
// Note: runEstimateV2() is defined in v2_sync.js
// v2_sync.js handles DOM updates and orchestration
// ============================================================
