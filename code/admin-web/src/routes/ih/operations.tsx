import { useEffect, useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ProCard,
  StatisticCard,
  ActionType,
} from '@ant-design/pro-components'
import { Tag, Space, message } from 'antd'
import type { ProColumns } from '@ant-design/pro-components'
import {
  listPrescriptions,
  auditPrescription,
  getDashboards,
  type Prescription,
} from '@/services/ih'

const rxColor: Record<string, string> = {
  approved: 'green',
  rejected: 'red',
  pending_audit: 'gold',
}

export default function IhOperations() {
  const [stats, setStats] = useState({
    doctors: 0,
    pendingRx: 0,
    consults: 0,
    paidOrders: 0,
    passRate: 0,
    complaints: 0,
    lowStock: 0,
  })
  useEffect(() => {
    ;(async () => {
      const d = await getDashboards()
      setStats({
        doctors: d.core.active_doctors,
        pendingRx: d.core.pending_prescriptions,
        consults: d.core.total_consultations,
        paidOrders: d.core.paid_orders,
        passRate: d.compliance.prescription_pass_rate,
        complaints: d.compliance.complaint_total,
        lowStock: d.warning.low_stock_count,
      })
    })().catch(() => {})
  }, [])

  const actionRef = useRef<ActionType>()
  const columns: ProColumns<Prescription>[] = [
    { title: '处方号', dataIndex: 'prescription_no', width: 160 },
    { title: '医生ID', dataIndex: 'doctor_id', width: 90 },
    { title: '患者ID', dataIndex: 'patient_id', width: 90 },
    { title: '诊断', dataIndex: 'diagnose', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (_, r) => <Tag color={rxColor[r.status]}>{r.status}</Tag>,
    },
    {
      title: '合理用药告警',
      dataIndex: 'rx_check_json',
      width: 130,
      render: (_, r) => {
        const c = r.rx_check_json as { warnings?: unknown[]; risk_level?: string } | undefined
        if (c && (Array.isArray(c.warnings) ? c.warnings.length : c.risk_level)) {
          return <Tag color="red">有告警</Tag>
        }
        return <Tag color="green">无</Tag>
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 140,
      render: (_, r) =>
        r.status === 'pending_audit' ? (
          <Space>
            <a
              onClick={async () => {
                await auditPrescription(r.id, { action: 'approve', reviewer_id: Number(localStorage.getItem('uid') || 1) })
                actionRef.current?.reload()
                message.success('已审核通过')
              }}
            >
              通过
            </a>
            <a
              onClick={async () => {
                await auditPrescription(r.id, { action: 'reject', reviewer_id: Number(localStorage.getItem('uid') || 1), note: '不合规' })
                actionRef.current?.reload()
                message.success('已驳回')
              }}
            >
              驳回
            </a>
          </Space>
        ) : (
          <span>—</span>
        ),
    },
  ]

  return (
    <PageContainer>
      <ProCard gutter={16} wrap>
        <StatisticCard statistic={{ title: '在线医师数', value: stats.doctors }} />
        <StatisticCard statistic={{ title: '待审处方', value: stats.pendingRx }} />
        <StatisticCard statistic={{ title: '累计问诊', value: stats.consults }} />
        <StatisticCard statistic={{ title: '已支付订单', value: stats.paidOrders }} />
        <StatisticCard statistic={{ title: '审方通过率', value: `${(stats.passRate * 100).toFixed(1)}%` }} />
        <StatisticCard statistic={{ title: '累计投诉', value: stats.complaints }} />
        <StatisticCard statistic={{ title: '低库存预警', value: stats.lowStock }} />
      </ProCard>
      <ProCard title="异常预警 · 处方审核与合理用药" style={{ marginTop: 16 }}>
        <ProTable<Prescription>
          rowKey="id"
          actionRef={actionRef}
          columns={columns}
          search={false}
          pagination={{ pageSize: 10 }}
          request={async (params) => {
            const res = await listPrescriptions({ page: params.current, page_size: params.pageSize })
            return { data: res.items, total: res.total, success: true }
          }}
        />
      </ProCard>
    </PageContainer>
  )
}
