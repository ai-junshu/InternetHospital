import { useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormSelect,
  ProFormTextArea,
  ProFormDigit,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { Button, Tag, App } from 'antd'
import {
  listCompliance,
  submitCompliance,
  approveCompliance,
  rejectCompliance,
  type ComplianceItem,
} from '@/services/plat'

const STATUS_ENUM = {
  pending: { text: '待审核', status: 'Processing' },
  approved: { text: '已通过', status: 'Success' },
  rejected: { text: '已驳回', status: 'Error' },
}

const CATEGORIES = [
  { label: '执业许可', value: '执业许可' },
  { label: '等保测评', value: '等保测评' },
  { label: '数据合规', value: '数据合规' },
  { label: '隐私政策', value: '隐私政策' },
]
const SUBJECT_TYPES = [
  { label: '执业医师', value: 'doctor' },
  { label: '调理师', value: 'therapist' },
  { label: '门店', value: 'store' },
  { label: '医院', value: 'hospital' },
  { label: '平台', value: 'platform' },
]

export default function ComplianceReview() {
  const actionRef = useRef<ActionType>()
  const { message } = App.useApp()
  const role = localStorage.getItem('role')
  const canReview = role === 'platform' || role === 'xingyao'
  const [submitOpen, setSubmitOpen] = useState(false)
  const [rejectId, setRejectId] = useState<number | null>(null)

  const columns: ProColumns<ComplianceItem>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '类别',
      dataIndex: 'category',
      width: 120,
      valueType: 'select',
      fieldProps: { options: CATEGORIES },
    },
    {
      title: '主体类型',
      dataIndex: 'subject_type',
      width: 120,
      valueType: 'select',
      fieldProps: { options: SUBJECT_TYPES },
    },
    { title: '主体ID', dataIndex: 'subject_id', width: 90, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      valueEnum: STATUS_ENUM,
      render: (_, r) => (
        <Tag color={r.status === 'approved' ? 'green' : r.status === 'rejected' ? 'red' : 'blue'}>
          {STATUS_ENUM[r.status as keyof typeof STATUS_ENUM]?.text || r.status}
        </Tag>
      ),
    },
    { title: '提交人', dataIndex: 'submitter_id', width: 90, search: false },
    { title: '审核人', dataIndex: 'reviewer_id', width: 90, search: false },
    { title: '审核意见', dataIndex: 'review_note', width: 160, search: false, ellipsis: true },
    { title: '提交时间', dataIndex: 'created_at', width: 170, search: false },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) =>
        canReview && r.status === 'pending'
          ? [
              <a
                key="ok"
                onClick={async () => {
                  try {
                    await approveCompliance(r.id)
                    message.success('已通过')
                    actionRef.current?.reload()
                  } catch {}
                }}
              >
                通过
              </a>,
              <a key="no" onClick={() => setRejectId(r.id)}>
                驳回
              </a>,
            ]
          : [],
    },
  ]

  return (
    <PageContainer title="合规采集审核（plat · 第3.6.2章）">
      <ProTable<ComplianceItem>
        rowKey="id"
        headerTitle="合规工单"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="submit" type="primary" onClick={() => setSubmitOpen(true)}>
            提交工单
          </Button>,
        ]}
        request={async (params) => {
          const res = await listCompliance({
            page: params.current,
            page_size: params.pageSize,
            category: params.category as string | undefined,
            status: params.status as string | undefined,
            subject_type: params.subject_type as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
      <ModalForm
        title="提交合规工单"
        open={submitOpen}
        onOpenChange={setSubmitOpen}
        width={520}
        onFinish={async (v: {
          category: string
          subject_type: string
          subject_id?: number
          title: string
          content_json?: string
        }) => {
          let content_json: Record<string, unknown> | undefined
          if (v.content_json) {
            try {
              content_json = JSON.parse(v.content_json)
            } catch {
              message.error('内容(JSON) 格式不正确')
              return false
            }
          }
          try {
            await submitCompliance({
              category: v.category,
              subject_type: v.subject_type,
              subject_id: v.subject_id,
              title: v.title,
              content_json,
            })
            message.success('工单已提交')
            actionRef.current?.reload()
            return true
          } catch {
            return false
          }
        }}
      >
        <ProFormSelect name="category" label="类别" options={CATEGORIES} rules={[{ required: true }]} />
        <ProFormSelect
          name="subject_type"
          label="主体类型"
          options={SUBJECT_TYPES}
          rules={[{ required: true }]}
        />
        <ProFormDigit name="subject_id" label="主体ID" />
        <ProFormText name="title" label="标题" rules={[{ required: true }]} />
        <ProFormTextArea name="content_json" label="内容(JSON)" extra="合规材料内容，JSON 格式字符串" />
      </ModalForm>
      <ModalForm
        title="驳回工单"
        open={rejectId != null}
        initialValues={{ review_note: '' }}
        onOpenChange={(o) => {
          if (!o) setRejectId(null)
        }}
        width={480}
        onFinish={async (v: { review_note: string }) => {
          if (!rejectId) return false
          if (!v.review_note?.trim()) {
            message.error('驳回必须填写意见')
            return false
          }
          try {
            await rejectCompliance(rejectId, v.review_note)
            message.success('已驳回')
            setRejectId(null)
            actionRef.current?.reload()
            return true
          } catch {
            return false
          }
        }}
      >
        <ProFormTextArea
          name="review_note"
          label="驳回意见"
          rules={[{ required: true, message: '请填写驳回意见' }]}
        />
      </ModalForm>
    </PageContainer>
  )
}
