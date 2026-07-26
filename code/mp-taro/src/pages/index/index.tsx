import { useState } from 'react'
import { Text, View, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'

const PRIMARY = '#1677FF'
const BG = '#F5F7FA'

const SERVICES = [
  { key: 'consult', label: '在线复诊', desc: '图文沟通 · 复诊续方', url: '/pages/doctor-consult/index', icon: '💬' },
  { key: 'rx', label: '我的处方', desc: '药师审核 · 电子处方', url: '/pages/prescription/index', icon: '📋' },
  { key: 'buy', label: '去开药', desc: '处方药 · 凭方购买', url: '/pages/order/index', icon: '💊' },
  { key: 'record', label: '健康档案', desc: '问诊 · 处方记录', url: '/pages/health-record/index', icon: '🗂️' },
]

export default function Home() {
  const token = Taro.getStorageSync('token')
  const [showConfirm, setShowConfirm] = useState(true)

  const go = (url: string) => {
    if (!token && url !== '/pages/doctor-consult/index') {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      Taro.navigateTo({ url: '/pages/login/index' })
      return
    }
    Taro.navigateTo({ url })
  }

  return (
    <View style={{ minHeight: '100vh', background: BG, padding: '20px 16px 40px' }}>
      {/* 品牌区 */}
      <View style={{ padding: '16px 8px 8px' }}>
        <Text style={{ display: 'block', fontSize: '22px', fontWeight: 600, color: '#1F1F1F' }}>
          互联网医疗中心
        </Text>
        <Text style={{ display: 'block', marginTop: '4px', fontSize: '13px', color: '#8C8C8C' }}>
          在线复诊 · 电子处方 · 药品配送
        </Text>
      </View>

      {/* 复诊确认弹窗 */}
      {showConfirm && (
        <View
          style={{
            position: 'fixed',
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 99,
            padding: '0 24px',
          }}
        >
          <View
            style={{
              background: '#fff',
              borderRadius: '16px',
              padding: '24px 20px',
              width: '100%',
            }}
          >
            <Text style={{ display: 'block', fontSize: '17px', fontWeight: 600, marginBottom: '10px' }}>
              服务须知
            </Text>
            <Text style={{ display: 'block', fontSize: '14px', color: '#595959', lineHeight: '22px' }}>
              根据国家规定，互联网诊疗仅适用于复诊患者。本服务不适用于首诊及急危重症。请您确认已在线下医疗机构有过就诊记录。
            </Text>
            <Button
              type='primary'
              style={{ marginTop: '18px', background: PRIMARY }}
              onClick={() => setShowConfirm(false)}
            >
              我已了解（仅复诊）
            </Button>
          </View>
        </View>
      )}

      {/* 服务入口卡片 */}
      <View style={{ marginTop: '12px' }}>
        {SERVICES.map((s) => (
          <View
            key={s.key}
            onClick={() => go(s.url)}
            style={{
              background: '#fff',
              borderRadius: '14px',
              padding: '16px',
              marginBottom: '12px',
              display: 'flex',
              alignItems: 'center',
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
            }}
          >
            <Text style={{ fontSize: '26px', marginRight: '14px' }}>{s.icon}</Text>
            <View style={{ flex: 1 }}>
              <Text style={{ display: 'block', fontSize: '16px', fontWeight: 500 }}>{s.label}</Text>
              <Text style={{ display: 'block', fontSize: '12px', color: '#8C8C8C', marginTop: '2px' }}>
                {s.desc}
              </Text>
            </View>
            <Text style={{ color: '#bfbfbf', fontSize: '18px' }}>›</Text>
          </View>
        ))}
      </View>

      {/* 个人中心入口 */}
      <View
        onClick={() => go('/pages/profile/index')}
        style={{
          marginTop: '8px',
          textAlign: 'center',
          color: PRIMARY,
          fontSize: '14px',
          padding: '12px',
        }}
      >
        {token ? '进入个人中心' : '去登录'}
      </View>
    </View>
  )
}
