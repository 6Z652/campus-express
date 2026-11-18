# 截图目录说明

> **本目录当前没有截图。请组员按「一键启动」步骤真实运行项目后，把截图放入本目录，禁止使用伪造、拼接或网图。**

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
| `06_staff_exception.png` | 工作人员端登记异常件与异常件清单 | UC-04 |
| `07_pytest.png` | 本机 `pytest -q` 真实输出（应与 `docs/smoke_test_output.txt` 一致） | 测试 |
| `08_api_docs.png` | `http://127.0.0.1:8000/docs` Swagger 页面 | 工程化 |

## 要求

- 截图需包含浏览器地址栏或终端窗口，能看出是本机真实运行。
- 截图中的数字（测试通过数、等待分钟数等）必须与 `docs/REAL_METRICS.json`、`docs/smoke_test_output.txt` 一致；如因重新运行导致数字变化，请在报告中说明运行时点。
- 建议同时保留一份终端原文（复制到报告），不要只放图片。
- 图片文件体积过大时可适当压缩，但不得改变内容。

## 当前状态

- 【待组员填写】已放入截图数量：____ / 8
- 【待组员填写】截图人 / 日期：____________
- 【待组员填写】运行命令与浏览器版本：____________
