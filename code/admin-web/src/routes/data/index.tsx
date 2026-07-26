import { useRef, useState } from 'react'
import { PageContainer, ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components'
import { Button, Card, Col, DatePicker, Row, Space, Statistic, Tag } from 'antd'
import { getStoreMetrics, type StoreMetrics } from '@/services/mt'

const { RangePicker } = DatePicker

export default function DataAdmin() {
  const actionRef = useRef<ActionType>(null)
  const [range, setRange] = useState<[string, string] | null>(null)
  const [summary, setSummary] = useState({ appointment: 0, deal: 0, repurchase: 0, nps: 0 })

  const columns: ProColumns<StoreMetrics>[] = [
    { title: '日期', dataIndex: 'date', width: 120 },
    { title: '门店ID', dataIndex: 'store_id', width: 90 },
    { title: '门店', dataIndex: 'store_name', width: 140 },
    {
      title: '区域',
      dataIndex: 'region',
      width: 100,
      render: (_, r) => (r.region ? <Tag color="blue">{r.region}</Tag> : '-'),
    },
    { title: '到店数', dataIndex: 'appointment_cnt', width: 90 },
    { title: '成交客户', dataIndex: 'deal_customers', width: 90 },
    { title: '复购客户', dataIndex: 'repurchase_customers', width: 90 },
    {
      title: 'NPS',
      dataIndex: 'nps_avg',
      width: 90,
      render: (_, r) => (r.nps_avg != null ? r.nps_avg.toFixed(2) : '-'),
    },
  ]

  return (
    <PageContainer
      title="门店经营看板"
      content="健康数据中台 · 门店经营宽表（ClickHouse 预聚合，技术架构第11.3章）"
    >
      <Card style={{ marginBottom: 16 }}>
        <Space size="middle" wrap>
          <RangePicker onChange={(_, ds) => setRange((ds as [string, string]) || null)} />
          <Button type="primary" onClick={() => actionRef.current?.reload()}>
            查询
          </Button>
        </Space>
      </Card>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card hoverable>
            <Statistic title="到店总数" value={summary.appointment} />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic title="成交客户" value={summary.deal} />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic title="复购客户" value={summary.repurchase} />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic title="平均 NPS" value={summary.nps} precision={2} />
          </Card>
        </Col>
      </Row>

      <ProTable<StoreMetrics>
        actionRef={actionRef}
        rowKey={(r) => `${r.date}-${r.store_id}`}
        columns={columns}
        search={false}
        pagination={{ pageSize: 20 }}
        request={async (params) => {
          const res = await getStoreMetrics({
            page: params.current,
            page_size: params.pageSize,
            date_from: range?.[0],
            date_to: range?.[1],
          })
          const items = res.items || []
          const totalNps = items.reduce((s, i) => s + (i.nps_avg || 0), 0)
          setSummary({
            appointment: items.reduce((s, i) => s + (i.appointment_cnt || 0), 0),
            deal: items.reduce((s, i) => s + (i.deal_customers || 0), 0),
            repurchase: items.reduce((s, i) => s + (i.repurchase_customers || 0), 0),
            nps: items.length ? totalNps / items.length : 0,
          })
          return { data: items, success: true, total: res.total }
        }}
      />
    </PageContainer>
  )
}
