// 互联网医院（ih）服务封装：医师 / 处方 / 问诊 / 订单 / 药品目录（P6）。
import http from './request'
import { API } from '@/constants/api'

export interface PageResult<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

// ---------------- 医师 ----------------
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

export async function listDoctors(params: {
  page?: number
  page_size?: number
  status?: string
  dept?: string
}) {
  return http.get(API.ihDoctors, { params }) as Promise<PageResult<Doctor>>
}

export async function approveDoctor(id: number, reviewer_id: number, note?: string) {
  return http.post(`${API.ihDoctors}/${id}/approve`, { action: 'approve', reviewer_id, note }) as Promise<Doctor>
}

export async function rejectDoctor(id: number, reviewer_id: number, note?: string) {
  return http.post(`${API.ihDoctors}/${id}/reject`, { action: 'reject', reviewer_id, note }) as Promise<Doctor>
}

// ---------------- 处方 ----------------
export interface Prescription {
  id: number
  prescription_no: string
  patient_id: number
  doctor_id: number
  pharmacist_id?: number
  diagnose?: string
  status: string
  rx_check_json?: Record<string, unknown>
}

export async function listPrescriptions(params: {
  page?: number
  page_size?: number
  status?: string
}) {
  return http.get(API.ihPrescriptions, { params }) as Promise<PageResult<Prescription>>
}

export async function auditPrescription(
  id: number,
  body: { action: 'approve' | 'reject'; reviewer_id: number; note?: string },
) {
  return http.patch(`${API.ihPrescriptions}/${id}/audit`, body) as Promise<Prescription>
}

// ---------------- 订单 ----------------
export interface Order {
  id: number
  order_no: string
  user_id: number
  type: string
  amount: number
  pay_status: string
  prescription_id?: number | null
  created_at?: string
}

export async function listOrders(params: {
  page?: number
  page_size?: number
  user_id?: number
  pay_status?: string
}) {
  return http.get(API.ihOrders, { params }) as Promise<PageResult<Order>>
}

// ---------------- 在线复诊（会话） ----------------
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

export async function listConsultations(params: {
  page?: number
  page_size?: number
  status?: string
  patient_id?: number
  doctor_id?: number
}) {
  return http.get(API.ihConsultations, { params }) as Promise<PageResult<Consultation>>
}

// ---------------- P6: 药品目录（platform 管理） ----------------
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
  return http.get(API.ihDrugs, { params }) as Promise<PageResult<IhDrug>>
}

export async function getDrug(id: number) {
  return http.get(`${API.ihDrugs}/${id}`) as Promise<IhDrug>
}

export async function createDrug(body: {
  name: string
  spec?: string
  manufacturer?: string
  otc_type: string
  category?: string
  unit?: string
  price: number
  status?: string
}) {
  return http.post(API.ihDrugs, body) as Promise<IhDrug>
}

export async function updateDrug(
  id: number,
  body: {
    name?: string
    spec?: string
    manufacturer?: string
    otc_type?: string
    category?: string
    unit?: string
    price?: number
    status?: string
  },
) {
  return http.patch(`${API.ihDrugs}/${id}`, body) as Promise<IhDrug>
}

export async function deleteDrug(id: number) {
  return http.delete(`${API.ihDrugs}/${id}`) as Promise<void>
}

// ---------------- 患者（用户） ----------------
// 后端 UserOut 返回脱敏字段（real_name_mask/phone_mask/id_card_mask），
// 前端需按此命名渲染（不可臆造 nickname/phone/gender）。
export interface IhPatient {
  id: number
  openid: string
  real_name_mask?: string
  phone_mask?: string
  id_card_mask?: string
  user_type?: string
  role: string
}

export async function listPatients(params: {
  page?: number
  page_size?: number
  keyword?: string
}) {
  return http.get(API.ihUsers, { params }) as Promise<PageResult<IhPatient>>
}

export async function getPatient(id: number) {
  return http.get(`${API.ihUsers}/${id}`) as Promise<IhPatient>
}

// ---------------- 订单支付（mock，待商户号） ----------------
export async function payOrder(orderId: number) {
  return http.post(`${API.ihOrders}/${orderId}/pay`, {}) as Promise<{
    order_no: string
    pay_status: string
    prepay_id?: string
  }>
}

// ---------------- 医生排班（医生/平台管理） ----------------
export interface IhSchedule {
  id: number
  doctor_id: number
  work_date: string
  am_pm: string
  start_time?: string
  end_time?: string
  status?: string
  created_at?: string
}

export async function listSchedules(params: {
  page?: number
  page_size?: number
  doctor_id?: number
  work_date?: string
  am_pm?: string
  status?: string
}) {
  return http.get(API.ihSchedules, { params }) as Promise<PageResult<IhSchedule>>
}

// 后端 DoctorScheduleCreate：work_date/am_pm/start_time/end_time 必填
export async function createSchedule(body: {
  doctor_id?: number
  work_date: string
  am_pm: string
  start_time: string
  end_time: string
  capacity?: number
  remark?: string
}) {
  return http.post(API.ihSchedules, body) as Promise<IhSchedule>
}

export async function updateSchedule(
  id: number,
  body: {
    work_date?: string
    am_pm?: string
    start_time?: string
    end_time?: string
    status?: string
    capacity?: number
    remark?: string
  },
) {
  return http.patch(`${API.ihSchedules}/${id}`, body) as Promise<IhSchedule>
}

export async function deleteSchedule(id: number) {
  return http.delete(`${API.ihSchedules}/${id}`) as Promise<void>
}

export async function getSchedule(id: number) {
  return http.get(`${API.ihSchedules}/${id}`) as Promise<IhSchedule>
}

// ---------------- 问诊详情 / 结束 ----------------
export async function getConsultation(id: number) {
  return http.get(`${API.ihConsultations}/${id}`) as Promise<Consultation>
}

export async function endConsultation(id: number, doctorId: number) {
  return http.patch(`${API.ihConsultations}/${id}/end`, null, {
    params: { doctor_id: doctorId },
  }) as Promise<Consultation>
}
