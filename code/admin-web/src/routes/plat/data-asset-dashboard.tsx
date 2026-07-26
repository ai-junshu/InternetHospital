import { useEffect, useState } from 'react'
import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components'
import { Tabs, Typography } from 'antd'
import { listDataAssets, listAiModels } from '@/services/plat'
import DataAssetsAdmin from './data-assets'
import AiModelsAdmin from './ai-models'

export default function DataAssetDashboard() {
  const [stats, setStats] = useState({ assets: 0, models: 0, avgQuality: 0, sensitive: 0 })
  useEffect(() => {
    ;(async () => {
      const [a, m] = await Promise.all([
        listDataAssets({ page: 1, page_size: 200 }),
        listAiModels({ page: 1, page_size: 200 }),
      ])
      const sensitive = a.items.filter((x) => (x.sensitivity_level || '') === 'high').length
      const avg = a.items.length
        ? a.items.reduce((s, x) => s + (x.quality_score || 0), 0) / a.items.length
        : 0
      setStats({ assets: a.total, models: m.total, avgQuality: avg, sensitive })
    })().catch(() => {})
  }, [])

  return (
    <PageContainer>
      <ProCard gutter={16} wrap>
        <StatisticCard statistic={{ title: '数据资产总数', value: stats.assets }} />
        <StatisticCard statistic={{ title: 'AI模型数', value: stats.models }} />
        <StatisticCard statistic={{ title: '平均质量分', value: stats.avgQuality.toFixed(2) }} />
        <StatisticCard statistic={{ title: '高敏资产数', value: stats.sensitive }} />
      </ProCard>
      <ProCard title="数据资产估值与质量看板" style={{ marginTop: 16 }}>
        <Typography.Paragraph type="secondary">
          连续、结构化的治疗效果数据是平台第二阶段融资估值的核心壁垒。下方为数据资产目录与 AI 模型目录实时视图；
          资产估值随数据沉淀持续累计（示意）。所有资产访问受等保三级权限与审计约束。
        </Typography.Paragraph>
        <Tabs
          items={[
            { key: 'assets', label: '数据资产目录', children: <DataAssetsAdmin /> },
            { key: 'models', label: 'AI模型目录', children: <AiModelsAdmin /> },
          ]}
        />
      </ProCard>
    </PageContainer>
  )
}
