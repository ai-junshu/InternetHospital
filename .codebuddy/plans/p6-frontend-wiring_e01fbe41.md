---
name: p6-frontend-wiring
overview: 将前端原 P6 标注的 4 处缺口（医生排班 / 调理师排班分配标签 / 药品目录 / 合规采集审核）从 localStorage/占位切换为真实后端 P6 接口调用。其中合规采集审核与药品目录平台管理页为新建模块，医生排班与调理师页为 localStorage→API 改写。
design:
  architecture:
    framework: react
  styleKeywords:
    - Ant Design Pro
    - 医疗科技
    - 卡片化
    - 企业级后台
    - 浅灰分层
    - 轻阴影圆角
  fontSystem:
    fontFamily: PingFang SC, Microsoft YaHei
    heading:
      size: 20px
      weight: 600
    subheading:
      size: 16px
      weight: 500
    body:
      size: 14px
      weight: 400
  colorSystem:
    primary:
      - "#1677FF"
      - "#13C2C2"
      - "#0958D9"
    background:
      - "#F0F2F5"
      - "#FFFFFF"
    text:
      - "#000000D9"
      - "#8C8C8C"
    functional:
      - "#52C41A"
      - "#FF4D4F"
      - "#FAAD14"
      - "#1677FF"
todos:
  - id: wire-mp-taro-p6
    content: 改写小程序医生排班页接 /ih/schedules，并补药品目录 service 与开方选药接通
    status: completed
  - id: wire-therapist-store
    content: 后台门店页 localStorage 改调 /mt/therapists 排班与标签 API，补 mt service 与常量
    status: completed
  - id: build-compliance-module
    content: 新建合规采集审核 service、页面与路由菜单（提交/列表/通过/驳回）
    status: completed
  - id: build-drug-catalog-page
    content: 新建平台药品目录管理页（列表/增改/删）并注册路由菜单
    status: completed
  - id: verify-frontend-builds
    content: 两前端 tsc/build 通过并修复类型错误
    status: completed
    dependencies:
      - wire-mp-taro-p6
      - wire-therapist-store
      - build-compliance-module
      - build-drug-catalog-page
---

## 用户需求

P0 等保测评与执业许可（组织流程）完成后，将前端原先标注为 P6 缺口的 4 处业务域，从本地存储/占位实现切换为真实后端 P6 接口调用。

## 产品概述

双前端（小程序 mp-taro、后台 admin-web）接通已就绪的 4 个 P6 后端域：医生排班、调理师排班与能力标签分配、药品目录、合规采集审核。其中合规采集审核与药品目录平台管理为全新前端模块，医生排班与门店调理师页为本地存储改写。

## 核心功能

- 医生排班（小程序）：周视图排班从本地保存改为调用 /ih/schedules 拉取与保存，删除走 DELETE。
- 调理师排班与标签（后台门店页）：排班与能力标签由本地存储改为 /mt/therapists 排班与 /mt/therapists/{id}/tags 分配接口；标签目录可取自 /mt/therapist-tags。
- 药品目录：小程序开方选药接通只读 /ih/drugs 列表；后台新增平台药品目录管理页（增/改/删，platform 角色）。
- 合规采集审核（后台新模块）：工单提交、列表（状态筛选）、通过/驳回（驳回必填意见），审核仅 platform/xingyao 可见全部。

## 技术栈

- 前端一（小程序）：Taro (React) + TypeScript + 内置 request 封装（JWT 拦截）。
- 前端二（后台）：React + TypeScript + Ant Design Pro（@ant-design/pro-components）+ axios 封装（JWT 拦截）。
- 后端（已就绪，不改动）：FastAPI，路径前缀 /api/v1；统一响应 {code,message,data} 由前端拦截器解包。
- 约定：路径常量集中在各端 src/constants/api.ts；鉴权由 request 拦截器自动注入 Authorization: Bearer token。

## 实现方案

高层策略：以"最小改动接通后端"为原则，复用两前端既有 services/request/PageResult 范式，仅替换 localStorage 读写为 HTTP 调用。

关键决策与处理：

1. **医生排班模型对齐**：小程序 UI 为"星期×上午/下午/晚上"循环网格，后端为按具体 work_date 的记录。采用"保存时按所选星期生成未来 4 周具体日期记录；加载时按 weekday+am_pm 聚合渲染网格"的方案，保留周视图体验又符合后端模型（doctor 角色不传 doctor_id，由 JWT 解析）。
2. **调理师门店页**：排班→POST/PATCH /mt/therapists/{id}/schedules；标签→先 GET /mt/therapists/{id}/tags 比对，再 POST/DELETE 分配。"客户分配(customers)"不在 P6 后端范围，保留为本地存储字段，不向后端提交，避免越界。
3. **药品目录**：小程序只读 listDrugs 接通开方选药；后台平台管理页用 ProTable+ModalForm 复用 data-assets/ai-models 范式。列表后端走 Redis 缓存，前端无需关心。
4. **合规模块**：新建独立页（不改动既有"合规大脑" audit-chain 页），service 封装 submit/list/get/approve/reject。

性能与可靠性：列表均走分页（page/page_size），避免全量拉取；写操作后端已审计，前端仅做 loading 与 toast。角色门控：药品管理页与合规审核按钮按 platform/xingyao 显隐（可选，拦截器对 403 已提示）。

## 实现注意

- 仅在 constants/api.ts 登记新路径常量，复用现有 request 封装，不新增请求层。
- 不改动后端代码；不改动现有"合规大脑"页与 AuditLog/DataAsset 逻辑。
- 写操作失败保持原表单不关闭，成功后刷新列表（actionRef.reload()）。
- 药品管理页与合规审核属敏感操作，按钮按角色显隐，降低越权误操作。
- 验证：两前端分别 `tsc --noEmit` 与 `npm run build` 通过；如后端可运行则联调真实接口。

## 架构设计

统一请求流：前端页面 → services 封装 → request 拦截器（注入 JWT）→ 后端 /api/v1 P6 端点 → Postgres/Redis。

```mermaid
flowchart LR
  A[小程序/后台页面] --> B[services/*.ts 封装]
  B --> C[request 拦截器: 注入 Bearer]
  C --> D[后端 /api/v1/ih|mt|plat/* P6 端点]
  D --> E[(PostgreSQL + Redis 缓存)]
```

## 目录结构

```
code/mp-taro/src/
├── constants/api.ts                 # [MODIFY] 新增 drugs: '/ih/drugs'
├── services/ih.ts                  # [MODIFY] 新增 IhDrug 接口、listDrugs/getDrug；删除"后端暂无药品目录"注释
├── pages/doctor-schedule/index.tsx # [MODIFY] 本地存储改为 GET/POST/DELETE /ih/schedules，weekday↔date 聚合
└── pages/<开方选药页>              # [MODIFY] 选药下拉/搜索改调 listDrugs（具体页由子代理按 ih.ts 注释定位）

code/admin-web/src/
├── constants/api.ts                          # [MODIFY] 新增 ihDrugs/mtTherapistSchedules/mtTherapistTags/compliance 常量
├── services/mt.ts                            # [MODIFY] 新增排班/标签 service 函数与接口类型
├── services/plat.ts                          # [MODIFY] 新增 ComplianceItem 接口与 submit/list/get/approve/reject
├── routes/store/index.tsx                    # [MODIFY] persist 改调 /mt/therapists 排班+标签 API；标签目录多选
├── routes/plat/compliance-review/index.tsx   # [NEW] 合规采集审核页：提交表单+列表+通过/驳回
├── routes/ih/drug-catalog/index.tsx          # [NEW] 药品目录管理页：ProTable+ModalForm+删除（platform）
├── layouts/BasicLayout.tsx                   # [MODIFY] 菜单新增"药品目录""合规采集审核"
└── App.tsx                                   # [MODIFY] 路由注册两个新页面
```

## 关键代码结构

```ts
// mp-taro/src/constants/api.ts 新增
export const API = { /* 现有 */ drugs: '/ih/drugs' }

// admin-web/src/constants/api.ts 新增
export const API = {
  ihDrugs: '/ih/drugs',
  mtTherapistSchedules: '/mt/therapists',   // 实际路径拼接 /{id}/schedules
  mtTherapistTags: '/mt/therapist-tags',
  compliance: '/plat/compliance',
}

// admin-web/src/services/plat.ts 新增签名（不含实现体）
export interface ComplianceItem { id: number; category: string; subject_type: string; subject_id?: number; title: string; content_json?: Record<string, unknown>; submitter_id?: number; status: string; reviewer_id?: number; review_note?: string; reviewed_at?: string; created_at?: string }
export function submitCompliance(body: { category: string; subject_type: string; subject_id?: number; title: string; content_json?: Record<string, unknown> }): Promise<ComplianceItem>
export function listCompliance(params: { category?: string; status?: string; subject_type?: string; page?: number; page_size?: number }): Promise<PageResult<ComplianceItem>>
export function approveCompliance(itemId: number, review_note?: string): Promise<ComplianceItem>
export function rejectCompliance(itemId: number, review_note: string): Promise<ComplianceItem>
```

## 设计风格

后台采用 Ant Design Pro 企业级风格，医疗科技主题：以蓝色为主、医疗青绿为强调色，浅灰背景分层，卡片化布局，圆角 8px，轻阴影，表格与弹窗遵循 Pro 组件规范。小程序医生排班页沿用现有浅灰底(#F5F7FA)+白卡片风格，仅将"本地保存"提示改为"已同步云端"，交互保持开关网格。

## 页面规划

1. 门店管理·调理师调配（ renovated ）：保留 ProTable 列表 + ModalForm；弹窗内"可服务日/班次"仍用复选，新增"能力标签"改为从 /mt/therapist-tags 拉取的多选标签；客户分配保留本地字段并注明"仅本地"。
2. 药品目录管理（new）：PageContainer + ProTable（keyword/otc_type/category/status 筛选）+ 新建/编辑 ModalForm（名称/规格/厂商/OTC类型/分类/单位/价格(分)/状态）+ 删除气泡确认；platform 角色可见菜单。
3. 合规采集审核（new）：PageContainer + 顶部"提交工单"按钮(ModalForm: 类别/主体类型/主体ID/标题/内容JSON) + ProTable（status 筛选：pending/approved/rejected）+ 操作列"通过/驳回"，驳回弹窗必填意见；审核角色可见全部，其他角色仅见本人。
4. 小程序医生排班（renovated）：周×时段开关网格，保存改调后端；加载中显示骨架，保存成功 toast 改为"已同步"。
5. 小程序开方选药（renovated）：选药下拉/搜索改为调用 listDrugs 只读结果。

## 交互与响应式

后台后台侧栏固定、内容区自适应；弹窗宽度 520px；表格空态与加载态使用 Pro 默认。小程序医生排班为单列纵向布局，适配手机宽度。所有写操作带 loading 与成功/失败反馈，错误由拦截器统一 toast。