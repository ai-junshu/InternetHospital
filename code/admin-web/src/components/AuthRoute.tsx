import type { ReactElement } from 'react'
import { Navigate } from 'react-router-dom'

// 路由守卫：未携带 token 时强制跳转登录页（与 request 拦截器 401 清理联动）
export default function AuthRoute({ children }: { children: ReactElement }) {
  const token = localStorage.getItem('token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}
