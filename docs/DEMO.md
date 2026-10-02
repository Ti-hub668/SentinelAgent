# SentinelAgent v1.0-demo 演示指南

本指南演示已有扫描数据到 Discovery、Finding、调查、响应治理与审计的完整链路。v1.0-demo 面向本地演示；生产级认证、RBAC、部署与监控仍在 Roadmap。

## 1. 准备与启动

- 安装项目所需的 Python、Node.js、MySQL、Nmap 与 Nuclei；创建 backend/.venv 并按 backend/requirements.txt 安装依赖。
- 在 frontend 中运行 npm install。配置使用已有本地环境文件，不将密码或 Token 写入文档、截图或 Git。
- 启动 MySQL（默认端口 3306）。AI 调查还需要配置的 Ollama 服务（默认端口 11434）与模型；只浏览库存无需模型调用。
- 已有数据库需要升级时，先备份，再手动执行迁移；启动脚本不会自动修改数据库结构。

~~~powershell
cd D:\SentinelAgent\backend
.\.venv\Scripts\python.exe scripts\migrate_schema.py
cd ..
.\start-dev.ps1
~~~

start-dev.ps1 检查虚拟环境、前端依赖及相关端口；已占用的应用端口不会重复启动或结束原进程。服务在后台运行，前端准备后打开浏览器。

- UI: http://127.0.0.1:5173
- API: http://127.0.0.1:18080
- OpenAPI: http://127.0.0.1:18080/docs

## 2. 库存与 Finding 演示（只读）

1. 在 Settings 切换简体中文 / English，刷新确认语言保留。
2. 打开 Dashboard 查看历史统计；打开 Assets、Scans 查看已有资产与任务。
3. 打开 Discovery 查看服务清单。搜索主机、端口、服务、产品、版本或 Web 目标；切换“仅 Web 服务”；刷新只读取历史记录。
4. Web Target 链接在新窗口打开；统计基于全部库存，筛选结果数量单独显示。没有记录时显示明确的首次扫描提示。
5. 在 Findings 选择一条已有 Finding，查看完整标题、风险、端口、证据与修复建议。

Discovery 实际路径：GET /api/scans/discovery，返回数组：

~~~json
[
  {
    "port_id": 1,
    "scan_task_id": 1,
    "asset_id": 1,
    "host": "127.0.0.1",
    "protocol": "tcp",
    "port": 8000,
    "service": "http",
    "product": "uvicorn",
    "version": "",
    "web_target": "http://127.0.0.1:8000",
    "scan_status": "completed",
    "discovered_at": "2026-01-01T12:00:00"
  }
]
~~~

这是结构示例，不是预置数据。库存按观察时间降序，以扫描 ID、端口 ID 打破时间相同的排序；同一资产、主机、协议、端口只保留最近记录。历史库存不会自动删除关闭的端口，不等于实时资产状态。任务失败前已持久化的端口也会显示，扫描状态仍标记失败。

## 3. 调查、响应与审计

优先打开已有 Investigation Run，展示 Context、Research / RAG、Evidence、Risk、Grounding、Verdict 与 Policy 结果。Response 与 Audit 展示审批、执行收据、持久化 Claim、Replay 及 Reconciliation 事件。

需要现场产生新调查时，先确认本地模型与威胁情报配置，并只选择已授权的 Finding。审批、执行及 Reconciliation 按钮会改变状态，不是浏览操作。保持默认 dry-run；真实 GitHub 操作必须同时显式启用外部执行和已有 GitHub 配置，并经过原有策略、审批与持久化 Claim 检查。不要为了演示绕过治理链路或展示 Token。

如果需要新增扫描，只对自己控制且获授权的本地测试服务进行，事先确认 Nmap / Nuclei 已安装。不要扫描未知互联网目标。已有历史数据足以展示本指南的只读部分。

## 4. 验证命令

~~~powershell
cd D:\SentinelAgent\backend
.\.venv\Scripts\python.exe -m compileall app
.\.venv\Scripts\python.exe -m app.evaluation.discovery_inventory_evaluator
cd ..\frontend
npm run build
cd ..
git diff --check
~~~

Discovery evaluator 使用独立 SQLite 数据库，并断言读取不调用扫描器、不改变数据库与 Context。其他治理 evaluator 可按项目说明单独运行。

## 5. 常见问题与范围

- API 离线：检查 18080、数据库配置及后端日志；端口被其他服务占用时脚本会跳过，不会杀死原进程。
- Discovery 无数据：确认已有扫描保存了 ports；刷新不会自动扫描。
- 新 API 返回 404：确认正在运行当前代码的后端；无 reload 的旧服务需要手动重启。
- AI 调查失败：检查 Ollama、模型及外部服务配置；库存和历史审计仍可独立浏览。
- 前端表格列多时在表格内部横向滚动，页面主体保持在视口内。
- 本地启动脚本适合开发演示，不是生产进程管理器。生产认证 / RBAC、CI/CD、数据库版本迁移、监控、更多集成以及大规模库存分页仍是后续增强。
