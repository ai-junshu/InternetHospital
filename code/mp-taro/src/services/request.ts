import Taro from '@tarojs/taro'
import { API_BASE } from '@/constants/api'

// 统一响应（技术架构第10.2章）
interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
  timestamp: number
  requestId: string
}

// 错误码分段（与 backend ErrorCode 对齐）：1xxx 参数 / 2xxx 鉴权 / 3xxx 业务 / 4xxx 合规 / 5xxx 系统
const AUTH_CODES = [2001, 2002, 2003]

export async function request<T = any>(
  path: string,
  options: Omit<Taro.request.Option, 'url'> & { method?: any } = {},
): Promise<T> {
  const token = Taro.getStorageSync('token')
  const header: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.header as Record<string, string>),
  }
  if (token) header['Authorization'] = `Bearer ${token}`

  const res = await Taro.request({
    url: `${API_BASE}${path}`,
    method: options.method || 'GET',
    ...options,
    header,
  })

  const body = res.data as ApiResponse<T>
  if (body.code !== 0) {
    Taro.showToast({ title: body.message || '请求失败', icon: 'none' })
    if (AUTH_CODES.includes(body.code)) {
      Taro.removeStorageSync('token')
    }
    throw new Error(body.message)
  }
  return body.data
}
