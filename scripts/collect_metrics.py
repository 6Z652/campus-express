"""采集真实工程指标，生成 docs/REAL_METRICS.json。

所有数字都来自本机实际运行，不包含任何手写常量：
- 测试总数/通过/失败  : 解析 docs/smoke_test_output.txt（pytest -q 真实输出）
- 用例按模块分类计数  : pytest --collect-only -q 的真实 nodeid
- 执行耗时            : subprocess + time.perf_counter() 真实计时
- 每个 API 的响应示例 : scripts/smoke.py 的 TestClient 真实调用
- 代码总行数          : 遍历 .py/.js/.html/.css 逐文件统计

用法（项目根目录）： python scripts/collect_metrics.py
前置：先运行 pytest -q 并把完整输出保存到 docs/smoke_test_output.txt
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
for p in (ROOT, SCRIPTS):
    if p not in sys.path:
        sys.path.insert(0, p)

DOCS = os.path.join(ROOT, "docs")
PYTEST_OUTPUT = os.path.join(DOCS, "smoke_test_output.txt")
METRICS_FILE = os.path.join(DOCS, "REAL_METRICS.json")
EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "data", ".venv", "node_modules"}
CODE_EXTS = (".py", ".js", ".html", ".css")

UC_MAP = {
    "uc01": "UC-01",
    "uc02": "UC-02",
    "uc03": "UC-03",
    "uc04": "UC-04",
}


def parse_pytest_output(text):
    def find(pattern):
        m = re.search(pattern, text)
        return int(m.group(1)) if m else 0

    return {
        "passed": find(r"(\d+) passed"),
        "failed": find(r"(\d+) failed"),
        "errors": find(r"(\d+) error"),
        "skipped": find(r"(\d+) skipped"),
        "warnings": find(r"(\d+) warning"),
        "reported_duration_seconds": (
            float(re.search(r"in ([\d.]+)s", text).group(1))
            if re.search(r"in ([\d.]+)s", text) else None
        ),
        "summary_line": text.strip().splitlines()[-1] if text.strip() else "",
    }


def collect_test_ids():
    """pytest --collect-only -q 的真实 nodeid，用于按模块分类计数。"""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    ids = [ln.strip() for ln in proc.stdout.splitlines() if "::" in ln]
    return ids, proc.returncode


def classify(nodeid):
    name = nodeid.split("::")[-1]
    if name.startswith("test_health"):
        return "健康检查"
    for key, label in UC_MAP.items():
        if f"test_{key}_" in name:
            return label
    return "预测算法边界(纯函数)"


def count_code_lines():
    per_file = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn.endswith(CODE_EXTS):
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, ROOT).replace("\\", "/")
                with open(path, "r", encoding="utf-8") as f:
                    per_file[rel] = sum(1 for _ in f)
    by_ext = Counter()
    for rel, n in per_file.items():
        by_ext[os.path.splitext(rel)[1]] += n
    return {
        "per_file": dict(sorted(per_file.items())),
        "by_extension": dict(sorted(by_ext.items())),
        "total_lines": sum(per_file.values()),
        "file_count": len(per_file),
    }


def main():
    t_start = time.perf_counter()

    if not os.path.exists(PYTEST_OUTPUT):
        raise SystemExit(
            "缺少 docs/smoke_test_output.txt，请先运行 pytest -q 并保存真实输出。"
        )
    with open(PYTEST_OUTPUT, "r", encoding="utf-8") as f:
        pytest_output = f.read()

    parsed = parse_pytest_output(pytest_output)

    # 真实计时：独立再跑一次 pytest -q
    t0 = time.perf_counter()
    timing_run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    t1 = time.perf_counter()
    pytest_wall = round(t1 - t0, 3)
    timing_parsed = parse_pytest_output(timing_run.stdout)

    # 真实用例清单与分类
    nodeids, collect_rc = collect_test_ids()
    by_file = Counter(n.split("::")[0] for n in nodeids)
    by_use_case = Counter(classify(n) for n in nodeids)

    # 真实 API 响应：调用 smoke.collect()（TestClient，不启动常驻服务）
    import smoke
    t2 = time.perf_counter()
    steps = smoke.collect()
    t3 = time.perf_counter()
    smoke_wall = round(t3 - t2, 3)

    status_counter = Counter(str(s["status_code"]) for s in steps)

    code_lines = count_code_lines()

    t_end = time.perf_counter()
    metrics = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "note": (
            "本文件所有数字均由 scripts/collect_metrics.py 在本机实际运行采集，"
            "未手工编造。测试数来自 pytest -q 真实输出；耗时由 time.perf_counter() "
            "真实测量；API 响应来自 TestClient 真实调用。"
        ),
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "fastapi_version": __import__("fastapi").__version__,
            "pytest_version": __import__("pytest").__version__,
        },
        "tests": {
            "total": len(nodeids),
            "passed": parsed["passed"],
            "failed": parsed["failed"],
            "errors": parsed["errors"],
            "skipped": parsed["skipped"],
            "warnings": parsed["warnings"],
            "pytest_summary_line": parsed["summary_line"],
            "by_module": dict(sorted(by_file.items())),
            "by_use_case": dict(sorted(by_use_case.items())),
            "collect_only_returncode": collect_rc,
            "consistency_check": {
                "collected_equals_passed_plus_failed": (
                    len(nodeids) == parsed["passed"] + parsed["failed"] + parsed["errors"]
                ),
                "timing_run_passed": timing_parsed["passed"],
                "timing_run_summary_line": timing_parsed["summary_line"],
            },
        },
        "timing_seconds": {
            "pytest_wall_time_measured": pytest_wall,
            "pytest_reported_duration": parsed["reported_duration_seconds"],
            "smoke_api_calls_wall_time_measured": smoke_wall,
            "metrics_collection_total_wall_time_measured": round(t_end - t_start, 3),
        },
        "api_calls": {
            "total": len(steps),
            "ok_2xx": sum(1 for s in steps if s["ok"]),
            "non_2xx": sum(1 for s in steps if not s["ok"]),
            "status_code_counts": dict(sorted(status_counter.items())),
            "responses": [
                {
                    "name": s["name"],
                    "api": s["api"],
                    "method": s["method"],
                    "path": s["path"],
                    "request_body": s["request_body"],
                    "status_code": s["status_code"],
                    "ok": s["ok"],
                    "response": s["response"],
                }
                for s in steps
            ],
        },
        "code_lines": code_lines,
    }

    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("已生成", METRICS_FILE)
    print(json.dumps({
        "tests": metrics["tests"]["total"],
        "passed": metrics["tests"]["passed"],
        "failed": metrics["tests"]["failed"],
        "pytest_wall_seconds": pytest_wall,
        "api_calls": len(steps),
        "code_total_lines": code_lines["total_lines"],
    }, ensure_ascii=False, indent=2))
    return metrics


if __name__ == "__main__":
    main()
