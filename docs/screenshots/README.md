# 截图目录说明

> **本目录的截图由组员在本机真实运行项目后截取（见文末「当前状态」），未使用伪造、拼接或网图。**

## 运行后再截图

```bash
# 终端 A
python -m uvicorn app.main:app --port 8000
# 终端 B
python -m http.server 8080 --directory frontend
# 浏览器打开 http://127.0.0.1:8080
```

## 建议截图清单（供报告引用）

| 建议文件名 | 内容 | 对应用例 |
| --- | --- | --- |
| `01_student_lookup.png` | 学生端取件码 `A-1-01-001` 查询结果（含货架号、3 个包裹） | UC-01 |
| `02_student_forecast.png` | 学生端排队预测与错峰建议 | UC-02 |
| `03_student_authorize.png` | 学生端生成代取授权码 | UC-04 |
| `04_staff_checkin.png` | 工作人员端入库，展示自动分配的货架位与取件码 | UC-03 |
| `05_staff_checkout.png` | 工作人员端出库核验通过 / 代取授权码校验 | UC-04 |
| `06_staff_exception.png` | 工作人员端登记异常件 | UC-04 |
| `06b_staff_exception_list.png` | 异常件清单（`查看异常件`） | UC-04 |
| `07_pytest.png` | 本机 `pytest` 真实输出（`collected 47 items` → `47 passed`） | 测试 |
| `08_api_docs.png` | `http://127.0.0.1:8000/docs` Swagger 页面 | 工程化 |

## 要求

- 截图需包含浏览器地址栏或终端窗口，能看出是本机真实运行。
- 截图中的数字（测试通过数、等待分钟数等）必须与 `docs/REAL_METRICS.json`、`docs/smoke_test_output.txt` 一致；如因重新运行导致数字变化，请在报告中说明运行时点。
- 建议同时保留一份终端原文（复制到报告），不要只放图片。
- 图片文件体积过大时可适当压缩，但不得改变内容。

## 当前状态

- 已放入截图数量：**9 张（清单内 8 张全部齐全，另有 `06b`）**
- 截图人 / 日期：张春亚 / 2026-11-19
- 运行命令与浏览器版本：`python -m uvicorn app.main:app --port 8000` + `python -m http.server 8080 --directory frontend`；Google Chrome 157.0.8103.52

### 本次截图的取数时点（与文档数字对齐）

- 截图前先 `reset_db()` 重建演示库，因此 `02_student_forecast.png` 中「待取件数 = 5」与 `docs/REAL_METRICS.json` 的 seed 数据一致；`04_staff_checkin.png` 的入库操作发生在预测截图之后，不影响该数字。
- `03_student_authorize.png` 生成的授权码 `003051` 与 `05_staff_checkout.png` 中「代取（授权码 003051）」是同一次会话的真实返回值。
- `docs/smoke_test_output.txt` 与 `REAL_METRICS.json` 已按本轮 `pytest -q` 重跑覆盖：**47 passed**（成员 D 的 UC-04 用例 5 个 + 其他成员 UC-01/UC-03 边界用例，基线 37）。

### 补拍的 07 / 08 是怎么来的

- `07_pytest.png`：在**真实 Windows 终端窗口**里执行
  `python -m pytest --no-header -p no:warnings`，窗口最大化后整屏截取（含标题栏与命令回显）。
  画面中可见 `collected 47 items`、`tests\test_api.py` 与 `tests\test_forecast.py` 两行进度、
  `47 passed in 4.75s`、`=== exit code: 0 ===`，末尾是本项目目录的提示符。
  加 `--no-header -p no:warnings` 只是为了让整轮结果在一屏内显示完（否则 `platform` / `rootdir`
  与 warnings summary 会把顶行挤出可视区），**用例数与结论未做任何改动**；完整原始输出见 `docs/smoke_test_output.txt`。
- `08_api_docs.png`：后端启动后打开 `http://127.0.0.1:8000/docs`，地址栏可见 `127.0.0.1:8000/docs`。
  为了把 UC-01~UC-04 四个分组的 8 个接口一次性拍全，浏览器缩放到 75% 后截取。

### 说明

- 两张图都是窗口级截屏（不是浏览器页面渲染导出），因此能看到系统标题栏、地址栏与终端提示符，
  可据此判断确为本机真实运行。
- `05_staff_checkout.png` / `06b_...` 与 `07` / `08` 是同一晚、同一份代码（`pytest` 47 passed）下采集的。
