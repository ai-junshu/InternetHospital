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

export async function approveDoctor(id: number) {
  return http.post(`${API.ihDoctors}/${id}/approve`) as Promise<Doctor>
}

export async function rejectDoctor(id: number) {
  return http.post(`${API.ihDoctors}/${id}/reject`) as Promise<Doctor>
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
