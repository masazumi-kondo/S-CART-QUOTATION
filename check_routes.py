from app import create_app
app = create_app()
print("All registered routes:")
for rule in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    if 'reset' in rule.rule:
        print(f"{rule.rule:50} {rule.methods} {rule.endpoint}")

print("\n\nChecking /admin/v2-parameters routes:")
for rule in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    if 'v2-parameters' in rule.rule:
        print(f"{rule.rule:50} {rule.methods} {rule.endpoint}")
