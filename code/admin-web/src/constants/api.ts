// API 路径常量（技术架构第10.2章：/api/v1/{ih,mt,plat}/...）
// 本地经 vite proxy /api → backend:8000
export const API_BASE = '/api/v1'

export const API = {
  // 门店管理后台（mt）
  stores: '/mt/stores',
  therapists: '/mt/therapists',
  therapistTags: '/mt/therapist-tags',
  customers: '/mt/customers',
  treatmentRecords: '/mt/treatment-records',
  carePlans: '/mt/care-plans',
  painAssessments: '/mt/pain-assessments',
  repurchasePredictions: '/mt/repurchase-predictions',
  riskProfiles: '/mt/risk-profiles',
  storeMetrics: '/mt/store-metrics',
  // 互联网医院（ih）
  ihDoctors: '/ih/doctors',
  ihUsers: '/ih/users',
  ihConsultations: '/ih/consultations',
  ihOrders: '/ih/orders',
  ihPrescriptions: '/ih/prescriptions',
  ihDrugs: '/ih/drugs',
  ihSchedules: '/ih/schedules',
  // 平台管理（plat）
  dataAssets: '/plat/data-assets',
  aiModels: '/plat/ai-models',
  auditLogs: '/plat/audit-logs',
  compliance: '/plat/compliance',
}
