import { useRef } from 'react'
import { PageContainer, ProTable } from '@ant-design/pro-components'
import { Tag, Progress } from 'antd'
import type { ActionType, ProColumns } from '@ant-design/pro-components'
import { listDataAssets, type DataAsset } from '@/services/plat'

const SENS_COLOR: Record<string, string> = {
  L1: 'blue',
  L2: 'cyan',
  L3: 'orange',
  L4: 'red',
}

export default function DataAssetsAdmin() {
  const actionRef = useRef<ActionType>()

  const columns: ProColumns<DataAsset>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    { title: '资产名称', dataIndex: 'name' },
    { title: '归属方', dataIndex: 'owner', width: 140 },
    {
      title: '敏感等级',
      dataIndex: 'sensitivity_level',
      width: 110,
      valueEnum: {
        L1: { text: 'L1' },
        L2: { text: 'L2' },
        L3: { text: 'L3' },
        L4: { text: 'L4' },
      },
      render: (_, r) => (
        <Tag color={SENS_COLOR[r.sensitivity_level ?? 'L1'] ?? 'blue'}>
          {r.sensitivity_level ?? '-'}
        </Tag>
      ),
    },
    {
      title: '质量评分',
      dataIndex: 'quality_score',
      width: 140,
      search: false,
      render: (_, r) =>
        r.quality_score == null ? (
          '-'
        ) : (
          <Progress percent={Math.round(r.quality_score * 100)} size="small" />
        ),
    },
    { title: '更新频率', dataIndex: 'update_freq', width: 100, search: false },
    {
      title: '用途范围',
      dataIndex: 'usage_scope',
      search: false,
      ellipsis: true,
    },
  ]

  return (
    <PageContainer title="数据资产目录（plat · 第11.2/13章）">
      <ProTable<DataAsset>
        rowKey="id"
        headerTitle="资产分级（L1-L4）与血缘"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        request={async (params) => {
          const res = await listDataAssets({
            page: params.current,
            page_size: params.pageSize,
            name: params.name as string | undefined,
            owner: params.owner as string | undefined,
            sensitivity_level: params.sensitivity_level as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
    </PageContainer>
  )
}
