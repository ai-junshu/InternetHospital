import { useEffect, useState } from 'react'
import { Picker, ScrollView, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  listStores,
  listTherapists,
  listSchedules,
  listCustomers,
  type Store,
  type Therapist,
  type Schedule,
  type Customer,
} from '@/services/mt'

const AM_PM_LABEL: Record<string, string> = { morning: '上午', afternoon: '下午', evening: '晚上' }
const STATUS_LABEL: Record<string, string> = { open: '可约', closed: '已约满' }
const AUTH_LABEL: Record<string, string> = { authorized: '已授权', unauthorized: '未授权' }

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export default function TherapistWorkbench() {
  const [therapistId, setTherapistId] = useState<number>()
  const [therapist, setTherapist] = useState<Therapist>()
  const [store, setStore] = useState<Store>()
  const [picking, setPicking] = useState(false)
  const [stores, setStores] = useState<Store[]>([])
  const [therapists, setTherapists] = useState<Therapist[]>([])
  const [storeIdx, setStoreIdx] = useState(0)
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])

  // 首屏：从 Storage 读取已选调理师，否则进入选择态
  useEffect(() => {
    const id = Taro.getStorageSync('therapistId') as number | undefined
    if (id) {
      setTherapistId(id)
      loadAll(id)
    } else {
      setPicking(true)
      listStores({ page: 1, page_size: 50 }).then((r) => setStores(r.items)).catch(() => Taro.showToast({ title: '门店加载失败', icon: 'none' }))
    }
  }, [])

  const loadAll = async (id: number) => {
    try {
      const [therapistRes, scheduleRes, customerRes] = await Promise.all([
        listTherapists(0, { page: 1, page_size: 200 }),
        listSchedules(id, { page: 1, page_size: 50 }),
        listCustomers({ page: 1, page_size: 20 }),
      ])
      const t = therapistRes.items.find((x) => x.id === id)
      if (t) {
        setTherapist(t)
        const s = (await listStores({ page: 1, page_size: 50 })).items.find((x) => x.id === t.store_id)
        if (s) setStore(s)
      }
      setSchedules(scheduleRes.items)
      setCustomers(customerRes.items)
    } catch {
      Taro.showToast({ title: '数据加载失败', icon: 'none' })
    }
  }

  // 选择门店 -> 拉取该门店调理师
  const onStorePick = (e: any) => {
    const idx = Number(e.detail.value)
    setStoreIdx(idx)
    const sid = stores[idx].id
    listTherapists(sid, { page: 1, page_size: 50 })
      .then((r) => setTherapists(r.items))
      .catch(() => Taro.showToast({ title: '调理师加载失败', icon: 'none' }))
  }

  // 选中调理师 -> 存 Storage 并加载工作台
  const pickTherapist = (t: Therapist) => {
    Taro.setStorageSync('therapistId', t.id)
    setTherapistId(t.id)
    setTherapist(t)
    setTherapists([])
    setPicking(false)
    loadAll(t.id)
  }

  const switchAccount = () => {
    Taro.removeStorageSync('therapistId')
    setTherapistId(undefined)
    setTherapist(undefined)
    setStore(undefined)
    setSchedules([])
    setCustomers([])
    setPicking(true)
    listStores({ page: 1, page_size: 50 }).then((r) => setStores(r.items)).catch(() => {})
  }

  const today = todayStr()
  const todaySchedules = schedules.filter((s) => s.work_date === today)

  // 快捷录入入口（复用 detail 页 URL 模式，customer_id 可选）
  const entries = [
    { label: '疼痛评估', url: '/pages/mt/pain/index' },
    { label: '照护计划', url: '/pages/mt/plans/index' },
    { label: '治疗记录', url: '/pages/mt/records/index' },
    { label: '效果四档', url: '/pages/mt/effect/index' },
    { label: '风险画像', url: '/pages/mt/risk/index' },
    { label: '复购预测', url: '/pages/mt/repurchase/index' },
    { label: '排班标签', url: '/pages/mt/scheduling/index' },
    { label: '客户管理', url: '/pages/mt/customers/index' },
  ]

  // 选择态：门店 -> 调理师
  if (picking) {
    return (
      <View className='mt-page'>
        <Text className='mt-label' style={{ fontSize: '16px', fontWeight: 600 }}>选择您的调理师账号</Text>
        <View style={{ marginTop: '16px' }}>
          <Text className='mt-label'>所属门店</Text>
          <Picker mode='selector' range={stores.map((s) => s.name || `门店${s.id}`)} value={storeIdx} onChange={onStorePick}>
            <View className='mt-input'>{stores[storeIdx]?.name || `门店${stores[storeIdx]?.id}` || '请选择门店'}</View>
          </Picker>
        </View>
        <ScrollView style={{ marginTop: '16px' }}>
          {therapists.length === 0 && (
            <Text className='mt-tip'>{stores.length ? '请选择门店后查看调理师' : '加载门店中…'}</Text>
          )}
          {therapists.map((t) => (
            <View key={t.id} className='mt-card' onClick={() => pickTherapist(t)}>
              <Text style={{ fontSize: '15px' }}>{t.name || t.name_mask || `调理师${t.id}`}</Text>
              <Text className='mt-tip'>ID {t.id} · 门店 {t.store_id}</Text>
            </View>
          ))}
        </ScrollView>
      </View>
    )
  }

  return (
    <ScrollView className='mt-page' scrollY>
      {/* 顶部身份条 */}
      <View style={{ background: 'linear-gradient(135deg,#1677FF,#13C2C2)', borderRadius: '0 0 16px 16px', padding: '18px 16px', color: '#fff' }}>
        <View style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <View>
            <Text style={{ fontSize: '18px', fontWeight: 600 }}>
              {therapist?.name || therapist?.name_mask || `调理师${therapistId}`} 工作台
            </Text>
            <Text style={{ display: 'block', fontSize: '12px', opacity: 0.85, marginTop: '4px' }}>
              {store ? `${store.name} · ` : ''}今日 {today}
            </Text>
          </View>
          <View onClick={switchAccount} style={{ fontSize: '13px', padding: '6px 12px', background: 'rgba(255,255,255,0.2)', borderRadius: '14px' }}>
            切换账号
          </View>
        </View>
      </View>

      {/* 今日排班 */}
      <View className='mt-card' style={{ marginTop: '14px' }}>
        <Text className='mt-label' style={{ fontSize: '15px', fontWeight: 600 }}>今日排班</Text>
        {todaySchedules.length === 0 ? (
          <Text className='mt-tip' style={{ marginTop: '10px' }}>今日暂无排班，可在「排班标签」中新增</Text>
        ) : (
          <View style={{ marginTop: '10px' }}>
            {todaySchedules.map((s, i) => (
              <View key={s.id || i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: i === todaySchedules.length - 1 ? 'none' : '1px solid #f0f0f0' }}>
                <View>
                  <Text style={{ fontSize: '14px' }}>{AM_PM_LABEL[s.am_pm || ''] || s.am_pm || '时段'}</Text>
                  <Text className='mt-tip' style={{ display: 'block' }}>
                    {s.start_time || '--:--'} - {s.end_time || '--:--'} · 名额 {s.capacity ?? '--'}
                  </Text>
                </View>
                <Text style={{ fontSize: '12px', color: s.status === 'open' ? '#52C41A' : '#FA8C16' }}>
                  {STATUS_LABEL[s.status || ''] || s.status || ''}
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* 我的客户 */}
      <View className='mt-card' style={{ marginTop: '14px' }}>
        <View style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text className='mt-label' style={{ fontSize: '15px', fontWeight: 600 }}>我的客户</Text>
          <Text className='mt-link' onClick={() => Taro.navigateTo({ url: '/pages/mt/customers/index' })}>全部 ›</Text>
        </View>
        {customers.length === 0 ? (
          <Text className='mt-tip' style={{ marginTop: '10px' }}>暂无客户</Text>
        ) : (
          <View style={{ marginTop: '10px' }}>
            {customers.slice(0, 6).map((c) => (
              <View key={c.id} className='mt-card' style={{ marginBottom: '8px', boxShadow: 'none', border: '1px solid #f0f0f0' }} onClick={() => Taro.navigateTo({ url: `/pages/mt/customers/detail?id=${c.id}` })}>
                <View style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={{ fontSize: '14px' }}>{c.name_mask || `客户${c.id}`}</Text>
                  <Text className='mt-tag' style={{ color: c.auth_status === 'authorized' ? '#52C41A' : '#FA8C16', borderColor: c.auth_status === 'authorized' ? '#b7eb8f' : '#ffd591' }}>
                    {AUTH_LABEL[c.auth_status] || c.auth_status}
                  </Text>
                </View>
                <Text className='mt-tip' style={{ display: 'block', marginTop: '2px' }}>来源门店 {c.source_store_id ?? '--'} · {c.gender || '—'}</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* 快捷录入 */}
      <View className='mt-card' style={{ marginTop: '14px', marginBottom: '20px' }}>
        <Text className='mt-label' style={{ fontSize: '15px', fontWeight: 600 }}>快捷录入</Text>
        <View style={{ display: 'flex', flexWrap: 'wrap', marginTop: '12px' }}>
          {entries.map((e) => (
            <View
              key={e.label}
              onClick={() => Taro.navigateTo({ url: e.url })}
              style={{ width: '23%', margin: '1%', textAlign: 'center', padding: '12px 4px', background: '#F5F7FA', borderRadius: '10px' }}
            >
              <Text style={{ fontSize: '13px', color: '#262626' }}>{e.label}</Text>
            </View>
          ))}
        </View>
      </View>
    </ScrollView>
  )
}
