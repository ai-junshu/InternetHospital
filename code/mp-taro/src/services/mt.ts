// 健康数据中台（mt）服务封装（第11.2/11.3章：客户/疼痛评估/照护计划/治疗记录/复购/风险）。
// 风格对齐 services/ih.ts：request + API 常量 + PageResult 泛型。
import { request } from './request'
import { API } from '@/constants/api'
import type { PageResult } from './ih'

// ---------------- 客户 ----------------
export interface Customer {
  id: number
  name_mask?: string
  gender?: string
  phone_mask?: string
  source_store_id?: number
  auth_status: string // unauthorized | authorized
  created_at?: string
}

export async function listCustomers(params: { page?: number; page_size?: number; auth_status?: string }) {
  return request<PageResult<Customer>>(API.customers, { data: params })
}

export async function createCustomer(body: {
  name_mask?: string
  gender?: string
  phone_mask?: string
  source_store_id?: number
  health_tags?: Record<string, unknown>
}) {
  return request<Customer>(API.customers, { method: 'POST', data: body })
}

export async function authorizeCustomer(customerId: number, body?: { auth_file_url?: string }) {
  return request<Customer>(`${API.customers}/${customerId}/authorize`, { method: 'PATCH', data: body || {} })
}

export async function getCustomer(customerId: number) {
  return request<Customer>(`${API.customers}/${customerId}`)
}

// ---------------- 疼痛评估 ----------------
export interface PainAssessment {
  id: number
  customer_id: number
  score?: number
  pain_site?: string
  pain_nature?: string
  scale_type?: string
  assess_time?: string
  created_at?: string
}

export async function listPainAssessments(params: { page?: number; page_size?: number; customer_id?: number }) {
  return request<PageResult<PainAssessment>>(API.painAssessments, { data: params })
}

export async function createPainAssessment(body: {
  customer_id: number
  score?: number
  pain_site?: string
  pain_nature?: string
  scale_type?: string
  answers_json?: Record<string, unknown>
}) {
  return request<PainAssessment>(API.painAssessments, { method: 'POST', data: body })
}

// ---------------- 照护计划 ----------------
export interface CarePlan {
  id: number
  customer_id: number
  doctor_advice_id?: number
  pain_type?: string
  goal?: string
  cycle?: string
  status: string
  items_json?: unknown
  product_combo_json?: unknown
  created_at?: string
}

export async function listCarePlans(params: { page?: number; page_size?: number; customer_id?: number }) {
  return request<PageResult<CarePlan>>(API.carePlans, { data: params })
}

export async function createCarePlan(body: {
  customer_id: number
  doctor_advice_id: number
  pain_type?: string
  goal?: string
  cycle?: string
  age?: number
  pain_score?: number
  chronic_count?: number
}) {
  return request<CarePlan>(API.carePlans, { method: 'POST', data: body })
}

// ---------------- 治疗记录 ----------------
export interface TreatmentRecord {
  id: number
  customer_id: number
  store_id: number
  therapist_id?: number
  plan_id?: number
  nps?: number
  service_time?: string
  remark?: string
  created_at?: string
}

export async function listTreatmentRecords(params: { page?: number; page_size?: number; customer_id?: number }) {
  return request<PageResult<TreatmentRecord>>(API.treatmentRecords, { data: params })
}

export async function createTreatmentRecord(body: {
  customer_id: number
  store_id: number
  therapist_id?: number
  plan_id?: number
  nps?: number
  products_json?: Record<string, unknown>
  remark?: string
}) {
  return request<TreatmentRecord>(API.treatmentRecords, { method: 'POST', data: body })
}

// 合规强规则2：治疗记录不可删，仅可更正留痕（PATCH 写入修订表 + 审计前后对照）
export async function reviseTreatmentRecord(
  recordId: number,
  body: {
    products_json?: Record<string, unknown>
    oper_sites_json?: Record<string, unknown>
    nps?: number
    images_json?: Record<string, unknown>
    remark?: string
    reason: string
  },
) {
  return request<TreatmentRecord>(`${API.treatmentRecords}/${recordId}`, { method: 'PATCH', data: body })
}

// ---------------- 门店 / 调理师 ----------------
export interface Store {
  id: number
  name?: string
  region?: string
  address?: string
}

export async function listStores(params: { page?: number; page_size?: number; region?: string }) {
  return request<PageResult<Store>>(API.stores, { data: params })
}

export interface Therapist {
  id: number
  store_id: number
  name?: string
  name_mask?: string
}

export async function listTherapists(storeId: number, params?: { page?: number; page_size?: number }) {
  return request<PageResult<Therapist>>(`${API.stores}/${storeId}/therapists`, { data: params })
}

// ---------------- 效果四档（合规强规则3） ----------------
export interface EffectTracking {
  id: number
  customer_id: number
  plan_id?: number
  effect_level?: string // significant | effective | ineffective | worsened
  generated_at?: string
}

export async function listEffectTracking(params: {
  page?: number
  page_size?: number
  customer_id?: number
  plan_id?: number
  effect_level?: string
}) {
  return request<PageResult<EffectTracking>>(API.effectTracking, { data: params })
}

export async function createEffectTracking(body: {
  customer_id: number
  plan_id?: number
  baseline_pain?: number
  latest_pain?: number
  nps?: number
  repurchase_count?: number
}) {
  return request<EffectTracking>(API.effectTracking, { method: 'POST', data: body })
}

// ---------------- 复购预测（AI 反馈闭环） ----------------
export interface RepurchasePrediction {
  id: number
  customer_id: number
  next_visit_prob?: number
  repurchase_prob?: number
  risk_level?: string
  model_version?: string
  predict_time?: string
}

export async function listRepurchasePredictions(params: { page?: number; page_size?: number; customer_id?: number }) {
  return request<PageResult<RepurchasePrediction>>(API.repurchasePredictions, { data: params })
}

export async function predictRepurchase(body: { customer_id: number; age?: number; visit_freq?: number; last_gap_days?: number }) {
  return request<RepurchasePrediction>(API.repurchasePredictions, { method: 'POST', data: body })
}

// ---------------- 风险画像（AI 反馈闭环） ----------------
export interface RiskProfile {
  id: number
  customer_id: number
  pain_risk?: string
  comorbidity_risk?: string
  model_version?: string
  predict_time?: string
}

export async function listRiskProfiles(params: { page?: number; page_size?: number; customer_id?: number }) {
  return request<PageResult<RiskProfile>>(API.riskProfiles, { data: params })
}

export async function predictRisk(body: { customer_id: number; age?: number; bmi?: number; comorbidity_count?: number }) {
  return request<RiskProfile>(API.riskProfiles, { method: 'POST', data: body })
}

// ---------------- 排班（Scheduling，按调理师维度） ----------------
// 后端路由：POST/GET /mt/therapists/{therapist_id}/schedules
export interface Schedule {
  id?: number
  therapist_id?: number
  store_id?: number
  work_date?: string
  am_pm?: string // morning/afternoon/evening
  start_time?: string
  end_time?: string
  status?: string // open/closed
  capacity?: number
  remark?: string
}

export async function listSchedules(therapistId: number, params?: { page?: number; page_size?: number }) {
  return request<PageResult<Schedule>>(`${API.therapistSchedules}/${therapistId}/schedules`, { data: params || {} })
}

export async function createSchedule(therapistId: number, body: {
  therapist_id: number
  work_date: string
  am_pm?: string
  start_time: string
  end_time: string
  capacity?: number
  remark?: string
}) {
  return request<Schedule>(`${API.therapistSchedules}/${therapistId}/schedules`, { method: 'POST', data: body })
}

// ---------------- 标签（Tags，目录 + 分配给调理师） ----------------
// 后端路由：GET/POST /mt/therapist-tags（目录）；POST/DELETE /mt/therapists/{therapist_id}/tags（分配/解绑）
export interface Tag {
  id: number
  name: string
  category?: string
  description?: string
}

export async function listTags(params: { page?: number; page_size?: number; category?: string }) {
  return request<PageResult<Tag>>(API.therapistTags, { data: params })
}

// 仅 platform/xingyao 角色可创建标签目录
export async function createTag(body: { name: string; category?: string; description?: string }) {
  return request<Tag>(API.therapistTags, { method: 'POST', data: body })
}

// 将标签分配给调理师（store/therapist/platform 均可）
export async function assignTag(therapistId: number, tagId: number) {
  return request<{ therapist_id: number; tag_id: number }>(
    `${API.therapistSchedules}/${therapistId}/tags`,
    { method: 'POST', data: { tag_id: tagId } },
  )
}

// 解绑调理师标签（非删除目录）
export async function unassignTag(therapistId: number, tagId: number) {
  return request<{ message?: string }>(`${API.therapistSchedules}/${therapistId}/tags/${tagId}`, { method: 'DELETE' })
}
