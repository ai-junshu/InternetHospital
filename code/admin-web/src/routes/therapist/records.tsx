import { useRef } from 'react'
import { PageContainer, ProTable, ActionType } from '@ant-design/pro-components'
import type { ProColumns } from '@ant-design/pro-components'
import { listTreatmentRecords, type TreatmentRecord } from '@/services/mt'

export default function TherapistRecords() {
  const actionRef = useRef<ActionType>()
  const columns: ProColumns<TreatmentRecord>[] = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '客户ID', dataIndex: 'customer_id', width: 90 },
    { title: '门店ID', dataIndex: 'store_id', width: 90 },
    { title: '调理师ID', dataIndex: 'therapist_id', width: 100 },
    { title: '方案ID', dataIndex: 'plan_id', width: 90 },
    { title: '服务时间', dataIndex: 'service_time', width: 170 },
    { title: 'NPS', dataIndex: 'nps', width: 80 },
    { title: '创建时间', dataIndex: 'created_at', width: 170 },
  ]

  return (
    <PageContainer>
      <ProTable<TreatmentRecord>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        pagination={{ pageSize: 10 }}
        toolBarRender={() => []}
        request={async (params) => {
          const res = await listTreatmentRecords({ page: params.current, page_size: params.pageSize })
          return { data: res.items, total: res.total, success: true }
        }}
      />
    </PageContainer>
  )
}
