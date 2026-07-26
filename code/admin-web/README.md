# admin-web · 管理后台（React + Vite + Ant Design Pro）

> 互联网医疗中心平台后台：门店管理 / 健康数据中台 / 平台管理三套，按路由前缀区分。

## 技术栈
React 18 · Vite 5 · Ant Design 5 · @ant-design/pro-components · TypeScript

## 本地启动

```powershell
npm install
npm run dev        # http://localhost:3000
```

- `/api` 经 Vite 代理转发至 backend `http://localhost:8000`（见 vite.config.ts）
- 统一请求封装见 `src/services/request.ts`（注入 JWT、解析统一响应、错误码拦截）

## 目录结构
```
src/
├── main.tsx / App.tsx          # 入口 + 路由
├── layouts/BasicLayout.tsx     # ProLayout 侧边栏 + 顶栏
├── routes/
│   ├── store/                  # 门店管理后台（mt）
│   ├── data/                   # 健康数据中台后台（mt）
│   └── plat/                   # 平台管理后台（plat）
├── services/request.ts         # 统一请求封装
├── constants/api.ts            # API 路径常量
└── components/                 # 通用组件占位
```
