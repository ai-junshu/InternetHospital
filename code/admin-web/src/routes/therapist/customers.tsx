import { useRef, useState } from 'react'
import { PageContainer, ProTable, ActionType } from '@ant-design/pro-components'
import { Tag, Drawer, Descriptions, message } from 'antd'
import type { ProColumns } from '@ant-design/pro-components'
import { listCustomers, authorizeCustomer, type Customer } from '@/services/mt'

type CustRow = Customer & { created_at?: string }

const authColor: Record<string, string> = {
  authorized: 'green',
  unauthorized: 'gold',
  pending: 'gold',
}

export default function TherapistCustomers() {
  const actionRef = useRef<ActionType>()
  const [current, setCurrent] = useState<CustRow | null>(null)

  const columns: ProColumns<CustRow>[] = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '姓名(脱敏)', dataIndex: 'name_mask', width: 120 },
    { title: '性别', dataIndex: 'gender', width: 80 },
    { title: '电话(脱敏)', dataIndex: 'phone_mask', width: 140 },
    { title: '来源门店', dataIndex: 'source_store_id', width: 100 },
    {
      title: '授权状态',
      dataIndex: 'auth_status',
      width: 100,
      render: (_, r) => <Tag color={authColor[r.auth_status]}>{r.auth_status}</Tag>,
    },
    { title: '创建时间', dataIndex: 'created_at', width: 170 },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, r) => [
        <a
          key="auth"
          onClick={async () => {
            await authorizeCustomer(r.id)
            actionRef.current?.reload()
            message.success('已发起授权')
          }}
        >
          授权
        </a>,
        <a key="view" onClick={() => setCurrent(r)}>
          详情
        </a>,
      ],
    },
  ]

  return (
    <PageContainer>
      <ProTable<CustRow>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        pagination={{ pageSize: 10 }}
        request={async (params) => {
          const res = await listCustomers({ page: params.current, page_size: params.pageSize })
          return { data: res.items as CustRow[], total: res.total, success: true }
        }}
      />
      <Drawer title="客户详情" width={420} open={!!current} onClose={() => setCurrent(null)}>
        {current && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="姓名(脱敏)">{current.name_mask || '—'}</Descriptions.Item>
            <Descriptions.Item label="性别">{current.gender || '—'}</Descriptions.Item>
            <Descriptions.Item label="电话(脱敏)">{current.phone_mask || '—'}</Descriptions.Item>
            <Descriptions.Item label="来源门店">{current.source_store_id ?? '—'}</Descriptions.Item>
            <Descriptions.Item label="授权状态">{current.auth_status}</Descriptions.Item>
            <Descriptions.Item label="健康标签">
              {JSON.stringify(current.health_tags ?? {})}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </PageContainer>
  )
}
