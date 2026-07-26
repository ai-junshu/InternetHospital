// API 路径常量（技术架构第10.2章：/api/v1/{ih,mt,plat}/...）
// 基准来自 config/dev.ts 或 config/prod.ts 注入的 process.env.API_BASE
export const API_BASE = process.env.API_BASE || 'http://localhost:8000/api/v1'

export const API = {
  // 互联网医院（ih）
  loginWx: '/ih/users/login/wx',
  doctors: '/ih/doctors',
  prescriptions: '/ih/prescriptions',
  orders: '/ih/orders',
  consultations: '/ih/consultations',
  doctorSchedules: '/ih/schedules',
  drugs: '/ih/drugs',
  // 健康数据中台（mt）
  customers: '/mt/customers',
  painAssessments: '/mt/pain-assessments',
  carePlans: '/mt/care-plans',
  treatmentRecords: '/mt/treatment-records',
}
