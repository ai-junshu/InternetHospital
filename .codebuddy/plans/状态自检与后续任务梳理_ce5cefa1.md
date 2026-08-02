---
name: 状态自检与后续任务梳理
overview: 基于文档要求与 08-02 工程真实代码，用第一性原理+对抗式审查完成自检，纠正文档与工程的事实偏差，重新产出状态报告，并梳理分级的后续任务清单。
todos:
  - id: verify-ground-truth
    content: 用 [subagent:code-explorer] 实地核查 RLS 测试/小程序S1S2/seed执行/rx mock/pay_order 证据
    status: completed
  - id: write-selfcheck-report
    content: 撰写主报告：第一性原理自检+对抗式审查+文档工程对账
    status: completed
    dependencies:
      - verify-ground-truth
  - id: revise-progress-docs
    content: 修订整体进度与下一步计划.md 与工程进度.md 纠正事实偏差
    status: completed
    dependencies:
      - write-selfcheck-report
  - id: list-next-tasks
    content: 在报告中输出 P0~P3 分级后续任务清单含对抗式暴露缺口
    status: completed
    dependencies:
      - write-selfcheck-report
---

## 用户需求

根据 PRD V2.0、技术架构方案等文档要求，结合 08-02 工程真实代码现状，先以"第一性原理 + 对抗式审查"完成自检，纠正既有文档与工程事实的偏差，再重新梳理一份项目状态报告，并梳理分级的后续任务清单。

## 产品概述

本任务为分析报告产出（非功能编码）。交付物为一份对齐真实代码状态的《状态自检与后续任务报告》，包含：第一性原理自检、对抗式审查、文档与工程事实对账、重新梳理的状态报告、后续任务分级清单。

## 核心内容

- 第一性原理自检：从"合规资质 + 可运行系统 + 风险可控"上线本质倒推必要能力，对照现状找缺口。
- 对抗式审查：对每一项"已完成"声明尝试证伪，列出未实证项与硬伤（DEV 建档后门、RLS 生效未验证、支付未生产化等）。
- 文档 vs 工程事实对账：纠正 P0-P3 自检报告(07-26)对双因子/审计链/落库加密/微信支付/医生身份的严重低估。
- 重新梳理状态报告：按 P0~P3 模块 + 合规资质硬门槛呈现真实完成度。
- 后续任务分级（P0 合规硬门槛 / P1 工程收口 / P2 真实化 / P3 产品补全）。

## 技术栈与产出形式

- 产出为 Markdown 分析报告，不生成 .docx（遵循"文档默认只输出 .md"约定）。
- 新建主报告 `互联网医疗中心平台_状态自检与后续任务_2026-08-02.md`。
- 同步修订既有文档（保持单一事实源）：`互联网医疗中心平台整体进度与下一步计划.md`、`互联网医疗中心平台工程进度.md`；`.xlsx` 项目状态报告仅在用户确认后更新。

## 实现方式

### 总体策略

先执行"实地验证"（只读探查真实代码与运行态证据），再撰写报告。报告严格区分"已代码级验证""已运行时验证""仅文档/未实证"三档，避免再次高估或低估。

### 关键技术决策

1. **对账必须以代码为事实源**：既有 P0-P3 自检报告(07-26)把双因子/审计链/落库加密列为"未做"，但 `security.py`/`audit.py`/`encrypted_field.py` 与迁移 0007/0008/0009 均已落地。报告须纠正此偏差，并标注证据文件行号。
2. **对抗式硬伤单列**：`login_wx` 开发态自动建 `DEV-DOC`/`DEV-PHA` 档案属合规红线后门；RLS 已注入但无多租户集成测试证明"越权拦截生效"（注入≠生效）；`pay_order` 仅 dev 沙箱模拟；`IhDoctor.dept` 未外键化。这些须作为高优先级风险条目。
3. **分级后续任务对齐第一性原理**：合规资质(P0 阻塞) → 工程收口(P1：种子实证、RLS 集成测试、DEV 后门关闭、支付生产化) → 真实化(P2：合理用药真引擎、CH 验证) → 产品补全(P3：小程序闭环、调理师/医院/监管前端)。

### 实现要点（执行阶段实地验证清单）

- 查明 `app/db/seed.py` 是否真执行：核查 PG `plat_account` 是否存在 seed 演示账号/双因子开启记录；如未执行，列为 P1 风险。
- 统计 `app/services/rx_engine/mock.py` 的 `_INTERACTIONS` 规则条数，评估 mock 深度。
- 检查 `mp-taro/src` 是否真正调用 S1 双身份登录（`services/ih.ts` 登录态持久化）与 S2 药师审核入口（`PATCH /prescriptions/{id}/audit` 封装与页面）。
- 确认 RLS 是否存在多租户集成测试（搜索 `tests/` 中带多 store 断言的用例）。

## 目录结构

```
互联网医疗中心平台_状态自检与后续任务_2026-08-02.md   # [NEW] 主报告：自检+对账+状态+后续任务
互联网医疗中心平台整体进度与下一步计划.md              # [MODIFY] 纠正双因子/审计链/加密/支付/医生身份偏差，附本次对账结论
互联网医疗中心平台工程进度.md                          # [MODIFY] 同步真实完成度（含 08-02 P3 四模块+ErrorCode修复+前端tsc0错）
```

## 关键代码结构（引用既有，不改）

- `code/backend/app/core/security.py`：TOTP(RFC6238)、PBKDF2-HMAC-SHA256、jwt。
- `code/backend/app/core/audit.py`：SHA-256 哈希链 + `verify_audit_chain`。
- `code/backend/app/core/deps.py`：`store_scope` / `customer_ids_for_store`（RLS 注入点）。
- `code/backend/app/api/v1/ih/users.py`：`login_wx` + `_resolve_subject`（含 DEV 建档后门，需标注）。
- `code/backend/app/services/rx_engine/`：base/mock/http/init（工厂 + HttpRxEngine 预留点）。
- `code/backend/app/db/seed.py`：幂等种子（执行与否需实证）。

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 执行报告前的实地验证——跨多文件核查 RLS 集成测试是否存在、mp-taro 是否接入 S1/S2、seed 执行痕迹、rx_engine mock 规则深度、pay_order 占位实现，产出可引用的代码证据清单。
- Expected outcome: 提供确凿的代码/测试层面证据，用于报告"已实证/未实证"分级与对抗式硬伤条目，避免报告再次偏离工程真实状态。