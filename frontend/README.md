# SentinelAgent Frontend · Day 29

独立 Vue 3 + Vite 工程，使用 Vue Router、Pinia、Element Plus 和 Axios。只在 `frontend/` 内维护，不修改后端。

## 本地运行

需要 Node.js 20.19+（20.x）或 22.12+。

```powershell
cd D:\SentinelAgent\frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173 。生产构建使用 `npm run build`，本地预览使用 `npm run preview`。

## 环境变量和接口

- `.env.development`：开发模式默认 `/api`，通过 Vite 代理到 `http://127.0.0.1:8000`，保留 `/api` 前缀。
- `.env.production`：生产模式默认同源 `/api`。
- 本地覆盖可复制 `.env.example` 为 `.env.local`，或使用 `.env.development.local`；修改后重启 Vite。
- `API_PROXY_TARGET` 只用于开发服务器；`VITE_` 变量会公开到浏览器，不得存放密钥。
- `src/api/request.js` 提供超时、返回体解包、FastAPI 错误提示和 Promise 拒绝；调用方仍需处理失败。可传 `{ silent: true }` 禁用全局提示，可传 `signal` 取消请求。
- `src/api/index.js` 已封装现有资产、扫描、安全发现列表 GET 接口，当前页面尚未调用。
- 生产部署需要将 `/api` 反向代理到后端，并将页面路由回退到 `index.html`；Vite 开发代理不会写入构建产物。

## 当前范围

9 个页面路由、可折叠侧栏、顶部时间、Dashboard 扫描入口、严重等级卡片、趋势/分布空态和最近任务表格。非 Dashboard 页面保留基础标题、说明和后续模块占位。

Dashboard 以 `—` 表示数据待接入，不代表风险为零。顶部状态不冒充后端健康状态。快速扫描仅携带目标地址跳转到 Scans，不发起真实扫描。AI 调查、响应审批、审计和系统设置均留待后续实现。

全局布局按要求保留 `min-width: 1180px`，面向桌面使用。
