# mp-taro · 微信小程序前端（Taro 3 + React + TypeScript）

> 互联网医疗中心平台小程序：患者端 + 医生端。一套代码多端（微信小程序 / H5）。

## 技术栈
Taro 3 · React 18 · TypeScript ·（生产不独立 App，仅小程序，第3章）

## 本地启动

```powershell
npm install
npm run dev:weapp     # 微信小程序（用微信开发者工具打开 dist 目录）
# 或
npm run dev:h5        # H5 调试
```

- 接口基准来自 `config/dev.ts` 的 `API_BASE` → backend 本地 `http://localhost:8000/api/v1`
- 统一请求封装见 `src/services/request.ts`（自动注入 JWT、解析统一响应、错误码提示）

## 目录结构
```
src/
├── app.tsx / app.config.ts     # 入口 + 路由
├── pages/                      # login / index / prescription / order / doctor-consult
├── services/request.ts         # 统一请求封装
├── constants/api.ts            # API 路径常量
└── components/                 # 通用组件占位
```
