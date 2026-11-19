# AI 辅助开发贡献台账（模板）

> **重要：本文件是模板，不是已完成记录。请 4 位组员按本人实际使用情况逐行填写，禁止编造。**
>
> 课程指导书要求体现 AI 辅助开发（GitHub Copilot 等）。本台账用于如实记录 AI 在需求拆解、代码生成、测试编写、文档撰写中的贡献，以及人工复核与修改情况。提交前请删除本提示块中的示例占位文字，保留真实填写的行。

## 填写说明

- 「AI 工具」填写实际使用的工具与版本，例如 `GitHub Copilot / Copilot Chat`、其他大模型助手等。
- 「生成内容」写清被 AI 生成或改写的具体文件与函数，不要笼统写「部分代码」。
- 「人工修改」必须写清人做了哪些改动（逻辑修正、边界补充、中文文案、格式调整等）。
- 「验证方式」写如何确认该产出正确（单元测试名、`pytest -q`、`scripts/smoke.py`、手工页面操作等）。
- 「采纳比例」由组员按自身判断如实估计，无依据可填「未评估」。

## 成员贡献台账

| 序号 | 日期 | 成员 | 负责用例 | AI 工具与版本 | 使用环节 | AI 生成/改写的内容（具体文件） | 人工修改与复核 | 验证方式 | 采纳比例 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 |
| 2 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 |
| 3 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 |
| 4 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 |
| 5 | 2026-11-19 | 李艳慧 | UC-03 扫码入库与货架自动分配 | WorkBuddy（DeepSeek-V4-Flash） | 测试编写 + 文档校准 | `tests/test_api.py` 新增 `test_uc03_idempotent_keeps_first_record`、`test_uc03_sequential_checkin_increments_shelf`；`docs/usecases/UC-03.md` 验收要点补 2 条 | 按 seed 只有 5 条包裹，核对期望货架位为 A-1-06-006 / A-1-07-007；测试插入 UC-03 段内而非文件末尾，避开成员 D 的 UC-04 段；复核后未改动断言逻辑 | `python -m pytest tests/test_api.py -q` → 26 passed；`python -m pytest -q` → 39 passed | 约 65% |

| 6 | 2026-11-19 | 赵佳悦 | UC-01 取件码解析与包裹聚合查询 | WorkBuddy（DeepSeek-V4-Flash） | 测试编写 + 用例文档校准 | `tests/test_api.py` 新增 `test_uc01_lookup_trims_surrounding_space`、`test_uc01_lowercase_area_is_rejected`、`test_uc01_newly_checked_in_package_is_queryable`；`docs/usecases/UC-01.md` 补 E5/E6 两条异常流与 2 条验收要点 | 核对 `parse_pickup_code` 是先 `strip()` 再走正则，故首尾空格属合法输入、小写区号应判 400；第三条用例改为复用 UC-03 入库接口返回的 `pickup_code`，不再硬编码货架位，并把断言从「等于固定字符串」改为「解析货架号 == 入库存储的 `shelf_label`」，避免与 seed 数据耦合 | `python -m pytest tests/test_api.py -q` → 29 passed；`python -m pytest -q` → 42 passed | 约 70% |
| 7 | 2026-11-19 | 朱蒙蒙 | UC-02 排队预测与错峰提醒 | WorkBuddy（DeepSeek-V4-Flash） | 差距审计 + 代码修复 + 测试编写 + 文档同步 + 运行验证 | `app/forecast.py`：`average_service_minutes()` 的 NULL 分支改造（`history.get()` + `if value is not None`）并同步模块 docstring；`tests/test_forecast.py`：新增 E8（当前时段值为 NULL）与 E9（有人排队不得显示 0 分钟）两例；`docs/usecases/UC-02.md`：基本流公式、异常流表 E8/E9、验收要点；`docs/PROMPT_LOG.md`：第 6～10 条记录 | ①修前先手工复现 `float(None)` 的 `TypeError`，确认缺陷真实存在再动手；②E9 的断言从 `>= 1` 收紧为精确 `== 1`，否则 `ceil` 失效时用例仍会通过；③E8 的历史字典特意保留 `10:1.0` 与 `12:3.0`，同时验证「剔除 NULL 后取全局均值」与「推荐时段跳过 NULL 时段」；④确认未触碰 `uc02_forecast.py`、`tests/test_api.py` 与其他成员负责的文件；⑤核对 `UC-02.md` 中 E1～E9 与 `pytest --collect-only -q` 的用例名逐条对应 | `python -m pytest tests/test_forecast.py -q` → 15 passed；`python -m pytest -q` → 44 passed（main 42 例 + 本人 2 例）；浏览器实跑 `/api/queue/forecast` 与 `docs/screenshots/02_student_forecast.png` 数字一致 | 约 75% |

（行数按实际需要增减，一人可多行。）

## 汇总与自查（由组长汇总填写）

| 项目 | 内容 |
| --- | --- |
| 使用 AI 工具的成员人数 | 【待填写】 / 4 |
| 涉及 AI 生成的文件数 | 【待填写】 |
| 经人工修改后保留的产出比例 | 【待填写】 |
| 全部 AI 产出是否都经过测试验证 | 【待填写：是 / 否，并说明】 |
| 是否存在完全未复核即提交的 AI 产出 | 【待填写：是 / 否】 |

## 声明

- 本台账仅记录**真实发生**的 AI 使用情况；未使用的环节留空或写「未使用」，不要虚构。
- 项目骨架代码由本次会话中的 AI 助手生成，但**这部分必须由组员复核后按实际填写**，不得直接照抄为「本人使用 Copilot」。
- 真实测试结果请以 `docs/smoke_test_output.txt`、`docs/api_smoke_output.txt`、`docs/REAL_METRICS.json` 为准，本台账不得填写与之矛盾的数字。
