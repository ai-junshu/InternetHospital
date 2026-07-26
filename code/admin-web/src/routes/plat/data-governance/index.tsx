import { useEffect, useState } from 'react'
import { PageContainer, ProTable } from '@ant-design/pro-components'
import { Card, Col, Row, Statistic, Tag } from 'antd'
import type { ProColumns } from '@ant-design/pro-components'
import {
  listCarePlans,
  listStores,
  listTreatmentRecords,
  type CarePlan,
  type Store,
  type TreatmentRecord,
} from '@/services/mt'
import { listDataAssets, type DataAsset } from '@/services/plat'

export default function DataGovernance() {
  const [stores, setStores] = useState(0)
  const [plans, setPlans] = useState(0)
  const [records, setRecords] = useState(0)
  const [assets, setAssets] = useState(0)

  useEffect(() => {
    listStores({ page: 1, page_size: 1 }).then((r) => setStores(r.total))
    listCarePlans({ page: 1, page_size: 1 }).then((r) => setPlans(r.total))
    listTreatmentRecords({ page: 1, page_size: 1 }).then((r) => setRecords(r.total))
    listDataAssets({ page: 1, page_size: 1 }).then((r) => setAssets(r.total))
  }, [])

  const planColumns: ProColumns<CarePlan>[] = [
    { title: '方案ID', dataIndex: 'id', width: 80 },
    {
      title: '疼痛类型（结构化维度一）',
      dataIndex: 'pain_type',
      render: (_, r) => <Tag color="blue">{r.pain_type || '未分类'}</Tag>,
    },
    { title: '目标', dataIndex: 'goal', ellipsis: true },
    { title: '周期', dataIndex: 'cycle', width: 110 },
    {
      title: '产品组合（结构化维度三）',
      dataIndex: 'product_combo_json',
      ellipsis: true,
      render: (_, r) => (r.product_combo_json ? String(JSON.stringify(r.product_combo_json)) : '—'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (_, r) => <Tag color={r.status === 'active' ? 'green' : 'default'}>{r.status}</Tag>,
    },
  ]

  const assetColumns: ProColumns<DataAsset>[] = [
    { title: '资产名称', dataIndex: 'name' },
    {
      title: '敏感度',
      dataIndex: 'sensitivity_level',
      width: 110,
      render: (_, r) => (
        <Tag color={r.sensitivity_level === 'public' ? 'green' : 'volcano'}>
          {r.sensitivity_level}
        </Tag>
      ),
    },
    { title: '数据质量分', dataIndex: 'quality_score', width: 110 },
    { title: '更新时间', dataIndex: 'update_time', width: 160 },
  ]

  return (
    <PageContainer title="治疗数据沉淀（3.6.2）">
      <Card>
        <p style={{ color: '#595959', marginTop: 0 }}>
          治疗数据沉淀指将门店调理过程的结构化数据（疼痛类型 / 方案 / 产品组合 / 疗效）
          标准化采集、治理后形成可资产化、可对外赋能的核心数据壁垒，支撑第二阶段融资估值。
        </p>
      </Card>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="接入门店数" value={stores} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="调理方案数" value={plans} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="治疗记录数" value={records} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="治理后数据资产" value={assets} valueStyle={{ color: '#1677ff' }} />
          </Card>
        </Col>
      </Row>

      <ProTable<CarePlan>
        rowKey="id"
        headerTitle="结构化存储三维 · 调理方案（疼痛类型 / 方案 / 产品组合）"
        columns={planColumns}
        search={false}
        pagination={{ pageSize: 20 }}
        cardProps={{ style: { marginTop: 16 } }}
        request={async (params) => {
          const res = await listCarePlans({ page: params.current, page_size: params.pageSize })
          return { data: res.items, total: res.total, success: true }
        }}
      />

      <ProTable<DataAsset>
        rowKey="id"
        headerTitle="数据质量治理 · 资产目录（详见数据资产管理）"
        columns={assetColumns}
        search={false}
        pagination={{ pageSize: 20 }}
        cardProps={{ style: { marginTop: 16 } }}
        request={async (params) => {
          const res = await listDataAssets({ page: params.current, page_size: params.pageSize })
          return { data: res.items, total: res.total, success: true }
        }}
      />
    </PageContainer>
  )
}
