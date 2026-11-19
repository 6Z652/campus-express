# 提示词日志（模板）

> **重要：本文件是模板，不是已完成记录。请组员按本人实际与 AI 工具的交互逐条补录，禁止编造提示词或产出。**
>
> 用途：还原 AI 辅助开发过程，说明「为什么这样问、AI 给了什么、人如何取舍」，供课程检查与复盘。提交前请把示例占位行替换为真实记录。

## 填写说明

- 「提示词」尽量记录原始提问（可节选关键句），不要事后美化成理想版本。
- 「用途」对应需求拆解 / 代码生成 / 测试编写 / 调试排错 / 文档撰写 / 重构等。
- 「AI 产出摘要」写主要结论或代码片段所在文件，不必全文粘贴。
- 「采纳情况」填 `全量采纳 / 修改后采纳 / 部分采纳 / 弃用`，弃用请写原因。
- 「后续验证」写具体测试或操作，例如 `pytest -q`、`scripts/smoke.py`、页面点击某按钮。

## 提示词记录

| 编号 | 日期时间 | 成员 | AI 工具 | 用途 | 提示词（原文或关键节选） | AI 产出摘要 | 采纳情况 | 后续验证 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 |
| 2 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 |
| 3 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 | 【待填写】 |
| 4 | 2026-11-19 12:52 | 李艳慧 | WorkBuddy（DeepSeek-V4-Flash） | 测试编写 | “给 UC-03 扫码入库补两个异常/边界测试，重点验证幂等不覆盖首次信息和连续入库货架位递增” | 建议 2 个用例：重复提交保留首次记录、连续入库得 A-1-06-006 / A-1-07-007，并插入 `tests/test_api.py` 的 UC-03 段而非文件末尾 | 修改后采纳 | `python -m pytest tests/test_api.py -q` → 26 passed；`python -m pytest -q` → 39 passed |

| 5 | 2026-11-19 16:05 | 赵佳悦 | WorkBuddy（DeepSeek-V4-Flash） | 测试编写 | “给 UC-01 取件码查询补两个边界测试：首尾空格、小写区号；再补一个入库后立刻能查到的集成用例，验证生成和解析用的是同一套规则” | 给出 3 个用例：空格裁剪后正常返回、小写区号判 400、入库→查询闭环；第三条建议断言「解析货架号 == `packages` 表 `shelf_label`」而不是写死 `A-1-06-006` | 修改后采纳（把硬编码货架位改成与入库返回值比对，seed 增减时不会误挂） | `python -m pytest tests/test_api.py -q` → 29 passed；`python -m pytest -q` → 42 passed |
| 6 | 2026-11-19 22:09 | 朱蒙蒙 | WorkBuddy（DeepSeek-V4-Flash） | 需求梳理 / 差距审计 | “我是成员 B 朱蒙蒙，根据四人提交包，完成我这部分的内容。”随消息附《软件项目实践指导书 V6.0》与 `四人提交包_合订/` | 通读 `00_开工说明.md`、`UC-02.md`、`forecast.py`、`test_forecast.py` 后列出四处缺口：报告 5.2.2 称已补 E8/E9、实测只有 13 例；报告称 NULL 分支已修、代码仍会 `float(None)` 抛 `TypeError`；`PROMPT_LOG`/`AI_CONTRIBUTION` 仍是模板；`docs/screenshots/` 无图 | 修改后采纳（按缺口排序，先复现后修） | 手工复现 `average_service_minutes({11: None, 12: 3.0}, 11)` → `TypeError: float() argument must be ... not 'NoneType'`，确认缺陷真实存在 |
| 7 | 2026-11-19 22:12 | 朱蒙蒙 | WorkBuddy（DeepSeek-V4-Flash） | 代码修复 | “先修 `average_service_minutes` 的 NULL 分支：当前时段值为 NULL 时按「无该时段数据」回退到全局均值，不要抛异常；函数文档也要同步” | `if current_hour in history: return float(...)` 改为 `value = history.get(current_hour)` + `if value is not None`，NULL 与缺键走同一条回退分支；模块 docstring 第 1 条补「或值为 NULL（采集缺失）」 | 全量采纳（未改动其他函数，`forecast.py` 119 → 123 行） | `python -m pytest tests/test_forecast.py -q` → 15 passed |
| 8 | 2026-11-19 22:15 | 朱蒙蒙 | WorkBuddy（DeepSeek-V4-Flash） | 测试编写 | “按报告 6.4 已写的口径补 E8、E9 两例：E8 是历史表当前时段值为 NULL，E9 是只要有人排队就不该显示 0 分钟。断言要能真正卡住缺陷，不要写成恒真” | `test_history_hour_value_none_falls_back_to_global_mean`（`{10:1.0, 11:None, 12:3.0}` → avg 2.0、wait 6、推荐 10 点）与 `test_nonzero_queue_never_reports_zero_wait`（`predict_wait_minutes(1, 0.2) == 1`、`(1, 0.5, servers=3) == 1`） | 修改后采纳：E9 断言从 `>= 1` 收紧为精确 `== 1`，否则 `ceil` 被换成 `round` 或 `int()` 截断时抓不住 | `python -m pytest tests/test_forecast.py -q` → 15 passed；`python -m pytest -q` → 44 passed（main 42 例 + 本人 2 例） |
| 9 | 2026-11-19 22:22 | 朱蒙蒙 | WorkBuddy（DeepSeek-V4-Flash） | 文档同步 | “E8/E9 要同步进 `UC-02.md` 的异常流表和验收要点，文档不能和代码对不上” | `docs/usecases/UC-02.md` 基本流公式补 NULL 回退、异常流表新增 E8/E9 两行（指向真实用例名）、验收要点补「15 个用例」「NULL 先剔除」「有人排队 ≥ 1 分钟」 | 全量采纳 | 比对表格用例名与 `pytest --collect-only -q` 输出，E1～E9 九条与用例一一对应 |
| 10 | 2026-11-19 22:35 | 朱蒙蒙 | WorkBuddy（DeepSeek-V4-Flash） | 运行验证 / 截图 | “启动前后端，把「刷新预测」的真实结果截下来放进 `docs/screenshots/`，数字要和这次跑出来的一致，不要用示例值” | `uvicorn` 起后端 + `http.server` 起前端，页面加载即拉 `GET /api/queue/forecast`，截取当前时段／待取件数／平均单人时长／预计等待／拥挤等级／推荐错峰时段／提示／算法八行 | 全量采纳（整页截图保留「后端地址 127.0.0.1」与「连接正常」，可看出本机真实运行） | 截图中的 `pending_count=5`、`avg_service_minutes=1.55`、`predicted_wait_minutes=4` 与同一次 `curl /api/queue/forecast` 响应逐字一致 |

（行数按实际交互次数增减。）

## 建议补录的场景（供组员参考，非既成事实）

以下仅为**建议记录的方向**，请按真实发生情况填写，未发生就不要写：

1. 让 AI 把用例文档拆成 API 分组与目录结构。
2. 让 AI 生成某个 UC 的 FastAPI 路由与异常分支。
3. 让 AI 为预测算法补充边界条件（0 人排队、高峰、无历史数据）的测试。
4. 让 AI 排查测试失败原因（如 Pydantic 422、TestClient 用法、SQLite 隔离）。
5. 让 AI 生成前端 Tab 切换与 Fetch 调用代码。
6. 让 AI 审阅 `.devcontainer/devcontainer.json` 与 CI 配置。

## 声明

- 本日志只记录真实发生的交互；骨架代码由本次会话中的 AI 助手生成，这部分需组员在复核后按实际补录，不得虚构为本人操作。
- 日志中如引用测试结果，必须与 `docs/smoke_test_output.txt` / `docs/REAL_METRICS.json` 的真实数字一致。
