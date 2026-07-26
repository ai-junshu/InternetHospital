import { useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
} from '@ant-design/pro-components'
import { Button, Card, Col, Row, Statistic, Tag, message } from 'antd'
import type { ActionType, ProColumns } from '@ant-design/pro-components'
import {
  listAuditLogs,
  listDataAssets,
  verifyAuditChain,
  type AuditLog,
  type DataAsset,
} from '@/services/plat'

const REQUIRED_FIELDS = [
  '患者主诉',
  '临床诊断',
  '电子处方',
  '过敏史',
  '知情同意书',
  '复诊记录',
]

export default function ComplianceBrain() {
  const actionRef = useRef<ActionType>()
  const [chainOk, setChainOk] = useState<boolean | null>(null)
  const [brokenAt, setBrokenAt] = useState<number | null>(null)
  const [assetTotal, setAssetTotal] = useState(0)
  const [restricted, setRestricted] = useState(0)
  const [logTotal, setLogTotal] = useState(0)

  const loadStats = async () => {
    const a = await listDataAssets({ page: 1, page_size: 1 })
    setAssetTotal(a.total)
    setRestricted(
      (await listDataAssets({ page: 1, page_size: 200, sensitivity_level: 'restricted' })).total +
        (await listDataAssets({ page: 1, page_size: 200, sensitivity_level: 'confidential' })).total,
    )
    setLogTotal((await listAuditLogs({ page: 1, page_size: 1 })).total)
  }

  const onVerify = async () => {
    const r = await verifyAuditChain()
    setChainOk(r.ok)
    setBrokenAt(r.broken_at_seq)
    message[r.ok ? 'success' : 'error'](
      r.ok ? '审计哈希链完整，未被篡改' : `哈希链在序号 ${r.broken_at_seq} 处断裂`,
    )
  }

  const columns: ProColumns<AuditLog>[] = [
    { title: '序号', dataIndex: 'seq_no', width: 70 },
    { title: '操作人', dataIndex: 'actor_id', width: 90 },
    { title: '角色', dataIndex: 'role', width: 90, render: (_, r) => <Tag>{r.role}</Tag> },
    { title: '动作', dataIndex: 'action', width: 90 },
    { title: '资源', dataIndex: 'resource', ellipsis: true },
    { title: 'IP', dataIndex: 'ip', width: 120 },
    { title: '时间', dataIndex: 'created_at', width: 170 },
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
    { title: '使用范围', dataIndex: 'usage_scope', ellipsis: true },
    { title: '负责人', dataIndex: 'owner', width: 110 },
  ]

  return (
    <PageContainer
      title="合规大脑（3.6.1）"
      extra={
        <Button type="primary" onClick={() => { onVerify(); loadStats() }}>
          校验哈希链完整性
        </Button>
      }
    >
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="审计日志总量" value={logTotal} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="哈希链完整性"
              value={chainOk == null ? '未校验' : chainOk ? '完整' : `断裂@${brokenAt}`}
              valueStyle={{ color: chainOk == null ? '#8c8c8c' : chainOk ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="数据资产数" value={assetTotal} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="受限对外输出" value={restricted} valueStyle={{ color: '#fa8c16' }} />
          </Card>
        </Col>
      </Row>

      <Card title="数据采集字段合规清单（必采字段）" style={{ marginTop: 16 }}>
        <p style={{ color: '#595959', marginTop: 0 }}>
          下列字段为互联网医院执业与等保三级要求的最低采集项，缺失将影响执业许可与测评通过：
        </p>
        <div>
          {REQUIRED_FIELDS.map((f) => (
            <Tag color="blue" key={f} style={{ marginBottom: 8 }}>
              {f}
            </Tag>
          ))}
        </div>
      </Card>

      <ProTable<AuditLog>
        rowKey="id"
        headerTitle="数据使用监控（审计日志）"
        actionRef={actionRef}
        columns={columns}
        search={false}
        pagination={{ pageSize: 20 }}
        cardProps={{ style: { marginTop: 16 } }}
        request={async (params) => {
          const res = await listAuditLogs({ page: params.current, page_size: params.pageSize })
          if (!logTotal) setLogTotal(res.total)
          return { data: res.items, total: res.total, success: true }
        }}
      />

      <ProTable<DataAsset>
        rowKey="id"
        headerTitle="对外输出审核（数据资产使用范围）"
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
