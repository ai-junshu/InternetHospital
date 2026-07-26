import { useEffect, useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ProCard,
  StatisticCard,
  ActionType,
} from '@ant-design/pro-components'
import { Tag, Space, message, Typography } from 'antd'
import type { ProColumns } from '@ant-design/pro-components'
import {
  listDoctors,
  listPrescriptions,
  listConsultations,
  listOrders,
  auditPrescription,
  type Prescription,
} from '@/services/ih'

const rxColor: Record<string, string> = {
  approved: 'green',
  rejected: 'red',
  pending: 'gold',
}

export default function IhSupervision() {
  const [stats, setStats] = useState({ doctors: 0, consults: 0, rx: 0, paid: 0 })
  useEffect(() => {
    ;(async () => {
      const [d, c, rx, o] = await Promise.all([
        listDoctors({ status: 'active', page: 1, page_size: 1 }),
        listConsultations({ page: 1, page_size: 1 }),
        listPrescriptions({ page: 1, page_size: 1 }),
        listOrders({ pay_status: 'paid', page: 1, page_size: 1 }),
      ])
      setStats({ doctors: d.total, consults: c.total, rx: rx.total, paid: o.total })
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
        r.status === 'pending' ? (
          <Space>
            <a
              onClick={async () => {
                await auditPrescription(r.id, { action: 'approve', reviewer_id: 1 })
                actionRef.current?.reload()
                message.success('已审核通过')
              }}
            >
              通过
            </a>
            <a
              onClick={async () => {
                await auditPrescription(r.id, { action: 'reject', reviewer_id: 1, note: '不合规' })
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
        <StatisticCard statistic={{ title: '累计问诊', value: stats.consults }} />
        <StatisticCard statistic={{ title: '累计处方', value: stats.rx }} />
        <StatisticCard statistic={{ title: '已支付订单', value: stats.paid }} />
      </ProCard>
      <ProCard title="异常预警 · 处方审核与合理用药（平台监管视角）" style={{ marginTop: 16 }}>
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
      <ProCard style={{ marginTop: 16 }}>
        <Typography.Paragraph type="secondary">
          合规要求（等保三级 / 互联网医院监管）：全部在线复诊、电子处方、药品销售数据需留痕并可向监管平台报送；
          处方须经药师审核且合理用药引擎校验通过后流转。本页为监管总览，明细经 <code>/api/v1/ih/*</code> 实时拉取。
        </Typography.Paragraph>
      </ProCard>
    </PageContainer>
  )
}
