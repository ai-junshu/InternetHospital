import { useEffect, useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ProCard,
  StatisticCard,
  ActionType,
} from '@ant-design/pro-components'
import { Tag } from 'antd'
import type { ProColumns } from '@ant-design/pro-components'
import { listRepurchase, type RepurchasePrediction } from '@/services/mt'

const riskColor: Record<string, string> = {
  high: 'red',
  medium: 'gold',
  low: 'green',
}

export default function TherapistAdherence() {
  const [stats, setStats] = useState({ high: 0, medium: 0, low: 0 })
  useEffect(() => {
    ;(async () => {
      const res = await listRepurchase({ page: 1, page_size: 200 })
      const cnt: Record<'high' | 'medium' | 'low', number> = { high: 0, medium: 0, low: 0 }
      res.items.forEach((r) => {
        const k = (r.risk_level || 'low') as 'high' | 'medium' | 'low'
        cnt[k] += 1
      })
      setStats(cnt)
    })().catch(() => {})
  }, [])

  const actionRef = useRef<ActionType>()
  const columns: ProColumns<RepurchasePrediction>[] = [
    { title: '客户ID', dataIndex: 'customer_id', width: 100 },
    {
      title: '下次到店概率',
      dataIndex: 'next_visit_prob',
      width: 130,
      render: (_, r) =>
        r.next_visit_prob != null ? `${(r.next_visit_prob * 100).toFixed(1)}%` : '—',
    },
    {
      title: '复购概率',
      dataIndex: 'repurchase_prob',
      width: 120,
      render: (_, r) =>
        r.repurchase_prob != null ? `${(r.repurchase_prob * 100).toFixed(1)}%` : '—',
    },
    {
      title: '依从性分层',
      dataIndex: 'risk_level',
      width: 110,
      render: (_, r) => <Tag color={riskColor[r.risk_level || 'low']}>{r.risk_level || 'low'}</Tag>,
    },
    { title: '模型版本', dataIndex: 'model_version', width: 120 },
  ]

  return (
    <PageContainer>
      <ProCard gutter={16} wrap>
        <StatisticCard statistic={{ title: '高流失风险(低依从)', value: stats.high, suffix: '人' }} />
        <StatisticCard statistic={{ title: '中风险', value: stats.medium, suffix: '人' }} />
        <StatisticCard statistic={{ title: '低风险(高依从)', value: stats.low, suffix: '人' }} />
      </ProCard>
      <ProCard title="客户依从性分层（基于复购预测 AI）" style={{ marginTop: 16 }}>
        <ProTable<RepurchasePrediction>
          rowKey="id"
          actionRef={actionRef}
          columns={columns}
          search={false}
          pagination={{ pageSize: 10 }}
          request={async (params) => {
            const res = await listRepurchase({ page: params.current, page_size: params.pageSize })
            return { data: res.items, total: res.total, success: true }
          }}
        />
      </ProCard>
    </PageContainer>
  )
}
