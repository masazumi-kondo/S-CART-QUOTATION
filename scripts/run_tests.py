
import sys
import subprocess
from pathlib import Path
import argparse
import os
import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def run_test(script, env):
    proc = subprocess.run([
        sys.executable, str(PROJECT_ROOT / 'scripts' / script)
    ], cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=env)
    print(proc.stdout, end="")
    print(proc.stderr, end="")
    fail_log_paths = []
    for line in (proc.stdout + proc.stderr).splitlines():
        if line.startswith("[INFO] FAIL log path: "):
            fail_log_paths.append(line[len("[INFO] FAIL log path: "):].strip())
    return proc.returncode, fail_log_paths, proc.stdout, proc.stderr

def extract_key_failure(stdout, stderr):
    lines = (stdout + '\n' + stderr).splitlines()
    # Prefer first FAIL: line
    for line in lines:
        if line.startswith("FAIL:") and not any(x in line.lower() for x in ["password", "token", "salt"]):
            return line.strip()
    # Next, look for Traceback
    for i, line in enumerate(lines):
        if "Traceback" in line:
            # Try previous or next line
            if i > 0 and lines[i-1].strip() and not any(x in lines[i-1].lower() for x in ["password", "token", "salt"]):
                return lines[i-1].strip()
            if i+1 < len(lines) and lines[i+1].strip() and not any(x in lines[i+1].lower() for x in ["password", "token", "salt"]):
                return lines[i+1].strip()
    # Next, look for ERROR
    for line in lines:
        if "ERROR" in line and not any(x in line.lower() for x in ["password", "token", "salt"]):
            return line.strip()
    return ""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', type=str, default=None)
    parser.add_argument('--db', type=str, default=None)
        parser.add_argument("--write-summary-on-pass", action="store_true", help="Write summary even if all tests pass (CI mode)")
    args = parser.parse_args()

    env = dict(os.environ)
    base_url = args.base_url or env.get('BASE_URL', 'default')
    db_path = args.db or env.get('SCART_DB_PATH', 'auto')
    if args.base_url:
        env['BASE_URL'] = args.base_url
    if args.db:
        env['SCART_DB_PATH'] = args.db

    test_results = []
    fail_log_paths = []

    rc1, logs1, out1, err1 = run_test('test_permissions.py', env)
    key_failure1 = extract_key_failure(out1, err1)
    fail_log1 = logs1[0] if logs1 else ""
    test_results.append({
        "name": "test_permissions",
        "returncode": rc1,
        "fail_log_path": fail_log1,
        "stdout": out1,
        "stderr": err1,
        "key_failure": key_failure1
    })
    fail_log_paths.extend(logs1)

    rc2, logs2, out2, err2 = run_test('test_concurrent_approve.py', env)
    key_failure2 = extract_key_failure(out2, err2)
    fail_log2 = logs2[0] if logs2 else ""
    test_results.append({
        "name": "test_concurrent_approve",
        "returncode": rc2,
        "fail_log_path": fail_log2,
        "stdout": out2,
        "stderr": err2,
        "key_failure": key_failure2
    })
    fail_log_paths.extend(logs2)

    print("\n==== SUMMARY ====")
    print(f"test_permissions: {'PASS' if rc1 == 0 else 'FAIL'}")
    print(f"test_concurrent_approve: {'PASS' if rc2 == 0 else 'FAIL'}")
    if rc1 != 0 or rc2 != 0:
        print("FAIL LOGS:")
        if fail_log_paths:
            for path in fail_log_paths:
                print(f"  {path}")
        else:
            print("  (not found)")

    # Markdown summary generation (FAIL only)
        if rc1 != 0 or rc2 != 0 or args.write_summary_on_pass:
        summary_dir = PROJECT_ROOT / "artifacts" / "test_summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = summary_dir / f"test_summary_{ts}.md"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("# SCART Quotation Automated Test Summary\n\n")
            f.write(f"**Run Timestamp:** {ts}\n\n")
            f.write(f"**cwd:** {os.getcwd()}\n\n")
            f.write(f"**Python Executable:** {sys.executable}\n\n")
            f.write(f"**BASE_URL:** {base_url}\n\n")
            f.write(f"**SCART_DB_PATH:** {db_path}\n\n")
            f.write("\n## Test Results\n\n")
            f.write("| Test | Status | ExitCode | Fail Log Path | Key Failure |\n")
            f.write("|------|--------|----------|---------------|-------------|\n")
            for tr in test_results:
                status = "PASS" if tr["returncode"] == 0 else "FAIL"
                fail_log_disp = tr["fail_log_path"] if tr["fail_log_path"] else ""
                key_failure_disp = tr["key_failure"] if tr["key_failure"] else ""
                f.write(f"| {tr['name']} | {status} | {tr['returncode']} | {fail_log_disp} | {key_failure_disp} |\n")
            f.write("\n## FAIL LOGS\n\n")
            if fail_log_paths:
                for path in fail_log_paths:
                    f.write(f"- {path}\n")
            else:
                f.write("- (not found)\n")
        print(f"[INFO] Summary written: {summary_file.resolve()}")
    sys.exit(1 if rc1 != 0 or rc2 != 0 else 0)

if __name__ == "__main__":
    main()
