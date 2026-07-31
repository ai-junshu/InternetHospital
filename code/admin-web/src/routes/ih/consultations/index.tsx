import { useRef } from 'react'
import { PageContainer, ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components'
import { Tag } from 'antd'
import { listConsultations, type Consultation } from '@/services/ih'

const STATUS_ENUM = {
  created: { text: '已创建', status: 'Default' },
  ongoing: { text: '进行中', status: 'Processing' },
  ended: { text: '已结束', status: 'Success' },
}

export default function ConsultationAdmin() {
  const actionRef = useRef<ActionType>()

  const columns: ProColumns<Consultation>[] = [
    { title: '会话号', dataIndex: 'consultation_no', width: 180, search: false },
    { title: '患者ID', dataIndex: 'patient_id', width: 90 },
    { title: '医生ID', dataIndex: 'doctor_id', width: 90 },
    { title: '主诉', dataIndex: 'chief_complaint', search: false, ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      valueType: 'select',
      valueEnum: STATUS_ENUM,
      render: (_, r) => (
        <Tag color={r.status === 'ongoing' ? 'blue' : r.status === 'ended' ? 'green' : 'default'}>
          {STATUS_ENUM[r.status as keyof typeof STATUS_ENUM]?.text || r.status}
        </Tag>
      ),
    },
    {
      title: '时间',
      dataIndex: 'started_at',
      width: 180,
      search: false,
      render: (_, r) => (r.started_at ? new Date(r.started_at).toLocaleString() : '-'),
    },
  ]

  return (
    <PageContainer title="问诊会话监管（ih）">
      <ProTable<Consultation>
        rowKey="id"
        headerTitle="问诊会话列表"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const res = await listConsultations({
            page: params.current,
            page_size: params.pageSize,
            status: params.status as string | undefined,
            patient_id: params.patient_id as number | undefined,
            doctor_id: params.doctor_id as number | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
    </PageContainer>
  )
}
