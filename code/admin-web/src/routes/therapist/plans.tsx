import { useRef, useState } from 'react'
import { PageContainer, ProTable, ActionType } from '@ant-design/pro-components'
import { Tag, Drawer, Typography } from 'antd'
import type { ProColumns } from '@ant-design/pro-components'
import { listCarePlans, type CarePlan } from '@/services/mt'

export default function TherapistPlans() {
  const actionRef = useRef<ActionType>()
  const [current, setCurrent] = useState<CarePlan | null>(null)

  const columns: ProColumns<CarePlan>[] = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '客户ID', dataIndex: 'customer_id', width: 90 },
    { title: '疼痛类型', dataIndex: 'pain_type', width: 120 },
    { title: '调理目标', dataIndex: 'goal', ellipsis: true },
    { title: '周期', dataIndex: 'cycle', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (_, r) => <Tag color={r.status === 'active' ? 'green' : 'default'}>{r.status}</Tag>,
    },
    { title: '创建时间', dataIndex: 'created_at', width: 170 },
    {
      title: '操作',
      valueType: 'option',
      width: 90,
      render: (_, r) => [<a key="view" onClick={() => setCurrent(r)}>查看</a>],
    },
  ]

  return (
    <PageContainer>
      <ProTable<CarePlan>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        pagination={{ pageSize: 10 }}
        toolBarRender={() => []}
        request={async (params) => {
          const res = await listCarePlans({ page: params.current, page_size: params.pageSize })
          return { data: res.items, total: res.total, success: true }
        }}
      />
      <Drawer title="调理方案详情" width={480} open={!!current} onClose={() => setCurrent(null)}>
        {current && (
          <Typography.Paragraph>
            <div>
              <b>调理目标：</b>
              {current.goal || '—'}
            </div>
            <div>
              <b>周期：</b>
              {current.cycle || '—'}
            </div>
            <div style={{ marginTop: 12 }}>
              <b>方案明细(JSON)：</b>
            </div>
            <Typography.Paragraph copyable>{JSON.stringify(current.items_json, null, 2)}</Typography.Paragraph>
            <div>
              <b>产品组合(JSON)：</b>
            </div>
            <Typography.Paragraph copyable>{JSON.stringify(current.product_combo_json, null, 2)}</Typography.Paragraph>
            <div>
              <b>复评节点(JSON)：</b>
            </div>
            <Typography.Paragraph copyable>{JSON.stringify(current.reeval_nodes, null, 2)}</Typography.Paragraph>
          </Typography.Paragraph>
        )}
      </Drawer>
    </PageContainer>
  )
}
