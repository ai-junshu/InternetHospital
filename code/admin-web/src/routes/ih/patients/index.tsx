import { useRef, useState } from 'react'
import { PageContainer, ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components'
import { Drawer, Descriptions, Tag } from 'antd'
import { listPatients, getPatient, type IhPatient } from '@/services/ih'

export default function PatientAdmin() {
  const actionRef = useRef<ActionType>()
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState<IhPatient | null>(null)

  const openDetail = async (id: number) => {
    const d = await getPatient(id).catch(() => null)
    setDetail(d)
    setOpen(true)
  }

  const columns: ProColumns<IhPatient>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    { title: '姓名(脱敏)', dataIndex: 'real_name_mask', search: false },
    { title: '手机号(脱敏)', dataIndex: 'phone_mask', search: false },
    { title: '身份证(脱敏)', dataIndex: 'id_card_mask', search: false },
    { title: '角色', dataIndex: 'role', width: 100, search: false },
    { title: '用户类型', dataIndex: 'user_type', width: 120, search: false },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) => [
        <a key="view" onClick={() => openDetail(r.id)}>
          详情
        </a>,
      ],
    },
  ]

  return (
    <PageContainer title="患者管理（ih）">
      <ProTable<IhPatient>
        rowKey="id"
        headerTitle="患者列表"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const res = await listPatients({
            page: params.current,
            page_size: params.pageSize,
            keyword: params.real_name_mask as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
      <Drawer title="患者详情" open={open} onClose={() => setOpen(false)} width={420}>
        {detail && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{detail.id}</Descriptions.Item>
            <Descriptions.Item label="姓名(脱敏)">{detail.real_name_mask || '-'}</Descriptions.Item>
            <Descriptions.Item label="手机号(脱敏)">{detail.phone_mask || '-'}</Descriptions.Item>
            <Descriptions.Item label="身份证(脱敏)">{detail.id_card_mask || '-'}</Descriptions.Item>
            <Descriptions.Item label="角色">
              <Tag color="blue">{detail.role || 'patient'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="用户类型">{detail.user_type || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </PageContainer>
  )
}
