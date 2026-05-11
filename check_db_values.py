#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from app import create_app, db
from app.models.v2_calculation_setting import V2CalculationSetting

app = create_app()
with app.app_context():
    s = V2CalculationSetting.query.first()
    if s:
        print(f"design_base_hours={s.design_base_hours}")
        print(f"setup_base_hours={s.setup_base_hours}")
        print(f"design_vehicle_hours={s.design_vehicle_hours}")
        print(f"cost_hourly_rate={s.cost_hourly_rate}")
    else:
        print("No record found")
