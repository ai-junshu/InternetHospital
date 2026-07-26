import { useRef } from 'react'
import { PageContainer, ProTable } from '@ant-design/pro-components'
import { Tag } from 'antd'
import type { ActionType, ProColumns } from '@ant-design/pro-components'
import { listAiModels, type AiModel } from '@/services/plat'

const STATUS_COLOR: Record<string, string> = {
  online: 'green',
  offline: 'default',
}

function fmtMetrics(m?: Record<string, unknown>) {
  if (!m) return '-'
  return Object.entries(m)
    .map(([k, v]) => `${k}=${(typeof v === 'number' ? v : String(v))}`)
    .join(' / ')
}

export default function AiModelsAdmin() {
  const actionRef = useRef<ActionType>()

  const columns: ProColumns<AiModel>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    { title: '模型名称', dataIndex: 'name' },
    { title: '版本', dataIndex: 'version', width: 100, search: false },
    { title: '算法类型', dataIndex: 'algo_type', width: 140 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        online: { text: '在线', status: 'Success' },
        offline: { text: '离线', status: 'Default' },
      },
      render: (_, r) => (
        <Tag color={STATUS_COLOR[r.status] ?? 'default'}>{r.status}</Tag>
      ),
    },
    {
      title: '指标摘要',
      dataIndex: 'metrics_json',
      search: false,
      render: (_, r) => fmtMetrics(r.metrics_json),
    },
    { title: '上线时间', dataIndex: 'online_at', width: 180, search: false },
  ]

  return (
    <PageContainer title="AI 模型目录（plat · 第11.2/12.3章）">
      <ProTable<AiModel>
        rowKey="id"
        headerTitle="模型版本与效果指标"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        request={async (params) => {
          const res = await listAiModels({
            page: params.current,
            page_size: params.pageSize,
            name: params.name as string | undefined,
            status: params.status as string | undefined,
            algo_type: params.algo_type as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
    </PageContainer>
  )
}
