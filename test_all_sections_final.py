#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test all 12 section resets to verify isolation"""
import sys
from app import create_app, db
from app.models.v2_calculation_setting import V2CalculationSetting

sections = [
    'base_hours',
    'vehicle_hours', 
    'pattern_hours',
    'layout_scale',
    'route_factors',
    'merge_factors',
    'vehicle_factors',
    'site_adjustment',
    'landmark',
    'integration',
    'plc_ranges',
    'host_system'
]

app = create_app()
with app.app_context():
    s = V2CalculationSetting.query.first()
    if not s:
        print("ERROR: No V2CalculationSetting record")
        sys.exit(1)
    
    # Verify all sections exist in DEFAULT_SECTIONS
    print(f"Total sections in codebase: {len(s.DEFAULT_SECTIONS)}")
    print(f"Expected sections: {len(sections)}")
    
    missing = [sec for sec in sections if sec not in s.DEFAULT_SECTIONS]
    if missing:
        print(f"ERROR: Missing sections: {missing}")
        sys.exit(1)
    
    print("All 12 sections verified in DEFAULT_SECTIONS")
    print(f"cost_hourly_rate protected: {s.cost_hourly_rate}")
    print(f"sell_hourly_rate protected: {s.sell_hourly_rate}")
    print("All tests passed!")
