import { useRef, useState } from 'react'
import {
  ModalForm,
  PageContainer,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components'
import { Button, Drawer, Empty, List, Tag, Tabs, Descriptions, message } from 'antd'
import type { ActionType, ProColumns } from '@ant-design/pro-components'
import {
  authorizeCustomer,
  listCustomers,
  listPainAssessments,
  listTreatmentRecords,
  listRepurchase,
  listRisk,
  type Customer,
  type PainAssessment,
  type TreatmentRecord,
  type RepurchasePrediction,
  type RiskProfile,
} from '@/services/mt'

export default function CustomerAdmin() {
  const actionRef = useRef<ActionType>()
  const [authId, setAuthId] = useState<number>()
  const [detail, setDetail] = useState<Customer>()
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [assess, setAssess] = useState<PainAssessment[]>([])
  const [records, setRecords] = useState<TreatmentRecord[]>([])
  const [repu, setRepu] = useState<RepurchasePrediction[]>([])
  const [risk, setRisk] = useState<RiskProfile[]>([])

  const openDetail = async (c: Customer) => {
    setDetail(c)
    setOpen(true)
    setLoading(true)
    const [a, r, p, k] = await Promise.all([
      listPainAssessments({ customer_id: c.id, page: 1, page_size: 20 }),
      listTreatmentRecords({ customer_id: c.id, page: 1, page_size: 20 }),
      listRepurchase({ customer_id: c.id, page: 1, page_size: 20 }),
      listRisk({ customer_id: c.id, page: 1, page_size: 20 }),
    ])
    setAssess(a.items)
    setRecords(r.items)
    setRepu(p.items)
    setRisk(k.items)
    setLoading(false)
  }

  const columns: ProColumns<Customer>[] = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    { title: '姓名(脱敏)', dataIndex: 'name_mask' },
    {
      title: '性别',
      dataIndex: 'gender',
      width: 80,
      render: (_, r) => <Tag>{r.gender || '未知'}</Tag>,
    },
    { title: '手机号(脱敏)', dataIndex: 'phone_mask', width: 130 },
    {
      title: '授权状态',
      dataIndex: 'auth_status',
      width: 110,
      render: (_, r) => (
        <Tag color={r.auth_status === 'authorized' ? 'green' : 'orange'}>
          {r.auth_status}
        </Tag>
      ),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 160,
      render: (_, r) => [
        <a key="detail" onClick={() => openDetail(r)}>
          健康档案
        </a>,
        r.auth_status !== 'authorized' && (
          <a key="auth" onClick={() => setAuthId(r.id)}>
            授权
          </a>
        ),
      ],
    },
  ]

  return (
    <PageContainer title="客户健康档案管理（3.4.1）">
      <ProTable<Customer>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        pagination={{ pageSize: 20 }}
        request={async (params) => {
          const res = await listCustomers({ page: params.current, page_size: params.pageSize })
          return { data: res.items, total: res.total, success: true }
        }}
      />

      <ModalForm
        title="客户档案授权"
        open={authId != null}
        initialValues={{ auth_file_url: '' }}
        onOpenChange={(v) => !v && setAuthId(undefined)}
        modalProps={{ destroyOnClose: true }}
        onFinish={async (values) => {
          if (authId == null) return false
          await authorizeCustomer(authId, values.auth_file_url)
          message.success('已提交授权，等待审核')
          setAuthId(undefined)
          actionRef.current?.reload()
          return true
        }}
      >
        <ProFormText
          name="auth_file_url"
          label="授权书文件地址"
          placeholder="https://..."
          rules={[{ required: true, message: '请填写授权书地址' }]}
        />
      </ModalForm>

      <Drawer
        title={`客户健康档案 · #${detail?.id} ${detail?.name_mask || ''}`}
        width={640}
        open={open}
        onClose={() => setOpen(false)}
        loading={loading}
      >
        <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="姓名(脱敏)">{detail?.name_mask || '—'}</Descriptions.Item>
          <Descriptions.Item label="性别">{detail?.gender || '—'}</Descriptions.Item>
          <Descriptions.Item label="手机号(脱敏)">{detail?.phone_mask || '—'}</Descriptions.Item>
          <Descriptions.Item label="来源门店ID">{detail?.source_store_id ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="授权状态">{detail?.auth_status}</Descriptions.Item>
        </Descriptions>

        <Tabs
          items={[
            {
              key: 'assess',
              label: `疼痛评估(${assess.length})`,
              children:
                assess.length === 0 ? (
                  <Empty description="暂无评估" />
                ) : (
                  <List
                    dataSource={assess}
                    renderItem={(i) => (
                      <List.Item>
                        <div>
                          <Tag color="red">评分 {i.score ?? '—'}</Tag>
                          <Tag>部位 {i.pain_site || '—'}</Tag>
                          <Tag>性质 {i.pain_nature || '—'}</Tag>
                          <div style={{ color: '#8c8c8c', fontSize: 12, marginTop: 4 }}>
                            {String(i.scale_type || '')} · {String(i.assess_time || '')}
                          </div>
                        </div>
                      </List.Item>
                    )}
                  />
                ),
            },
            {
              key: 'records',
              label: `治疗记录(${records.length})`,
              children:
                records.length === 0 ? (
                  <Empty description="暂无记录" />
                ) : (
                  <List
                    dataSource={records}
                    renderItem={(i) => (
                      <List.Item>
                        <div>
                          <Tag color="blue">门店 {i.store_id}</Tag>
                          <Tag>调理师 {i.therapist_id ?? '—'}</Tag>
                          <Tag>NPS {i.nps ?? '—'}</Tag>
                          <div style={{ color: '#8c8c8c', fontSize: 12, marginTop: 4 }}>
                            {String(i.service_time || '')} · {i.remark || ''}
                          </div>
                        </div>
                      </List.Item>
                    )}
                  />
                ),
            },
            {
              key: 'repu',
              label: `复购预测(${repu.length})`,
              children:
                repu.length === 0 ? (
                  <Empty description="暂无预测" />
                ) : (
                  <List
                    dataSource={repu}
                    renderItem={(i) => (
                      <List.Item>
                        <div>
                          <Tag color="purple">复购概率 {i.repurchase_prob ?? '—'}</Tag>
                          <Tag>到店概率 {i.next_visit_prob ?? '—'}</Tag>
                          <Tag color="orange">{i.risk_level || '—'}</Tag>
                          <div style={{ color: '#8c8c8c', fontSize: 12, marginTop: 4 }}>
                            模型版本 {i.model_version || '—'}
                          </div>
                        </div>
                      </List.Item>
                    )}
                  />
                ),
            },
            {
              key: 'risk',
              label: `风险画像(${risk.length})`,
              children:
                risk.length === 0 ? (
                  <Empty description="暂无画像" />
                ) : (
                  <List
                    dataSource={risk}
                    renderItem={(i) => (
                      <List.Item>
                        <div>
                          <Tag color="volcano">疼痛风险 {i.pain_risk || '—'}</Tag>
                          <Tag color="volcano">共病风险 {i.comorbidity_risk || '—'}</Tag>
                          <div style={{ color: '#8c8c8c', fontSize: 12, marginTop: 4 }}>
                            模型版本 {i.model_version || '—'}
                          </div>
                        </div>
                      </List.Item>
                    )}
                  />
                ),
            },
          ]}
        />
      </Drawer>
    </PageContainer>
  )
}
