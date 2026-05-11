from app.routes import admin
print("admin module:", admin)
print("admin_bp:", admin.admin_bp)
print("View functions:", list(admin.admin_bp.view_functions.keys()))
print("Reset function exists:", hasattr(admin, 'reset_v2_parameter_section'))

# Find the reset function manually
import inspect
for name, obj in inspect.getmembers(admin):
    if name == 'reset_v2_parameter_section':
        print(f"Found {name}: {obj}")

