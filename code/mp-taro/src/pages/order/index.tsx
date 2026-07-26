import { useEffect, useState } from 'react'
import { Text, View, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { listOrders, createOrder, payOrder, type Order } from '@/services/ih'

const PAY_COLOR: Record<string, string> = {
  unpaid: '#FA8C16',
  paid: '#52C41A',
}
const PAY_LABEL: Record<string, string> = { unpaid: '待支付', paid: '已支付' }
const TABS = [
  { key: 'all', label: '全部' },
  { key: 'unpaid', label: '待支付' },
  { key: 'paid', label: '已支付' },
]

export default function OrderPage() {
  const user = Taro.getStorageSync('user') || {}
  const [tab, setTab] = useState('all')
  const [list, setList] = useState<Order[]>([])
  const [loading, setLoading] = useState(false)
  const [detail, setDetail] = useState<Order>()

  const load = async () => {
    setLoading(true)
    try {
      const res = await listOrders({
        page: 1,
        page_size: 50,
        user_id: user.id,
        pay_status: tab === 'all' ? undefined : tab,
      })
      setList(res.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab])

  const handleBuy = async () => {
    try {
      const order = await createOrder({ user_id: user.id, type: 'rx', amount: 0 })
      await payOrder(order.id)
      Taro.showToast({ title: '购药成功', icon: 'success' })
      load()
    } catch {
      // request 已弹 toast
    }
  }

  const handlePay = async (o: Order) => {
    try {
      await payOrder(o.id)
      Taro.showToast({ title: '支付成功', icon: 'success' })
      setDetail(undefined)
      load()
    } catch {
      // request 已弹 toast
    }
  }

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', padding: '12px' }}>
      <Text style={{ display: 'block', fontSize: '18px', fontWeight: 600, margin: '4px 4px 12px' }}>
        订单与支付
      </Text>

      {/* Tab */}
      <View style={{ display: 'flex', background: '#fff', borderRadius: '10px', padding: '4px', marginBottom: '12px' }}>
        {TABS.map((t) => (
          <View
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              flex: 1,
              textAlign: 'center',
              padding: '8px 0',
              fontSize: '14px',
              borderRadius: '8px',
              color: tab === t.key ? '#fff' : '#595959',
              background: tab === t.key ? '#1677FF' : 'transparent',
            }}
          >
            <Text>{t.label}</Text>
          </View>
        ))}
      </View>

      {/* 申请开药 */}
      <Button type='primary' style={{ background: '#1677FF', marginBottom: '12px' }} onClick={handleBuy}>
        申请开药（处方药凭处方购买）
      </Button>

      {loading && <Text style={{ color: '#aaa' }}>加载中…</Text>}
      {!loading && list.length === 0 && (
        <Text style={{ display: 'block', textAlign: 'center', color: '#aaa', marginTop: '40px' }}>
          暂无订单
        </Text>
      )}

      {list.map((o) => (
        <View
          key={o.id}
          onClick={() => setDetail(o)}
          style={{
            background: '#fff',
            borderRadius: '12px',
            padding: '14px',
            marginBottom: '10px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
          }}
        >
          <Text style={{ display: 'block', fontSize: '15px' }}>订单号：{o.order_no}</Text>
          <Text style={{ display: 'block', color: '#8C8C8C', fontSize: '12px', marginTop: '4px' }}>
            类型：{o.type === 'rx' ? '处方药' : '非处方'} · ¥{o.amount}
          </Text>
          <Text style={{ color: PAY_COLOR[o.pay_status] || '#888', fontSize: '13px', marginTop: '6px', display: 'block' }}>
            {PAY_LABEL[o.pay_status] || o.pay_status}
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
            <Text style={{ display: 'block', fontSize: '17px', fontWeight: 600, marginBottom: '12px' }}>订单详情</Text>
            <Text style={{ display: 'block', fontSize: '14px' }}>订单号：{detail.order_no}</Text>
            <Text style={{ display: 'block', fontSize: '14px', marginTop: '6px' }}>类型：{detail.type === 'rx' ? '处方药（凭方购买）' : '非处方药'}</Text>
            <Text style={{ display: 'block', fontSize: '14px', marginTop: '6px' }}>金额：¥{detail.amount}</Text>
            <Text style={{ display: 'block', fontSize: '14px', marginTop: '6px', color: PAY_COLOR[detail.pay_status] }}>
              状态：{PAY_LABEL[detail.pay_status] || detail.pay_status}
            </Text>
            {detail.pay_status === 'unpaid' && (
              <Button type='primary' style={{ background: '#1677FF', marginTop: '16px' }} onClick={() => handlePay(detail)}>
                立即支付
              </Button>
            )}
          </View>
        </View>
      )}
    </View>
  )
}
