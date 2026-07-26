import axios, { AxiosResponse } from 'axios'
import { message } from 'antd'

// 统一请求封装（技术架构第10.2章：注入 JWT + 解析统一响应）
const http = axios.create({ baseURL: '/api/v1' })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 统一响应 { code, message, data, timestamp, requestId }；code=0 成功
http.interceptors.response.use(
  (resp: AxiosResponse) => {
    const body = resp.data
    if (body && body.code !== 0) {
      message.error(body.message || '请求失败')
      if ([2001, 2002, 2003].includes(body.code)) {
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      if (location.pathname !== '/login') window.location.assign('/login')
    }
      return Promise.reject(new Error(body.message))
    }
    return body?.data
  },
  (err) => Promise.reject(err),
)

export default http
