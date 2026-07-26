import { useRef, useState } from 'react'
import {
  PageContainer,
  ProForm,
  ProFormDigit,
  ProTable,
} from '@ant-design/pro-components'
import { Button, Card, Descriptions, message, Tag } from 'antd'
import type { ActionType, ProColumns } from '@ant-design/pro-components'
import { listRisk, predictRisk, type RiskProfile } from '@/services/mt'

export default function RiskAdmin() {
  const actionRef = useRef<ActionType>()
  const [result, setResult] = useState<RiskProfile>()

  const columns: ProColumns<RiskProfile>[] = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    { title: '客户ID', dataIndex: 'customer_id', width: 90 },
    { title: '预测时间', dataIndex: 'predict_time', width: 180 },
    {
      title: '疼痛风险',
      dataIndex: 'pain_risk',
      render: (_, r) => (
        <Tag color={r.pain_risk === 'high' ? 'red' : r.pain_risk === 'medium' ? 'orange' : 'green'}>
          {r.pain_risk ?? '-'}
        </Tag>
      ),
    },
    {
      title: '共病风险',
      dataIndex: 'comorbidity_risk',
      render: (_, r) => (
        <Tag color={r.comorbidity_risk === 'high' ? 'red' : r.comorbidity_risk === 'medium' ? 'orange' : 'green'}>
          {r.comorbidity_risk ?? '-'}
        </Tag>
      ),
    },
    { title: '模型版本', dataIndex: 'model_version', width: 100 },
  ]

  return (
    <PageContainer title="健康风险画像（AI 反馈闭环 · 第15.4章）">
      <Card title="发起风险画像（调用 ai-service risk-profile）" style={{ marginBottom: 16 }}>
        <ProForm
          layout="inline"
          submitter={{ render: ({ form }) => [
            <Button
              key="run"
              type="primary"
              onClick={async () => {
                if (!form) return
                const v = await form.validateFields()
                const r = await predictRisk(v)
                setResult(r)
                message.success('画像完成，已回写 mt_risk_profile')
                actionRef.current?.reload()
              }}
            >
              发起画像
            </Button>,
          ] }}
        >
          <ProFormDigit name="customer_id" label="客户ID" initialValue={1} rules={[{ required: true }]} />
          <ProFormDigit name="age" label="年龄" initialValue={65} />
          <ProFormDigit name="bmi" label="BMI" initialValue={30} />
          <ProFormDigit name="comorbidity_count" label="共病数量" initialValue={3} />
        </ProForm>
        {result && (
          <Descriptions style={{ marginTop: 16 }} column={2} bordered size="small">
            <Descriptions.Item label="客户ID">{result.customer_id}</Descriptions.Item>
            <Descriptions.Item label="模型版本">{result.model_version ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="疼痛风险">{result.pain_risk ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="共病风险">{result.comorbidity_risk ?? '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      <ProTable<RiskProfile>
        rowKey="id"
        headerTitle="画像历史"
        actionRef={actionRef}
        columns={columns}
        search={false}
        pagination={{ pageSize: 20 }}
        request={async (params) => {
          const res = await listRisk({
            page: params.current,
            page_size: params.pageSize,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
    </PageContainer>
  )
}
