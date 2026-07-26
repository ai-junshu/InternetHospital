import { useEffect, useState } from 'react'
import { Button, ScrollView, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  getDoctors,
  listDoctorConsultations,
  type Consultation,
  type Doctor,
} from '@/services/ih'

export default function DoctorWorkbench() {
  const [doctor, setDoctor] = useState<Doctor>()
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [picking, setPicking] = useState(false)
  const [list, setList] = useState<Consultation[]>([])
  const [tab, setTab] = useState<'open' | 'ongoing' | 'ended'>('open')

  const doctorId = Taro.getStorageSync('doctorId') as number | undefined

  const load = async (id: number) => {
    const res = await listDoctorConsultations({ doctor_id: id, page: 1, page_size: 200 })
    setList(res.items)
    const d = (await getDoctors({ page: 1, page_size: 50 })).items.find((x) => x.id === id)
    if (d) setDoctor(d)
  }

  useEffect(() => {
    if (!doctorId) {
      setPicking(true)
      getDoctors({ page: 1, page_size: 50 }).then((r) => setDoctors(r.items))
      return
    }
    load(doctorId)
  }, [])

  const pickDoctor = (d: Doctor) => {
    Taro.setStorageSync('doctorId', d.id)
    setDoctor(d)
    setDoctors([])
    setPicking(false)
    load(d.id)
  }

  const counts = {
    open: list.filter((c) => c.status === 'open').length,
    ongoing: list.filter((c) => c.status === 'ongoing').length,
    ended: list.filter((c) => c.status === 'ended').length,
    total: list.length,
  }

  if (picking) {
    return (
      <View style={{ padding: '24px 16px' }}>
        <Text style={{ fontSize: '16px', fontWeight: 600 }}>选择您的执业账号</Text>
        <ScrollView style={{ marginTop: '16px' }}>
          {doctors.map((d) => (
            <View
              key={d.id}
              onClick={() => pickDoctor(d)}
              style={{
                padding: '14px 16px',
                background: '#fff',
                borderRadius: '10px',
                marginBottom: '10px',
                boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
              }}
            >
              <Text style={{ fontSize: '15px' }}>{d.title || '医师'} · {d.dept || '全科'}</Text>
              <Text style={{ display: 'block', fontSize: '12px', color: '#8c8c8c', marginTop: '4px' }}>
                执业编号 {d.license_no} · {d.status}
              </Text>
            </View>
          ))}
        </ScrollView>
      </View>
    )
  }

  const cards = [
    { label: '待接诊', value: counts.open, color: '#FA8C16' },
    { label: '问诊中', value: counts.ongoing, color: '#1677FF' },
    { label: '已结束', value: counts.ended, color: '#52C41A' },
    { label: '累计接诊', value: counts.total, color: '#722ED1' },
  ]
  const filtered = list.filter((c) => c.status === tab)
  const tabs: { key: 'open' | 'ongoing' | 'ended'; label: string }[] = [
    { key: 'open', label: '待接诊' },
    { key: 'ongoing', label: '问诊中' },
    { key: 'ended', label: '已结束' },
  ]

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', padding: '16px' }}>
      <View style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ fontSize: '17px', fontWeight: 600 }}>{doctor?.title || '医师'} 工作台</Text>
        <Button
          size='mini'
          onClick={() => {
            Taro.removeStorageSync('doctorId')
            setPicking(true)
          }}
        >
          切换账号
        </Button>
      </View>

      <View style={{ display: 'flex', flexWrap: 'wrap', marginTop: '16px' }}>
        {cards.map((c) => (
          <View
            key={c.label}
            style={{
              width: '48%',
              margin: '1%',
              background: '#fff',
              borderRadius: '12px',
              padding: '16px',
              boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
            }}
          >
            <Text style={{ fontSize: '13px', color: '#8c8c8c' }}>{c.label}</Text>
            <Text style={{ display: 'block', fontSize: '26px', fontWeight: 700, color: c.color, marginTop: '6px' }}>
              {c.value}
            </Text>
          </View>
        ))}
      </View>

      <View style={{ display: 'flex', marginTop: '20px', background: '#fff', borderRadius: '12px', overflow: 'hidden' }}>
        {tabs.map((t) => (
          <View
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              flex: 1,
              textAlign: 'center',
              padding: '12px',
              color: tab === t.key ? '#1677FF' : '#595959',
              fontWeight: tab === t.key ? 600 : 400,
              borderBottom: tab === t.key ? '2px solid #1677FF' : '2px solid transparent',
            }}
          >
            <Text>{t.label}</Text>
          </View>
        ))}
      </View>

      <View style={{ marginTop: '12px' }}>
        {filtered.length === 0 && (
          <Text style={{ display: 'block', textAlign: 'center', color: '#8c8c8c', marginTop: '40px' }}>
            暂无{tab === 'open' ? '待接诊' : tab === 'ongoing' ? '问诊中' : '已结束'}会话
          </Text>
        )}
        {filtered.map((c) => (
          <View
            key={c.id}
            onClick={() => Taro.navigateTo({ url: `/pages/doctor-chat/index?id=${c.id}` })}
            style={{
              background: '#fff',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '10px',
              boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
            }}
          >
            <Text style={{ fontSize: '15px' }}>会话 {c.consultation_no}</Text>
            <Text style={{ display: 'block', fontSize: '13px', color: '#595959', marginTop: '4px' }}>
              主诉：{c.chief_complaint || '—'} · 患者ID {c.patient_id}
            </Text>
          </View>
        ))}
      </View>
    </View>
  )
}
