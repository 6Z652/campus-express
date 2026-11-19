# 校园快递驿站智能取件助手

《高级软件工程》课程项目 · 4 人小组 · 最小可运行可验证代码骨架。

学生端提供取件码查询、包裹聚合、排队预测与错峰建议、代取授权；工作人员端提供扫码入库、货架自动分配、出库核验与异常件登记。前后端均可本地一键启动，核心功能可运行、可演示、可测试。

## 技术栈

| 层 | 选型 |
| --- | --- |
| 后端 | Python 3 + FastAPI |
| 数据库 | 标准库 `sqlite3`，零外部服务，启动时自动建表 + seed |
| 前端 | 原生 ES6 + Fetch + HTML/CSS，免构建（不需要 npm / Vite） |
| 测试 | pytest + FastAPI `TestClient`（不启动常驻后台服务） |
| 开发环境 | GitHub Codespaces（`.devcontainer/`） |
| CI | GitHub Actions（`.github/workflows/ci.yml`） |
| AI 辅助 | GitHub Copilot（见 `docs/AI_CONTRIBUTION.md`） |

## 一键启动

在项目根目录执行：

```bash
# 1) 首次安装依赖
python -m pip install --no-cache-dir -r requirements.txt
#    如需国内镜像： python -m pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2) 终端 A：启动后端（自动建表并写入演示包裹数据）
python -m uvicorn app.main:app --port 8000

# 3) 终端 B：启动前端静态服务器
python -m http.server 8080 --directory frontend
```

浏览器打开 `http://127.0.0.1:8080`，页面顶部「后端地址」默认是 `http://127.0.0.1:8000`，点「检测连接」确认连通（后端已开启 CORS）。也可直接访问 `http://127.0.0.1:8000/docs` 查看 Swagger 交互式 API 文档。

演示取件码：`A-1-01-001`（学生「张三」，关联 3 个包裹）、`A-1-02-002`、`A-1-03-003`、`A-1-04-004`、`A-1-05-005`。

## 本机环境说明（如实记录）

- 本机解释器为 Python 3.13.14，初始环境缺少 `fastapi / uvicorn / httpx / pytest`。
- 首次用清华源安装时报 `ERROR: Could not find a version that satisfies the requirement fastapi (from versions: none)`；排查发现是 pip 缓存了一份空的索引响应，网络本身是通的（4 个源 HTTP 200）。
- 加 `--no-cache-dir` 后成功装齐依赖：`fastapi 0.162.4 / starlette 1.10.0 / uvicorn 0.54.0 / httpx 0.28.1 / pytest 9.2.0 / pydantic 2.14.3`。
- 因此**未**降级到标准库 `http.server` 方案，后端按原计划使用 FastAPI；上述安装命令统一带 `--no-cache-dir` 以规避该问题。

## API 列表

| 用例 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 基础 | GET | `/` | 服务信息 |
| 基础 | GET | `/api/health` | 健康检查 |
| UC-01 | GET / POST | `/api/packages/lookup?code=...` | 取件码解析 → 货架号 → 聚合返回同一学生的多个包裹 |
| UC-02 | GET | `/api/queue/forecast` | 排队预测（等待分钟数、拥挤等级、推荐错峰时段） |
| UC-03 | POST | `/api/packages/checkin` | 扫码入库、自动分配货架位、生成取件码、幂等 |
| UC-04 | POST | `/api/packages/checkout` | 出库核验（本人 / 代取 / 异常件登记） |
| UC-04 | POST | `/api/packages/authorize` | 生成代取授权码 |
| UC-04 | GET | `/api/packages/authorize/{code}` | 查询某取件码的授权状态（含过期判定） |
| UC-04 | GET | `/api/packages/exceptions` | 已登记异常件清单 |

取件码格式：`区(A-F)-层(1-5)-格(2位)-序号(3~6位)`，例如 `A-3-02-007`。

排队预测算法（`app/forecast.py`，纯函数可测）：

```
avg  = 当前时段历史均值；无该时段 -> 全局均值；完全无历史 -> 1.5 分钟
wait = ceil(pending_count * avg / servers)          # servers 默认 2
level: wait<=2 空闲 / <=5 正常 / <=10 繁忙 / >10 高峰
推荐错峰时段 = 历史中平均服务时长最低的非当前时段；无历史则给 10:00 或 15:00
```

## 目录结构

```
campus_express/
├── app/                        后端
│   ├── main.py                 FastAPI 入口、 lifespan 建表、CORS
│   ├── db.py                   sqlite3 建表 + 演示数据 seed
│   ├── codes.py                取件码生成与解析、货架位分配
│   ├── forecast.py             排队预测算法（纯函数）
│   ├── schemas.py              请求体 Pydantic 模型
│   ├── helpers.py              Row -> dict 序列化
│   └── routers/                按用例纵向切分的 4 个路由分组
│       ├── uc01_lookup.py
│       ├── uc02_forecast.py
│       ├── uc03_checkin.py
│       └── uc04_checkout.py
├── frontend/                   免构建前端
│   ├── index.html              学生端 / 工作人员端 Tab 切换
│   ├── app.js                  Fetch 调用全部 API
│   └── style.css
├── tests/
│   ├── conftest.py             DB 隔离到临时目录、每用例重建
│   ├── test_api.py             4 个 UC 正常流 + 异常分支
│   └── test_forecast.py        预测算法边界（0 人 / 高峰 / 无历史）
├── scripts/
│   ├── smoke.py                TestClient 依次调用全部 API 并打印真实响应
│   └── collect_metrics.py      真实采集指标 -> docs/REAL_METRICS.json
├── docs/
│   ├── usecases/UC-0X.md       4 份用例文档（基本流 + 异常流）
│   ├── AI_CONTRIBUTION.md      AI 贡献台账模板（需组员按实际填写）
│   ├── PROMPT_LOG.md           提示词日志模板（需组员按实际填写）
│   ├── screenshots/README.md   截图说明（截图由组员运行后放入）
│   ├── smoke_test_output.txt   pytest -q 真实完整输出
│   ├── api_smoke_output.txt    smoke.py 真实完整输出
│   └── REAL_METRICS.json       真实工程指标（测试数 / 耗时 / 代码行数 / API 响应）
├── data/                       express.db 运行时生成（已 gitignore）
├── .devcontainer/devcontainer.json
├── .github/workflows/ci.yml
├── requirements.txt
└── .gitignore
```

## 4 人纵向分工建议（目录归属）

按用例纵向切分，每人独立负责一个 UC 的「用例文档 → 后端路由 → 前端模块 → 测试」，减少交叉冲突：

| 成员 | 负责用例 | 目录归属 |
| --- | --- | --- |
| 赵佳悦（组长） | UC-01 取件码解析与包裹聚合查询 | `app/routers/uc01_lookup.py`、`app/codes.py`、`docs/usecases/UC-01.md`、`tests/test_api.py` 中 UC-01 用例、`frontend/` 学生端「取件码查询」模块 |
| 成员 B | UC-02 排队预测与错峰提醒 | `app/forecast.py`、`app/routers/uc02_forecast.py`、`tests/test_forecast.py`、`docs/usecases/UC-02.md`、`frontend/` 学生端「排队预测 / 错峰建议」模块 |
| 李艳慧 | UC-03 入库与货架分配 | `app/routers/uc03_checkin.py`、`app/db.py` 中 `packages` 表与 seed、`docs/usecases/UC-03.md`、`frontend/` 工作人员端「入库 / 货架分配」模块 |
| 成员 D | UC-04 出库核验与代取授权 | `app/routers/uc04_checkout.py`、`app/db.py` 中 `authorizations` / `exceptions` 表、`docs/usecases/UC-04.md`、`frontend/` 工作人员端「出库核验」模块 |
| 组长（公共） | 集成与工程化 | `app/main.py`、`app/schemas.py`、`tests/conftest.py`、`scripts/`、`.devcontainer/`、`.github/`、`requirements.txt`、`README.md` |

## 测试与真实结果

```bash
# 单元测试
python -m pytest -q

# API 冒烟（TestClient，不启动常驻服务）
python scripts/smoke.py

# 重新采集真实指标（需先保存 pytest -q 输出到 docs/smoke_test_output.txt）
python scripts/collect_metrics.py
```

> `docs/smoke_test_output.txt`、`docs/api_smoke_output.txt`、`docs/REAL_METRICS.json` 是本机实际运行产生的提交材料，数字与响应均来自真实执行，请勿手工修改；报告请直接引用这三个文件。

## 数据与隐私

`data/express.db` 由启动时自动建表并写入少量**虚构演示数据**（不提交、已加入 `.gitignore`）。`scripts/smoke.py` 每次运行会重建演示库以保证输出可复现；单元测试使用系统临时目录中的独立数据库，不污染演示库。
