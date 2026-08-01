import { useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormTextArea,
  ProFormSelect,
} from '@ant-design/pro-components'
import { Button, Tag, Drawer, Descriptions, message, App } from 'antd'
import type { ActionType, ProColumns } from '@ant-design/pro-components'
import { listComplaints, handleComplaint, type Complaint } from '@/services/ih'

const STATUS_COLOR: Record<string, string> = {
  pending: 'gold',
  processing: 'blue',
  resolved: 'green',
  closed: 'default',
}
const STATUS_LABEL: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  closed: '已关闭',
}
const TYPE_LABEL: Record<string, string> = {
  quality: '质量',
  service: '服务',
  refund: '退款',
}

export default function ComplaintAdmin() {
  const actionRef = useRef<ActionType>()
  const { message: msg } = App.useApp()
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState<Complaint | null>(null)

  const openDetail = (r: Complaint) => {
    setDetail(r)
    setOpen(true)
  }

  const columns: ProColumns<Complaint>[] = [
    { title: 'ID', dataIndex: 'id', width: 72, search: false },
    { title: '关联订单', dataIndex: 'order_id', width: 100, search: false },
    {
      title: '类型',
      dataIndex: 'type',
      width: 90,
      valueType: 'select',
      valueEnum: Object.fromEntries(Object.entries(TYPE_LABEL).map(([k, v]) => [k, { text: v }])),
      render: (_, r) => TYPE_LABEL[r.type] || r.type,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: Object.fromEntries(Object.entries(STATUS_LABEL).map(([k, v]) => [k, { text: v }])),
      render: (_, r) => <Tag color={STATUS_COLOR[r.status]}>{STATUS_LABEL[r.status] || r.status}</Tag>,
    },
    { title: '投诉内容', dataIndex: 'content', ellipsis: true, search: false },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) => [
        <a key="view" onClick={() => openDetail(r)}>
          处理
        </a>,
      ],
    },
  ]

  return (
    <PageContainer title="投诉与售后（ih）">
      <ProTable<Complaint>
        rowKey="id"
        headerTitle="投诉列表"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const res = await listComplaints({
            page: params.current,
            page_size: params.pageSize,
            status: params.status as string | undefined,
            type: params.type as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
      <Drawer title="投诉处理" open={open} onClose={() => setOpen(false)} width={480}>
        {detail && (
          <>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="ID">{detail.id}</Descriptions.Item>
              <Descriptions.Item label="关联订单">{detail.order_id ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="类型">{TYPE_LABEL[detail.type] || detail.type}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_COLOR[detail.status]}>{STATUS_LABEL[detail.status] || detail.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="投诉内容">{detail.content}</Descriptions.Item>
              <Descriptions.Item label="处理回复">{detail.reply || '尚未处理'}</Descriptions.Item>
            </Descriptions>
            <ModalForm<{ status: string; reply: string }>
              title="处理投诉"
              trigger={<Button type="primary" style={{ marginTop: 16 }}>提交处理</Button>}
              initialValues={{ status: detail.status === 'pending' ? 'processing' : detail.status }}
              onFinish={async (v) => {
                try {
                  await handleComplaint(detail.id, { status: v.status, reply: v.reply })
                  msg.success('已更新')
                  setOpen(false)
                  actionRef.current?.reload()
                  return true
                } catch (e: any) {
                  msg.error(e?.response?.data?.message || '处理失败')
                  return false
                }
              }}
            >
              <ProFormSelect
                name="status"
                label="状态"
                options={Object.entries(STATUS_LABEL).map(([k, v]) => ({ value: k, label: v }))}
                rules={[{ required: true }]}
              />
              <ProFormTextArea name="reply" label="处理回复" placeholder="请填写处理结果与回复内容" />
            </ModalForm>
          </>
        )}
      </Drawer>
    </PageContainer>
  )
}
