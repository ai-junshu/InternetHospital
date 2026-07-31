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
    { title: '昵称', dataIndex: 'nickname' },
    { title: '手机号', dataIndex: 'phone', search: false },
    { title: '性别', dataIndex: 'gender', width: 80, search: false },
    { title: '年龄', dataIndex: 'age', width: 80, search: false },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      width: 180,
      search: false,
      render: (_, r) => (r.created_at ? new Date(r.created_at).toLocaleString() : '-'),
    },
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
            keyword: params.nickname as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
      <Drawer title="患者详情" open={open} onClose={() => setOpen(false)} width={420}>
        {detail && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{detail.id}</Descriptions.Item>
            <Descriptions.Item label="昵称">{detail.nickname || '-'}</Descriptions.Item>
            <Descriptions.Item label="手机号">{detail.phone || '-'}</Descriptions.Item>
            <Descriptions.Item label="性别">{detail.gender || '-'}</Descriptions.Item>
            <Descriptions.Item label="年龄">{detail.age ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={detail.is_deleted ? 'red' : 'green'}>
                {detail.is_deleted ? '已注销' : '正常'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="注册时间">
              {detail.created_at ? new Date(detail.created_at).toLocaleString() : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </PageContainer>
  )
}
