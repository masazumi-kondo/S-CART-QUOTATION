#!/usr/bin/env python
import sqlite3

conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()

cursor.execute("""
SELECT 
  cost_hourly_rate,
  sell_hourly_rate,
  design_base_hours,
  setup_base_hours,
  design_vehicle_hours,
  setup_vehicle_hours,
  plc_small_value,
  design_host_system_medium_hours
FROM v2_calculation_settings
WHERE id = 1
""")

row = cursor.fetchone()
if row:
    print("DB VALUES:")
    print(f"  cost_hourly_rate: {row[0]}")
    print(f"  sell_hourly_rate: {row[1]}")
    print(f"  design_base_hours: {row[2]}")
    print(f"  setup_base_hours: {row[3]}")
    print(f"  design_vehicle_hours: {row[4]}")
    print(f"  setup_vehicle_hours: {row[5]}")
    print(f"  plc_small_value: {row[6]}")
    print(f"  design_host_system_medium_hours: {row[7]}")
else:
    print("NO RECORD FOUND")

conn.close()
