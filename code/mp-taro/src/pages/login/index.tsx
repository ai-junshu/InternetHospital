import { Button, Text, View, RadioGroup, Radio, Label } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState } from 'react'
import { loginWx } from '@/services/ih'

// 迭代 A · S1 双身份登录：三态身份选择，登录后按 role 路由工作台
const ROLE_ROUTES: Record<string, string> = {
  patient: '/pages/index/index',
  doctor: '/pages/doctor-workbench/index',
  pharmacist: '/pages/pharmacist-review/index',
}

export default function Login() {
  const [role, setRole] = useState('patient')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    if (loading) return
    setLoading(true)
    try {
      const { code } = await Taro.login()
      // 未配置 wx_appid/secret 时走开发模式：code 直接作为 openid 标识
      const data = await loginWx(code, { role })
      Taro.setStorageSync('token', data.access_token)
      Taro.setStorageSync('user', data.user)
      Taro.showToast({ title: '登录成功', icon: 'success' })
      const target = ROLE_ROUTES[data.user.role] || ROLE_ROUTES.patient
      Taro.reLaunch({ url: target })
    } catch (e) {
      // request 已弹 toast
    } finally {
      setLoading(false)
    }
  }

  return (
    <View style={{ padding: '48px 32px', textAlign: 'center' }}>
      <Text style={{ display: 'block', marginBottom: '24px', fontSize: '18px' }}>
        互联网医疗中心平台
      </Text>
      <Text style={{ display: 'block', marginBottom: '16px', fontSize: '14px', color: '#666' }}>
        请选择登录身份
      </Text>
      <RadioGroup
        style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}
        onChange={(e) => setRole(e.detail.value)}
      >
        <Label style={{ margin: '0 12px' }}>
          <Radio value='patient' checked={role === 'patient'} /> 患者
        </Label>
        <Label style={{ margin: '0 12px' }}>
          <Radio value='doctor' checked={role === 'doctor'} /> 医师
        </Label>
        <Label style={{ margin: '0 12px' }}>
          <Radio value='pharmacist' checked={role === 'pharmacist'} /> 药师
        </Label>
      </RadioGroup>
      <Button type='primary' loading={loading} onClick={handleLogin}>
        微信一键登录（{role === 'patient' ? '患者' : role === 'doctor' ? '医师' : '药师'}）
      </Button>
    </View>
  )
}
