import { useEffect, useState } from 'react'
import { Button, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  listPrescriptions,
  auditPrescription,
  type Prescription,
  type PrescriptionItem,
} from '@/services/ih'

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending_audit: { label: '待药师审核', color: '#FA8C16' },
  approved: { label: '已通过', color: '#52C41A' },
  rejected: { label: '已驳回', color: '#F5222D' },
}

export default function PharmacistReview() {
  const [list, setList] = useState<Prescription[]>([])
  const [loading, setLoading] = useState(false)
  const [processingId, setProcessingId] = useState<number>()

  const load = async () => {
    setLoading(true)
    try {
      const res = await listPrescriptions({ status: 'pending_audit', page: 1, page_size: 50 })
      setList(res.items || [])
    } catch {
      // request 已弹 toast
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleAudit = async (rxId: number, action: 'approve' | 'reject') => {
    if (processingId) return
    setProcessingId(rxId)
    try {
      await auditPrescription(rxId, { action })
      Taro.showToast({ title: action === 'approve' ? '已通过' : '已驳回', icon: 'success' })
      load()
    } catch {
      // request 已弹 toast
    } finally {
      setProcessingId(undefined)
    }
  }

  return (
    <View style={{ padding: '16px', background: '#F5F7FA', minHeight: '100vh' }}>
      <Text style={{ display: 'block', fontSize: '18px', fontWeight: 600, marginBottom: '12px' }}>
        药师审核工作台
      </Text>

      {loading && (
        <Text style={{ display: 'block', color: '#aaa', textAlign: 'center' }}>加载中…</Text>
      )}

      {!loading && list.length === 0 && (
        <Text style={{ display: 'block', color: '#aaa', textAlign: 'center', marginTop: '40px' }}>
          暂无待审核处方
        </Text>
      )}

      {list.map((rx) => {
        const items = (rx.items_json as PrescriptionItem[]) || []
        const st = STATUS_MAP[rx.status] || { label: rx.status, color: '#888' }
        return (
          <View key={rx.id} style={card}>
            <Text style={{ display: 'block', fontWeight: 600 }}>
              处方号：{rx.prescription_no}
              <Text style={{ color: st.color, fontSize: '12px', marginLeft: '8px' }}>{st.label}</Text>
            </Text>
            <Text style={{ display: 'block', marginTop: '6px' }}>诊断：{rx.diagnose || '-'}</Text>
            {items.map((it, i) => (
              <Text
                key={i}
                style={{ display: 'block', color: '#595959', fontSize: '13px', marginTop: '4px' }}
              >
                · {it.name}
                {[it.spec, it.dosage, it.freq].filter(Boolean).join(' · ') || ''}
                {it.qty ? ` ×${it.qty}` : ''}
              </Text>
            ))}
            {Boolean(rx.rx_check_json?.hit) && (
              <Text style={{ display: 'block', color: '#AD6800', fontSize: '12px', marginTop: '4px' }}>
                ⚠ 合理用药校验告警，请重点关注
              </Text>
            )}
            <View style={{ display: 'flex', marginTop: '12px', gap: '12px' }}>
              <Button
                size='mini'
                type='primary'
                loading={processingId === rx.id}
                style={{ background: '#52C41A', flex: 1 }}
                onClick={() => handleAudit(rx.id, 'approve')}
              >
                通过
              </Button>
              <Button
                size='mini'
                loading={processingId === rx.id}
                style={{ background: '#F5222D', color: '#fff', flex: 1 }}
                onClick={() => handleAudit(rx.id, 'reject')}
              >
                驳回
              </Button>
            </View>
          </View>
        )
      })}
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
