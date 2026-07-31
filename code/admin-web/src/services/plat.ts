// 平台管理（plat）服务封装（第10.2/11.2章）：AI 模型目录 / 数据资产目录。
// 统一响应经 request.ts 拦截器解包为 data（PageResult / 实体）。
import http from './request'
import { API } from '@/constants/api'

export interface PageResult<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface AiModel {
  id: number
  name: string
  version: string
  algo_type?: string
  metrics_json?: Record<string, unknown>
  status: string
  online_at?: string
  offline_at?: string
  created_at?: string
  updated_at?: string
}

export interface DataAsset {
  id: number
  name: string
  owner?: string
  sensitivity_level?: string
  usage_scope?: string
  quality_score?: number
  update_freq?: string
  lineage_json?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export async function listAiModels(params: {
  page?: number
  page_size?: number
  name?: string
  status?: string
  algo_type?: string
}) {
  return http.get(API.aiModels, { params }) as Promise<PageResult<AiModel>>
}

export async function listDataAssets(params: {
  page?: number
  page_size?: number
  name?: string
  owner?: string
  sensitivity_level?: string
}) {
  return http.get(API.dataAssets, { params }) as Promise<PageResult<DataAsset>>
}

// ---------------- 模型上下线 / 删除 ----------------
export async function setModelOnline(modelId: number) {
  return http.post(`${API.aiModels}/${modelId}/online`) as Promise<AiModel>
}

export async function setModelOffline(modelId: number) {
  return http.post(`${API.aiModels}/${modelId}/offline`) as Promise<AiModel>
}

export async function deleteModel(modelId: number) {
  return http.delete(`${API.aiModels}/${modelId}`) as Promise<void>
}

export async function createDataAsset(body: Partial<DataAsset>) {
  return http.post(API.dataAssets, body) as Promise<DataAsset>
}

export async function updateDataAsset(assetId: number, body: Partial<DataAsset>) {
  return http.put(`${API.dataAssets}/${assetId}`, body) as Promise<DataAsset>
}

export async function deleteDataAsset(assetId: number) {
  return http.delete(`${API.dataAssets}/${assetId}`) as Promise<void>
}

// ---------------- 审计日志（3.6.1 合规大脑，复用 P4 哈希链） ----------------
export interface AuditLog {
  id: number
  actor_id?: number
  role?: string
  action?: string
  resource?: string
  before_json?: Record<string, unknown>
  after_json?: Record<string, unknown>
  ip?: string
  seq_no: number
  prev_hash?: string
  hash?: string
  created_at?: string
}

export async function listAuditLogs(params: {
  page?: number
  page_size?: number
  resource?: string
}) {
  return http.get(API.auditLogs, { params }) as Promise<PageResult<AuditLog>>
}

export async function verifyAuditChain() {
  return http.get(`${API.auditLogs}/verify`) as Promise<{
    ok: boolean
    broken_at_seq: number | null
  }>
}

// ---------------- P6: 合规采集审核（3.6.2 合规大脑·采集与审核） ----------------
export interface ComplianceItem {
  id: number
  category: string
  subject_type: string
  subject_id?: number
  title: string
  content_json?: Record<string, unknown>
  submitter_id?: number
  status: string
  reviewer_id?: number
  review_note?: string
  reviewed_at?: string
  created_at?: string
}

export async function submitCompliance(body: {
  category: string
  subject_type: string
  subject_id?: number
  title: string
  content_json?: Record<string, unknown>
}) {
  return http.post(`${API.compliance}/submit`, body) as Promise<ComplianceItem>
}

export async function listCompliance(params: {
  category?: string
  status?: string
  subject_type?: string
  page?: number
  page_size?: number
}) {
  return http.get(API.compliance, { params }) as Promise<PageResult<ComplianceItem>>
}

export async function getCompliance(itemId: number) {
  return http.get(`${API.compliance}/${itemId}`) as Promise<ComplianceItem>
}

export async function approveCompliance(itemId: number, review_note?: string) {
  return http.post(`${API.compliance}/${itemId}/approve`, { review_note }) as Promise<ComplianceItem>
}

export async function rejectCompliance(itemId: number, review_note: string) {
  return http.post(`${API.compliance}/${itemId}/reject`, { review_note }) as Promise<ComplianceItem>
}
