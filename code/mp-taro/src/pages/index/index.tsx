import { useEffect, useState } from 'react'
import { Text, View, Button, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { getDoctors, type Doctor } from '@/services/ih'

const PRIMARY = '#1677FF'
const BG = '#F5F7FA'

const SERVICES = [
  { key: 'consult', label: '在线复诊', desc: '图文沟通 · 复诊续方', url: '/pages/patient-consult-list/index', icon: '💬' },
  { key: 'rx', label: '我的处方', desc: '药师审核 · 电子处方', url: '/pages/prescription/index', icon: '📋' },
  { key: 'buy', label: '去开药', desc: '处方药 · 凭方购买', url: '/pages/order/index', icon: '💊' },
  { key: 'record', label: '健康档案', desc: '问诊 · 处方记录', url: '/pages/health-record/index', icon: '🗂️' },
]

// S7 公告/banner 本地静态占位（后端暂无公告域，预留 getAnnouncements 接口位）
const BANNER = {
  title: '在线复诊服务升级',
  desc: '疼痛管理与调理专科医师已上线，支持图文复诊与电子处方配送',
}

export default function Home() {
  const token = Taro.getStorageSync('token')
  const [showConfirm, setShowConfirm] = useState(true)
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDoctors({ page: 1, page_size: 5 })
      .then((r) => setDoctors(r.items))
      .catch(() => setDoctors([]))
      .finally(() => setLoading(false))
  }, [])

  const go = (url: string) => {
    if (!token) {
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

      {/* 公告/banner 横条（本地静态占位） */}
      <View
        style={{
          marginTop: '12px',
          background: 'linear-gradient(135deg,#1677FF 0%,#4096FF 100%)',
          borderRadius: '14px',
          padding: '14px 16px',
        }}
      >
        <Text style={{ display: 'block', fontSize: '15px', fontWeight: 600, color: '#fff' }}>
          {BANNER.title}
        </Text>
        <Text style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.85)', marginTop: '4px' }}>
          {BANNER.desc}
        </Text>
      </View>

      {/* 推荐医生 */}
      <View style={{ marginTop: '18px' }}>
        <Text style={{ fontSize: '16px', fontWeight: 600, color: '#1F1F1F', paddingLeft: '4px' }}>
          推荐医师
        </Text>
        {loading ? (
          <View style={{ marginTop: '12px' }}>
            {[0, 1, 2].map((i) => (
              <View
                key={i}
                style={{
                  background: '#fff',
                  borderRadius: '12px',
                  padding: '14px',
                  marginBottom: '10px',
                  opacity: 0.6,
                }}
              >
                <View style={{ width: '60%', height: '14px', background: '#eee', borderRadius: '7px' }} />
                <View style={{ width: '40%', height: '12px', background: '#eee', borderRadius: '6px', marginTop: '10px' }} />
              </View>
            ))}
          </View>
        ) : doctors.length === 0 ? (
          <Text style={{ display: 'block', color: '#8c8c8c', fontSize: '13px', marginTop: '10px', paddingLeft: '4px' }}>
            暂无在线医师
          </Text>
        ) : (
          <ScrollView scrollY style={{ maxHeight: '40vh', marginTop: '12px' }}>
            {doctors.map((d) => (
              <View
                key={d.id}
                onClick={() => go('/pages/patient-consult-list/index')}
                style={{
                  background: '#fff',
                  borderRadius: '12px',
                  padding: '14px',
                  marginBottom: '10px',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <View
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '21px',
                    background: PRIMARY,
                    color: '#fff',
                    fontSize: '16px',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: '12px',
                  }}
                >
                  {String(d.id).slice(-2)}
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ display: 'block', fontSize: '15px', fontWeight: 500 }}>
                    医师 #{d.id}
                  </Text>
                  <Text style={{ display: 'block', fontSize: '12px', color: '#8C8C8C', marginTop: '2px' }}>
                    {d.dept} · {d.title}
                  </Text>
                </View>
                <Text style={{ color: '#bfbfbf', fontSize: '18px' }}>›</Text>
              </View>
            ))}
          </ScrollView>
        )}
      </View>

      {/* 服务入口卡片 */}
      <View style={{ marginTop: '18px' }}>
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
