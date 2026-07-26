// 健康数据中台（mt）服务封装（第11.2/15.4章）。
// 统一响应经 request.ts 拦截器已解包为 data（PageResult / 实体）。
import http from './request'
import { API } from '@/constants/api'

export interface PageResult<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface Customer {
  id: number
  name_mask?: string
  gender?: string
  phone_mask?: string
  source_store_id?: number
  health_tags?: Record<string, unknown>
  auth_status: string
}

export interface RepurchasePrediction {
  id: number
  customer_id: number
  predict_time?: string
  next_visit_prob?: number
  repurchase_prob?: number
  risk_level?: string
  model_version?: string
}

export interface RiskProfile {
  id: number
  customer_id: number
  predict_time?: string
  pain_risk?: string
  comorbidity_risk?: string
  model_version?: string
}

export async function listCustomers(params: {
  page?: number
  page_size?: number
  store_id?: number
  auth_status?: string
}) {
  return http.get(API.customers, { params }) as Promise<PageResult<Customer>>
}

export async function authorizeCustomer(id: number, auth_file_url?: string) {
  return http.patch(`${API.customers}/${id}/authorize`, { auth_file_url })
}

export async function predictRepurchase(body: {
  customer_id: number
  age?: number
  visit_freq?: number
  last_gap_days?: number
}) {
  return http.post(API.repurchasePredictions, body) as Promise<RepurchasePrediction>
}

export async function listRepurchase(params: {
  page?: number
  page_size?: number
  customer_id?: number
}) {
  return http.get(API.repurchasePredictions, { params }) as Promise<
    PageResult<RepurchasePrediction>
  >
}

export async function predictRisk(body: {
  customer_id: number
  age?: number
  bmi?: number
  comorbidity_count?: number
}) {
  return http.post(API.riskProfiles, body) as Promise<RiskProfile>
}

export async function listRisk(params: {
  page?: number
  page_size?: number
  customer_id?: number
}) {
  return http.get(API.riskProfiles, { params }) as Promise<PageResult<RiskProfile>>
}

export interface StoreMetrics {
  id?: number
  date?: string
  store_id?: number
  store_name?: string
  region?: string
  appointment_cnt: number
  arrival_cnt: number
  deal_customers: number
  deal_amount: number
  deal_orders: number
  repurchase_customers: number
  nps_avg: number
}

export async function getStoreMetrics(params: {
  page?: number
  page_size?: number
  store_id?: number
  region?: string
  date_from?: string
  date_to?: string
}) {
  return http.get(API.storeMetrics, { params }) as Promise<PageResult<StoreMetrics>>
}

// ---------------- 调理师工作台（3.5） ----------------
export interface CarePlan {
  id: number
  customer_id: number
  doctor_advice_id?: number
  pain_type?: string
  goal?: string
  cycle?: string
  items_json?: unknown
  product_combo_json?: unknown
  reeval_nodes?: unknown
  status: string
  created_at?: string
}

export async function listCarePlans(params: {
  page?: number
  page_size?: number
  customer_id?: number
  status?: string
}) {
  return http.get(API.carePlans, { params }) as Promise<PageResult<CarePlan>>
}

export interface TreatmentRecord {
  id: number
  customer_id: number
  store_id: number
  therapist_id?: number
  plan_id?: number
  service_time?: string
  products_json?: Record<string, unknown>
  oper_sites_json?: Record<string, unknown>
  nps?: number
  images_json?: Record<string, unknown>
  remark?: string
  created_at?: string
}

export async function listTreatmentRecords(params: {
  page?: number
  page_size?: number
  customer_id?: number
  store_id?: number
}) {
  return http.get(API.treatmentRecords, { params }) as Promise<
    PageResult<TreatmentRecord>
  >
}

export interface PainAssessment {
  id: number
  customer_id: number
  assess_time?: string
  scale_type?: string
  score?: number
  pain_site?: string
  pain_nature?: string
  therapist_id?: number
}

export async function listPainAssessments(params: {
  page?: number
  page_size?: number
  customer_id?: number
}) {
  return http.get(API.painAssessments, { params }) as Promise<
    PageResult<PainAssessment>
  >
}

// ---------------- 门店 / 调理师（3.4.3 门店管理） ----------------
export interface Store {
  id: number
  name?: string
  region?: string
  city?: string
  type?: string
  status: string
}

export async function listStores(params: {
  page?: number
  page_size?: number
  region?: string
}) {
  return http.get(API.stores, { params }) as Promise<PageResult<Store>>
}

export interface Therapist {
  id: number
  name?: string
  license_no?: string
  store_id: number
  skill_tags?: Record<string, unknown>
  status: string
}

// 后端端点：GET /mt/stores/{store_id}/therapists（门店行级隔离）。
export async function listStoreTherapists(
  storeId: number,
  params?: { page?: number; page_size?: number },
) {
  return http.get(`${API.stores}/${storeId}/therapists`, { params }) as Promise<
    PageResult<Therapist>
  >
}

// 客户健康档案详情（3.4.1 钻取）。
export async function getCustomerDetail(id: number) {
  return http.get(`${API.customers}/${id}`) as Promise<
    Customer & { birth_date?: string; health_tags?: Record<string, unknown> }
  >
}

// ---------------- P6: 调理师排班 / 能力标签（3.4.3 门店管理） ----------------
export interface TherapistSchedule {
  id: number
  therapist_id: number
  store_id: number
  work_date: string
  am_pm: string
  start_time: string
  end_time: string
  status: string
  capacity: number
  remark?: string
}

export async function listTherapistSchedules(
  therapistId: number,
  params?: { work_date?: string; am_pm?: string; status?: string; page?: number; page_size?: number },
) {
  return http.get(`${API.therapists}/${therapistId}/schedules`, { params }) as Promise<
    PageResult<TherapistSchedule>
  >
}

export async function createTherapistSchedule(
  therapistId: number,
  body: {
    work_date: string
    am_pm: string
    start_time: string
    end_time: string
    capacity?: number
    remark?: string
  },
) {
  return http.post(`${API.therapists}/${therapistId}/schedules`, body) as Promise<TherapistSchedule>
}

export async function deleteTherapistSchedule(therapistId: number, scheduleId: number) {
  return http.delete(`${API.therapists}/${therapistId}/schedules/${scheduleId}`) as Promise<void>
}

export interface TherapistTagRel {
  therapist_id: number
  tag_id: number
  tag_name?: string
  category?: string
  assigned_by?: number
  created_at?: string
}

export async function listTherapistTags(therapistId: number) {
  return http.get(`${API.therapists}/${therapistId}/tags`) as Promise<TherapistTagRel[]>
}

export async function assignTherapistTag(therapistId: number, tagId: number) {
  return http.post(`${API.therapists}/${therapistId}/tags`, { tag_id: tagId }) as Promise<void>
}

export async function unassignTherapistTag(therapistId: number, tagId: number) {
  return http.delete(`${API.therapists}/${therapistId}/tags/${tagId}`) as Promise<void>
}

export interface TherapistTag {
  id: number
  name: string
  category?: string
  description?: string
}

export async function listTherapistTagCatalog(params?: {
  category?: string
  page?: number
  page_size?: number
}) {
  return http.get(API.therapistTags, { params }) as Promise<PageResult<TherapistTag>>
}

export async function createTherapistTag(body: {
  name: string
  category?: string
  description?: string
}) {
  return http.post(API.therapistTags, body) as Promise<TherapistTag>
}
