import { useEffect, useState } from 'react'
import { Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { listConsultations, listPrescriptions, type Consultation, type Prescription } from '@/services/ih'

export default function HealthRecord() {
  const user = Taro.getStorageSync('user') || {}
  const [consults, setConsults] = useState<Consultation[]>([])
  const [rxs, setRxs] = useState<Prescription[]>([])

  useEffect(() => {
    const load = async () => {
      try {
        const [c, p] = await Promise.all([
          listConsultations({ page: 1, page_size: 20, patient_id: user.id }),
          listPrescriptions({ page: 1, page_size: 20 }),
        ])
        setConsults(c.items)
        setRxs(p.items)
      } catch {
        // request 已弹 toast
      }
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const Section = ({ title, count }: { title: string; count: number }) => (
    <Text style={{ display: 'block', fontSize: '15px', fontWeight: 600, margin: '16px 6px 8px' }}>
      {title}（{count}）
    </Text>
  )

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', padding: '12px' }}>
      <Text style={{ display: 'block', fontSize: '18px', fontWeight: 600, margin: '4px 4px 4px' }}>
        健康档案
      </Text>
      <Text style={{ display: 'block', fontSize: '12px', color: '#8C8C8C', margin: '0 6px' }}>
        聚合您的问诊、处方记录，便于复诊与连续性健康管理
      </Text>

      <Section title='问诊记录' count={consults.length} />
      {consults.length === 0 && (
        <Text style={{ display: 'block', color: '#aaa', margin: '0 6px' }}>暂无问诊记录</Text>
      )}
      {consults.map((c) => (
        <View key={c.id} style={card}>
          <Text style={{ display: 'block', fontSize: '14px' }}>问诊单：{c.consultation_no}</Text>
          <Text style={{ display: 'block', fontSize: '12px', color: '#8C8C8C', marginTop: '4px' }}>
            主诉：{c.chief_complaint || '—'} · {c.status}
          </Text>
        </View>
      ))}

      <Section title='处方记录' count={rxs.length} />
      {rxs.length === 0 && (
        <Text style={{ display: 'block', color: '#aaa', margin: '0 6px' }}>暂无处方记录</Text>
      )}
      {rxs.map((p) => (
        <View key={p.id} style={card}>
          <Text style={{ display: 'block', fontSize: '14px' }}>处方号：{p.prescription_no}</Text>
          <Text style={{ display: 'block', fontSize: '12px', color: '#8C8C8C', marginTop: '4px' }}>
            诊断：{p.diagnose || '—'} · {p.status}
          </Text>
        </View>
      ))}
    </View>
  )
}

const card: Record<string, string> = {
  background: '#fff',
  borderRadius: '12px',
  padding: '14px',
  marginBottom: '10px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
}
