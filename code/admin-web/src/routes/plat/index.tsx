import { Navigate, Outlet } from 'react-router-dom'
import { PageContainer } from '@ant-design/pro-components'

export default function PlatAdmin() {
  return (
    <PageContainer title="平台管理">
      <Outlet />
    </PageContainer>
  )
}

// 默认重定向到 AI 模型目录
export function PlatIndex() {
  return <Navigate to="/plat/ai-models" replace />
}
