import { useEffect, useState } from 'react'
import { Button, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { listPrescriptions, getPrescription, type Prescription } from '@/services/ih'

const STATUS_COLOR: Record<string, string> = {
  pending_audit: '#FA8C16',
  approved: '#52C41A',
  rejected: '#F5222D',
}
const STATUS_LABEL: Record<string, string> = {
  pending_audit: '待药师审核',
  approved: '已审核',
  rejected: '已驳回',
}

export default function PrescriptionPage() {
  const [list, setList] = useState<Prescription[]>([])
  const [detail, setDetail] = useState<Prescription>()

  const load = async () => {
    try {
      const res = await listPrescriptions({ page: 1, page_size: 50 })
      setList(res.items)
    } catch {
      // request 已弹 toast
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const openDetail = async (id: number) => {
    try {
      const d = await getPrescription(id)
      setDetail(d)
    } catch {
      // request 已弹 toast
    }
  }

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', padding: '12px' }}>
      <Text style={{ display: 'block', fontSize: '18px', fontWeight: 600, margin: '4px 4px 12px' }}>
        我的处方
      </Text>
      <View style={{ margin: '0 4px 12px' }}>
        <Button
          size='mini'
          onClick={() => Taro.navigateTo({ url: '/pages/drug-catalog/index' })}
        >
          药品目录
        </Button>
      </View>

      {list.length === 0 && (
        <Text style={{ display: 'block', textAlign: 'center', color: '#aaa', marginTop: '40px' }}>
          暂无处方
        </Text>
      )}

      {list.map((p) => (
        <View
          key={p.id}
          onClick={() => openDetail(p.id)}
          style={{
            background: '#fff',
            borderRadius: '12px',
            padding: '14px',
            marginBottom: '10px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
          }}
        >
          <Text style={{ display: 'block', fontSize: '15px' }}>处方号：{p.prescription_no}</Text>
          <Text style={{ display: 'block', color: '#8C8C8C', fontSize: '12px', marginTop: '4px' }}>
            诊断：{p.diagnose || '—'}
          </Text>
          <Text style={{ color: STATUS_COLOR[p.status] || '#888', fontSize: '13px', marginTop: '6px', display: 'block' }}>
            {STATUS_LABEL[p.status] || p.status}
          </Text>
        </View>
      ))}

      {/* 详情 */}
      {detail && (
        <View
          style={{
            position: 'fixed',
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.45)',
            display: 'flex',
            alignItems: 'flex-end',
            zIndex: 99,
          }}
          onClick={() => setDetail(undefined)}
        >
          <View
            style={{ background: '#fff', width: '100%', borderTopLeftRadius: '16px', borderTopRightRadius: '16px', padding: '20px 16px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <Text style={{ display: 'block', fontSize: '17px', fontWeight: 600, marginBottom: '12px' }}>处方详情</Text>
            <Text style={{ display: 'block', fontSize: '14px' }}>处方号：{detail.prescription_no}</Text>
            <Text style={{ display: 'block', fontSize: '14px', marginTop: '6px' }}>诊断：{detail.diagnose || '—'}</Text>
            <Text style={{ display: 'block', fontSize: '14px', marginTop: '6px', color: STATUS_COLOR[detail.status] }}>
              状态：{STATUS_LABEL[detail.status] || detail.status}
            </Text>
            {!!detail.items_json && (
              <Text style={{ display: 'block', fontSize: '13px', marginTop: '8px', color: '#595959' }}>
                用药明细：{String(JSON.stringify(detail.items_json))}
              </Text>
            )}
            {!!detail.rx_check_json && (
              <Text style={{ display: 'block', fontSize: '13px', marginTop: '8px', color: '#FA8C16' }}>
                合理用药审核：{String(JSON.stringify(detail.rx_check_json))}
              </Text>
            )}
          </View>
        </View>
      )}
    </View>
  )
}
