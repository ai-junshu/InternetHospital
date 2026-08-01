// 互联网医院（ih）服务封装（第10.2/11.2/13.3章）。
import { request } from './request'
import { API } from '@/constants/api'

export interface TokenData {
  access_token: string
  token_type: string
  user: { id: number; openid: string; role: string; phone_mask?: string; real_name_mask?: string }
}

export interface PageResult<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface Consultation {
  id: number
  consultation_no: string
  patient_id: number
  doctor_id: number
  order_id?: number
  chief_complaint?: string
  status: string
  started_at?: string
  ended_at?: string
}

export interface ConsultationMessage {
  id: number
  consultation_id: number
  sender_role: string
  sender_id: number
  msg_type: string
  content: string
}

export interface Prescription {
  id: number
  prescription_no: string
  patient_id: number
  doctor_id: number
  pharmacist_id?: number
  diagnose?: string
  status: string
  items_json?: unknown
  rx_check_json?: Record<string, unknown>
  signature_url?: string
  audit_at?: string
}

export interface Order {
  id: number
  order_no: string
  user_id: number
  type: string // rx | otc
  amount: number
  pay_status: string // unpaid | paid
  prescription_id?: number // 处方药凭方购买关联处方
  created_at?: string
}

export async function loginWx(
  code: string,
  extra?: { phone_mask?: string; real_name_mask?: string; role?: string },
) {
  return request<TokenData>(API.loginWx, {
    method: 'POST',
    data: { code, ...extra },
  })
}

export async function createConsultation(body: {
  patient_id: number
  doctor_id: number
  chief_complaint?: string
}) {
  return request<Consultation>(API.consultations, {
    method: 'POST',
    data: body,
  })
}

export async function listConsultations(params: {
  page?: number
  page_size?: number
  patient_id?: number
  status?: string
}) {
  return request<PageResult<Consultation>>(API.consultations, { data: params })
}

export async function sendMessage(
  consultationId: number,
  body: { sender_role: string; sender_id: number; content: string; msg_type?: string },
) {
  return request<ConsultationMessage>(`${API.consultations}/${consultationId}/messages`, {
    method: 'POST',
    data: body,
  })
}

export async function listMessages(
  consultationId: number,
  params?: { page?: number; page_size?: number },
) {
  return request<PageResult<ConsultationMessage>>(
    `${API.consultations}/${consultationId}/messages`,
    { data: params },
  )
}

export async function listPrescriptions(params: { page?: number; page_size?: number; status?: string }) {
  return request<PageResult<Prescription>>(API.prescriptions, { data: params })
}

export async function getPrescription(id: number) {
  return request<Prescription>(`${API.prescriptions}/${id}`)
}

// 药师审核（第11.2章 药师审方，迭代 A · S2）：reviewer 由后端取当前 JWT 主体，前端仅传 action/note
export async function auditPrescription(
  rxId: number,
  body: { action: 'approve' | 'reject'; note?: string },
) {
  return request<Prescription>(`${API.prescriptions}/${rxId}/audit`, {
    method: 'PATCH',
    data: body,
  })
}

// ---------------- 订单与支付（第14.2章 微信 JSAPI + 幂等） ----------------
export async function listOrders(params: {
  page?: number
  page_size?: number
  user_id?: number
  pay_status?: string
}) {
  return request<PageResult<Order>>(API.orders, { data: params })
}

export async function createOrder(body: {
  user_id: number
  type?: string
  amount?: number
  prescription_id?: number
}) {
  return request<Order>(API.orders, {
    method: 'POST',
    data: body,
  })
}

// S5 预支付返回：前端 wx.requestPayment 调起所需字段
export interface PrepayResult {
  order_no: string
  pay_status: string
  prepay_id: string
  app_id: string
  time_stamp: string
  nonce_str: string
  package: string
  pay_sign: string
  sign_type: string
}

export async function payOrder(
  orderId: number,
  extra?: { channel?: string; description?: string; openid?: string },
) {
  return request<PrepayResult>(`${API.orders}/${orderId}/pay`, {
    method: 'POST',
    data: { channel: extra?.channel || 'wechat', description: extra?.description, openid: extra?.openid },
  })
}

// S5 dev 沙箱：模拟支付成功，驱动支付闭环（生产由微信回调完成）
export async function payMockSuccess(orderId: number) {
  return request<{ order_no: string; pay_status: string; trade_state: string }>(
    `${API.orders}/${orderId}/pay/mock-success`,
    { method: 'POST', data: {} },
  )
}

// ---------------- 医师端（3.2 医生端小程序） ----------------
export interface Doctor {
  id: number
  user_id: number
  license_no: string
  title?: string
  hospital_id?: number
  dept?: string
  good_at?: string
  consult_price?: number
  status: string
}

export async function getDoctors(params?: { page?: number; page_size?: number; status?: string }) {
  return request<PageResult<Doctor>>(API.doctors, { data: params })
}

export async function getDoctor(doctorId: number) {
  return request<Doctor>(`${API.doctors}/${doctorId}`)
}

export async function getConsultation(id: number) {
  return request<Consultation>(`${API.consultations}/${id}`)
}

export async function listDoctorConsultations(params: {
  doctor_id: number
  page?: number
  page_size?: number
  status?: string
}) {
  return request<PageResult<Consultation>>(API.consultations, { data: params })
}

export async function startConsultation(consultationId: number, doctorId: number) {
  return request<Consultation>(
    `${API.consultations}/${consultationId}/start?doctor_id=${doctorId}`,
    { method: 'PATCH' },
  )
}

export async function endConsultation(consultationId: number, doctorId: number) {
  return request<Consultation>(
    `${API.consultations}/${consultationId}/end?doctor_id=${doctorId}`,
    { method: 'PATCH' },
  )
}

export interface PrescriptionItem {
  name: string
  drug_id?: number
  spec?: string
  dosage?: string
  freq?: string
  qty?: number
  daily_dose?: number
  max_daily_dose?: number
  // S4 药品联动：前端选药回填的展示字段（后端按 drug_id 反查标准化）
  otc_type?: string
  unit?: string
  price?: number
}

// 开方：药品明细可经 listDrugs 从药品目录选取（drug_id 关联，见 P6 药品目录端点）。
export async function createPrescription(body: {
  patient_id: number
  doctor_id: number
  diagnose?: string
  items: PrescriptionItem[]
  patient_pregnancy?: boolean
  patient_allergies?: string[]
  signature_url?: string
}) {
  return request<Prescription>(API.prescriptions, {
    method: 'POST',
    data: body,
  })
}

// ---------------- P6: 药品目录（只读） ----------------
export interface IhDrug {
  id: number
  name: string
  spec?: string
  manufacturer?: string
  otc_type: string
  category?: string
  unit?: string
  price?: number // 分
  status: string
}

export async function listDrugs(params: {
  keyword?: string
  otc_type?: string
  category?: string
  status?: string
  page?: number
  page_size?: number
}) {
  return request<PageResult<IhDrug>>(API.drugs, { data: params })
}

export async function getDrug(id: number) {
  return request<IhDrug>(`${API.drugs}/${id}`)
}

// ---------------- P6: 医生排班 ----------------
export interface DoctorSchedule {
  id: number
  doctor_id: number
  work_date: string
  am_pm: string
  start_time: string
  end_time: string
  status: string
  capacity: number
  remark?: string
}

export async function listDoctorSchedules(params: {
  doctor_id?: number
  work_date?: string
  am_pm?: string
  status?: string
  page?: number
  page_size?: number
}) {
  return request<PageResult<DoctorSchedule>>(API.doctorSchedules, { data: params })
}

export async function createDoctorSchedule(body: {
  work_date: string
  am_pm: string
  start_time: string
  end_time: string
  capacity?: number
  remark?: string
  doctor_id?: number
}) {
  return request<DoctorSchedule>(API.doctorSchedules, { method: 'POST', data: body })
}

export async function deleteDoctorSchedule(id: number) {
  return request<null>(`${API.doctorSchedules}/${id}`, { method: 'DELETE' })
}
