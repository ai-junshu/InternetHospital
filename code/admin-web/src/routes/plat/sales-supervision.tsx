import { useEffect, useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ProCard,
  StatisticCard,
  ActionType,
} from '@ant-design/pro-components'
import { Tag, Typography } from 'antd'
import type { ProColumns } from '@ant-design/pro-components'
import { listOrders, type Order } from '@/services/ih'

export default function SalesSupervision() {
  const [stats, setStats] = useState({ gmv: 0, orders: 0, rxOrders: 0, unpaid: 0 })
  useEffect(() => {
    ;(async () => {
      const res = await listOrders({ page: 1, page_size: 200 })
      const gmv = res.items.reduce((s, o) => s + (o.amount || 0), 0)
      const rxOrders = res.items.filter((o) => o.type === 'rx').length
      const unpaid = res.items.filter((o) => o.pay_status !== 'paid').length
      setStats({ gmv: gmv / 100, orders: res.total, rxOrders, unpaid })
    })().catch(() => {})
  }, [])

  const actionRef = useRef<ActionType>()
  const columns: ProColumns<Order>[] = [
    { title: '订单号', dataIndex: 'order_no', width: 170 },
    { title: '用户ID', dataIndex: 'user_id', width: 90 },
    {
      title: '类型',
      dataIndex: 'type',
      width: 90,
      render: (_, r) => <Tag color={r.type === 'rx' ? 'blue' : 'default'}>{r.type}</Tag>,
    },
    {
      title: '金额(元)',
      dataIndex: 'amount',
      width: 110,
      render: (_, r) => ((r.amount || 0) / 100).toFixed(2),
    },
    {
      title: '支付状态',
      dataIndex: 'pay_status',
      width: 100,
      render: (_, r) => <Tag color={r.pay_status === 'paid' ? 'green' : 'gold'}>{r.pay_status}</Tag>,
    },
    { title: '创建时间', dataIndex: 'created_at', width: 170 },
  ]

  return (
    <PageContainer>
      <ProCard gutter={16} wrap>
        <StatisticCard statistic={{ title: 'GMV(元)', value: stats.gmv.toFixed(2) }} />
        <StatisticCard statistic={{ title: '订单总数', value: stats.orders }} />
        <StatisticCard statistic={{ title: '处方订单数', value: stats.rxOrders }} />
        <StatisticCard statistic={{ title: '未支付/异常', value: stats.unpaid }} />
      </ProCard>
      <ProCard title="销售明细（合规：处方订单须关联有效电子处方）" style={{ marginTop: 16 }}>
        <ProTable<Order>
          rowKey="id"
          actionRef={actionRef}
          columns={columns}
          search={false}
          pagination={{ pageSize: 10 }}
          request={async (params) => {
            const res = await listOrders({ page: params.current, page_size: params.pageSize })
            return { data: res.items, total: res.total, success: true }
          }}
        />
      </ProCard>
      <ProCard style={{ marginTop: 16 }}>
        <Typography.Paragraph type="secondary">
          合规要求（等保三级 / 产品销售监管）：处方药销售须与电子处方一一对应并可追溯；
          异常订单（大额、高频、处方缺失）须触发预警并留痕。本页数据经 <code>/api/v1/ih/orders</code> 实时拉取。
        </Typography.Paragraph>
      </ProCard>
    </PageContainer>
  )
}
