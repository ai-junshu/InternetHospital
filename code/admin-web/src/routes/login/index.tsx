import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LoginForm, ProFormSelect, ProFormText } from '@ant-design/pro-components'
import { message } from 'antd'
import http from '@/services/request'
import { API_BASE } from '@/constants/api'

const ROLES = [
  { label: '平台运营（platform）', value: 'platform' },
  { label: '门店管理员（store）', value: 'store' },
  { label: '调理师（therapist）', value: 'therapist' },
  { label: '星耀产业资本（xingyao）', value: 'xingyao' },
  { label: '执业医师（doctor）', value: 'doctor' },
  { label: '患者（patient）', value: 'patient' },
]

export default function LoginPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { role: string; sub?: string }) => {
    setLoading(true)
    try {
      const data = await http.post(`${API_BASE}/auth/dev-token`, {
        role: values.role,
        sub: values.sub?.trim() || '1',
      })
      const token = (data as { access_token?: string })?.access_token
      if (!token) {
        message.error('未获取到令牌，请重试')
        return false
      }
      localStorage.setItem('token', token)
      localStorage.setItem('role', values.role)
      localStorage.setItem('uid', (values.sub?.trim() || '1'))
      message.success('登录成功，正在进入后台')
      navigate('/', { replace: true })
      return true
    } catch (e) {
      console.error(e)
      message.error('获取开发令牌失败，请确认后端处于 debug 模式（settings.debug=True）')
      return false
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0b1f4d 0%, #1677ff 55%, #4096ff 100%)',
        padding: 24,
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 920,
          display: 'flex',
          borderRadius: 16,
          overflow: 'hidden',
          boxShadow: '0 24px 60px rgba(8, 24, 66, 0.35)',
          background: '#fff',
        }}
      >
        <div
          style={{
            flex: 1,
            padding: '48px 40px',
            color: '#fff',
            background:
              'radial-gradient(120% 120% at 0% 0%, rgba(64,150,255,0.55) 0%, rgba(11,31,77,0) 55%), linear-gradient(160deg, #0b1f4d 0%, #123a8f 100%)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
          className="login-brand"
        >
          <div>
            <div style={{ fontSize: 26, fontWeight: 600, letterSpacing: 1 }}>
              互联网医疗中心平台
            </div>
            <div style={{ marginTop: 8, opacity: 0.85, fontSize: 14 }}>
              健康数据中台 · 运营后台
            </div>
          </div>
          <div style={{ marginTop: 32 }}>
            <div style={{ fontSize: 15, lineHeight: 1.9, opacity: 0.95 }}>
              双主线能力 · 一站贯通
            </div>
            <ul style={{ marginTop: 12, paddingLeft: 18, fontSize: 13, lineHeight: 2, opacity: 0.8 }}>
              <li>互联网医院：在线复诊 · 电子处方 · 药品销售</li>
              <li>健康数据中台：门店赋能 · 复购预测 · 风险画像</li>
              <li>合规大脑：等保三级 · 审计可追溯</li>
            </ul>
          </div>
          <div style={{ fontSize: 12, opacity: 0.6 }}>
            开发态登录 · 仅用于本地联调与演示
          </div>
        </div>

        <div style={{ flex: 1, padding: '56px 44px', display: 'flex', alignItems: 'center' }}>
          <LoginForm
            title="运营后台登录"
            subTitle="选择角色以签发开发态令牌"
            loading={loading}
            onFinish={onFinish}
            submitter={{ searchConfig: { submitText: '获取开发令牌并登录' } }}
            style={{ width: '100%' }}
          >
            <ProFormSelect
              name="role"
              label="登录角色"
              options={ROLES}
              initialValue="platform"
              rules={[{ required: true, message: '请选择角色' }]}
            />
            <ProFormText
              name="sub"
              label="用户 ID（可选）"
              placeholder="默认 1，对应审计主体 ID"
            />
            <p style={{ color: '#8C8C8C', fontSize: 12, margin: '4px 0 0' }}>
              说明：开发态通过 <code>/auth/dev-token</code> 签发 JWT；生产环境将切换为正式账号登录（P3 补齐）。
            </p>
          </LoginForm>
        </div>
      </div>
    </div>
  )
}
