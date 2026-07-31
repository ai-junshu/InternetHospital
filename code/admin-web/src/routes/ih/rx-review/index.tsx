import { useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  DrawerForm,
  ProFormTextArea,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { Button, Tag, App, Descriptions, Alert, Space } from 'antd'
import { listPrescriptions, auditPrescription, type Prescription } from '@/services/ih'

const RX_COLOR: Record<string, string> = {
  approved: 'green',
  rejected: 'red',
  pending_audit: 'gold',
}

export default function RxReview() {
  const actionRef = useRef<ActionType>()
  const { message } = App.useApp()
  const [detail, setDetail] = useState<Prescription | null>(null)
  const [open, setOpen] = useState(false)
  const currentUid = Number(localStorage.getItem('uid') || 1)

  const openReview = (r: Prescription) => {
    setDetail(r)
    setOpen(true)
  }

  const doAudit = async (action: 'approve' | 'reject', note?: string) => {
    if (!detail) return
    try {
      await auditPrescription(detail.id, { action, reviewer_id: currentUid, note })
      message.success(action === 'approve' ? '已通过' : '已驳回')
      setOpen(false)
      setDetail(null)
      actionRef.current?.reload()
    } catch {}
  }

  const columns: ProColumns<Prescription>[] = [
    { title: '处方号', dataIndex: 'prescription_no', width: 180, search: false },
    { title: '患者ID', dataIndex: 'patient_id', width: 90 },
    { title: '医生ID', dataIndex: 'doctor_id', width: 90 },
    { title: '诊断', dataIndex: 'diagnose', search: false, ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      valueType: 'select',
      valueEnum: { pending_audit: { text: '待审', status: 'Warning' }, approved: { text: '通过', status: 'Success' }, rejected: { text: '驳回', status: 'Error' } },
      render: (_, r) => <Tag color={RX_COLOR[r.status] || 'default'}>{r.status}</Tag>,
    },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) =>
        r.status === 'pending_audit' ? [
          <a key="review" onClick={() => openReview(r)}>
            审核
          </a>,
        ] : [],
    },
  ]

  return (
    <PageContainer title="处方审核工作台（ih）">
      <ProTable<Prescription>
        rowKey="id"
        headerTitle="待审/历史处方"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const res = await listPrescriptions({
            page: params.current,
            page_size: params.pageSize,
            status: params.status as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
      <DrawerForm
        title="处方审核"
        open={open}
        onOpenChange={setOpen}
        drawerProps={{ width: 520 }}
        submitter={{
          render: () => [
            <Space key="op">
              <Button danger onClick={() => doAudit('reject', '不合规')}>
                驳回
              </Button>
              <Button type="primary" onClick={() => doAudit('approve')}>
                通过
              </Button>
            </Space>,
          ],
        }}
      >
        {detail && (
          <>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="处方号">{detail.prescription_no}</Descriptions.Item>
              <Descriptions.Item label="患者ID">{detail.patient_id}</Descriptions.Item>
              <Descriptions.Item label="医生ID">{detail.doctor_id}</Descriptions.Item>
              <Descriptions.Item label="诊断">{detail.diagnose || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={RX_COLOR[detail.status] || 'default'}>{detail.status}</Tag>
              </Descriptions.Item>
            </Descriptions>
            {detail.rx_check_json?.hit ? (
              <Alert
                style={{ marginTop: 16 }}
                type="warning"
                showIcon
                message="合理用药校验告警"
                description={
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(detail.rx_check_json, null, 2)}
                  </pre>
                }
              />
            ) : (
              <Alert style={{ marginTop: 16 }} type="success" showIcon message="合理用药校验通过" />
            )}
            <ProFormTextArea name="note" label="审核意见" placeholder="驳回时必填" style={{ marginTop: 16 }} />
          </>
        )}
      </DrawerForm>
    </PageContainer>
  )
}
