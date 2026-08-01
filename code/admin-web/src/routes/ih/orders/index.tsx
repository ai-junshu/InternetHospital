import { useRef } from 'react'
import { PageContainer, ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components'
import { Button, Tag, App, Popconfirm } from 'antd'
import { listOrders, payOrder, type Order } from '@/services/ih'

const PAY_ENUM = {
  unpaid: { text: '待支付', status: 'Warning' },
  paying: { text: '支付中', status: 'Processing' },
  paid: { text: '已支付', status: 'Success' },
  closed: { text: '已关闭', status: 'Default' },
}

export default function OrderAdmin() {
  const actionRef = useRef<ActionType>()
  const { message } = App.useApp()

  const pay = async (r: Order) => {
    try {
      await payOrder(r.id)
      message.success('已发起支付（mock，待商户号）')
      actionRef.current?.reload()
    } catch {}
  }

  const columns: ProColumns<Order>[] = [
    { title: '订单号', dataIndex: 'order_no', width: 180, search: false },
    { title: '用户ID', dataIndex: 'user_id', width: 90 },
    { title: '类型', dataIndex: 'type', width: 100 },
    {
      title: '关联处方',
      dataIndex: 'prescription_id',
      width: 120,
      search: false,
      render: (_, r) => (r.prescription_id ? `Rx#${r.prescription_id}` : '-'),
    },
    {
      title: '金额',
      dataIndex: 'amount',
      width: 100,
      search: false,
      render: (_, r) => `￥${((r.amount || 0) / 100).toFixed(2)}`,
    },
    {
      title: '支付状态',
      dataIndex: 'pay_status',
      width: 110,
      valueType: 'select',
      valueEnum: PAY_ENUM,
      render: (_, r) => (
        <Tag color={r.pay_status === 'paid' ? 'green' : r.pay_status === 'unpaid' ? 'gold' : 'default'}>
          {PAY_ENUM[r.pay_status as keyof typeof PAY_ENUM]?.text || r.pay_status}
        </Tag>
      ),
    },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) =>
        r.pay_status !== 'paid' ? [
          <Popconfirm key="pay" title="发起支付（mock）?" onConfirm={() => pay(r)}>
            <a>发起支付</a>
          </Popconfirm>,
        ] : [],
    },
  ]

  return (
    <PageContainer title="订单管理（ih）">
      <ProTable<Order>
        rowKey="id"
        headerTitle="订单列表"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const res = await listOrders({
            page: params.current,
            page_size: params.pageSize,
            user_id: params.user_id as number | undefined,
            pay_status: params.pay_status as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
    </PageContainer>
  )
}
