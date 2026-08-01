import { useEffect, useState } from 'react'
import { Text, View, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { getMe } from '@/services/ih'

const ENTRIES = [
  { label: '我的问诊', url: '/pages/patient-consult-list/index' },
  { label: '我的订单', url: '/pages/order/index' },
  { label: '我的处方', url: '/pages/prescription/index' },
  { label: '健康档案', url: '/pages/health-record/index' },
]

const ROLE_TEXT: Record<string, string> = {
  patient: '患者',
  doctor: '执业医师',
  pharmacist: '药师',
  platform: '平台运营',
}

export default function Profile() {
  const user = Taro.getStorageSync('user') || {}
  const token = Taro.getStorageSync('token')
  const [role, setRole] = useState<string>('')
  const [uid, setUid] = useState<number>()

  useEffect(() => {
    // S7 接入真实身份：getMe 返回 {user_id, role}
    if (!token) return
    getMe()
      .then((m) => {
        setRole(m.role)
        setUid(m.user_id)
      })
      .catch(() => {
        // 网络异常兜底：使用本地缓存 role
        setRole((user as { role?: string }).role || 'patient')
      })
  }, [token])

  const logout = () => {
    Taro.removeStorageSync('token')
    Taro.removeStorageSync('user')
    Taro.reLaunch({ url: '/pages/login/index' })
  }

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', padding: '12px' }}>
      {/* 用户卡片 */}
      <View
        style={{
          background: 'linear-gradient(135deg,#1677FF,#13C2C2)',
          borderRadius: '16px',
          padding: '22px 18px',
          color: '#fff',
        }}
      >
        <Text style={{ display: 'block', fontSize: '20px', fontWeight: 600 }}>
          {user.real_name_mask || '互联网医疗用户'}
        </Text>
        <Text style={{ display: 'block', fontSize: '13px', opacity: 0.9, marginTop: '6px' }}>
          账号：{user.phone_mask || (token ? '已登录' : '未登录')}
        </Text>
        <Text
          style={{
            display: 'inline-block',
            marginTop: '10px',
            fontSize: '12px',
            background: 'rgba(255,255,255,0.22)',
            borderRadius: '10px',
            padding: '3px 12px',
          }}
        >
          身份：{ROLE_TEXT[role] || role || '未登录'}
        </Text>
      </View>

      {/* 入口 */}
      <View style={{ marginTop: '12px', background: '#fff', borderRadius: '12px', overflow: 'hidden' }}>
        {ENTRIES.map((e, i) => (
          <View
            key={e.url}
            onClick={() => Taro.navigateTo({ url: e.url })}
            style={{
              padding: '16px',
              borderBottom: i < ENTRIES.length - 1 ? '1px solid #f0f0f0' : 'none',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <Text style={{ fontSize: '15px' }}>{e.label}</Text>
            <Text style={{ color: '#bfbfbf' }}>›</Text>
          </View>
        ))}
      </View>

      {token && (
        <Button style={{ marginTop: '20px', color: '#F5222D' }} onClick={logout}>
          退出登录
        </Button>
      )}

      {uid && (
        <Text style={{ display: 'block', textAlign: 'center', color: '#bfbfbf', fontSize: '11px', marginTop: '16px' }}>
          user_id: {uid}
        </Text>
      )}
    </View>
  )
}
