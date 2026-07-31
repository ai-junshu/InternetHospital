import { useRef } from 'react'
import { PageContainer, ProTable } from '@ant-design/pro-components'
import { Tag, Button, App, Popconfirm } from 'antd'
import type { ActionType, ProColumns } from '@ant-design/pro-components'
import { listAiModels, setModelOnline, setModelOffline, deleteModel, type AiModel } from '@/services/plat'

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
  const { message } = App.useApp()
  const role = localStorage.getItem('role')
  const canEdit = role === 'platform'

  const toggle = async (r: AiModel) => {
    try {
      if (r.status === 'online') await setModelOffline(r.id)
      else await setModelOnline(r.id)
      message.success('已更新')
      actionRef.current?.reload()
    } catch {}
  }
  const remove = async (r: AiModel) => {
    try {
      await deleteModel(r.id)
      message.success('已删除')
      actionRef.current?.reload()
    } catch {}
  }

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
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) =>
        canEdit
          ? [
              <a key="toggle" onClick={() => toggle(r)}>
                {r.status === 'online' ? '下线' : '上线'}
              </a>,
              <Popconfirm key="del" title="确认删除该模型?" onConfirm={() => remove(r)}>
                <a>删除</a>
              </Popconfirm>,
            ]
          : [],
    },
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
