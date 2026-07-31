import { useEffect, useState } from 'react'
import { Button, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { getPrescription, type Prescription, type PrescriptionItem } from '@/services/ih'

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending_audit: { label: '待药师审核', color: '#FA8C16' },
  approved: { label: '已通过', color: '#52C41A' },
  rejected: { label: '已驳回', color: '#F5222D' },
}

export default function PrescriptionDetail() {
  const params = Taro.getCurrentInstance().router?.params || {}
  const id = Number(params.id)
  const [rx, setRx] = useState<Prescription>()

  useEffect(() => {
    if (!id) return
    getPrescription(id)
      .then(setRx)
      .catch(() => Taro.showToast({ title: '处方不存在', icon: 'none' }))
  }, [id])

  if (!rx) {
    return (
      <View style={{ padding: '20px', textAlign: 'center', color: '#aaa' }}>
        <Text>加载中…</Text>
      </View>
    )
  }

  const items = (rx.items_json as PrescriptionItem[]) || []
  const st = STATUS_MAP[rx.status] || { label: rx.status, color: '#888' }

  return (
    <View style={{ padding: '16px', background: '#F5F7FA', minHeight: '100vh' }}>
      <Text style={{ display: 'block', fontSize: '18px', fontWeight: 600, marginBottom: '12px' }}>处方详情</Text>

      <View style={card}>
        <Text style={{ display: 'block' }}>处方号：{rx.prescription_no}</Text>
        <Text style={{ display: 'block', marginTop: '6px' }}>诊断：{rx.diagnose || '-'}</Text>
        <Text style={{ display: 'block', marginTop: '6px' }}>状态：{st.label}</Text>
      </View>

      <Text style={{ display: 'block', marginTop: '12px', marginBottom: '6px', fontSize: '14px', color: '#595959' }}>
        药品明细
      </Text>
      {items.map((it, i) => (
        <View key={i} style={card}>
          <Text style={{ display: 'block', fontSize: '15px' }}>{it.name}</Text>
          <Text style={{ display: 'block', color: '#8C8C8C', fontSize: '12px', marginTop: '4px' }}>
            {[it.spec, it.dosage, it.freq].filter(Boolean).join(' · ') || '-'}
            {it.qty ? ` · ×${it.qty}` : ''}
          </Text>
        </View>
      ))}

      {Boolean(rx.rx_check_json?.hit) && (
        <View style={{ ...card, background: '#FFFBE6', borderColor: '#FFE58F' }}>
          <Text style={{ color: '#AD6800' }}>合理用药校验告警，请遵医嘱</Text>
        </View>
      )}

      {rx.status === 'approved' && (
        <Button
          type="primary"
          style={{ background: '#1677FF', marginTop: '16px' }}
          onClick={() => Taro.navigateTo({ url: `/pages/order/index?prescription_id=${rx.id}&patient_id=${rx.patient_id}` })}
        >
          凭处方购药
        </Button>
      )}
    </View>
  )
}

const card: React.CSSProperties = {
  background: '#fff',
  borderRadius: '12px',
  padding: '14px',
  marginBottom: '10px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
}
