import { useRef, useState } from 'react'
import {
  PageContainer,
  ProForm,
  ProFormDigit,
  ProTable,
} from '@ant-design/pro-components'
import { Button, Card, Descriptions, message, Tag } from 'antd'
import type { ActionType, ProColumns } from '@ant-design/pro-components'
import {
  listRepurchase,
  predictRepurchase,
  type RepurchasePrediction,
} from '@/services/mt'

export default function RepurchaseAdmin() {
  const actionRef = useRef<ActionType>()
  const [result, setResult] = useState<RepurchasePrediction>()

  const columns: ProColumns<RepurchasePrediction>[] = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    { title: '客户ID', dataIndex: 'customer_id', width: 90 },
    { title: '预测时间', dataIndex: 'predict_time', width: 180 },
    {
      title: '复诊概率',
      dataIndex: 'next_visit_prob',
      render: (_, r) => (r.next_visit_prob == null ? '-' : `${(r.next_visit_prob * 100).toFixed(1)}%`),
    },
    {
      title: '复购概率',
      dataIndex: 'repurchase_prob',
      render: (_, r) => (r.repurchase_prob == null ? '-' : `${(r.repurchase_prob * 100).toFixed(1)}%`),
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      render: (_, r) => (
        <Tag color={r.risk_level === 'high' ? 'red' : r.risk_level === 'medium' ? 'orange' : 'green'}>
          {r.risk_level ?? '-'}
        </Tag>
      ),
    },
    { title: '模型版本', dataIndex: 'model_version', width: 100 },
  ]

  return (
    <PageContainer title="复购预测（AI 反馈闭环 · 第15.4章）">
      <Card title="发起复购预测（调用 ai-service repurchase-prediction）" style={{ marginBottom: 16 }}>
        <ProForm
          layout="inline"
          submitter={{ render: ({ form }) => [
            <Button
              key="run"
              type="primary"
              onClick={async () => {
                if (!form) return
                const v = await form.validateFields()
                const r = await predictRepurchase(v)
                setResult(r)
                message.success('预测完成，已回写 mt_repurchase_prediction')
                actionRef.current?.reload()
              }}
            >
              发起预测
            </Button>,
          ] }}
        >
          <ProFormDigit name="customer_id" label="客户ID" initialValue={1} rules={[{ required: true }]} />
          <ProFormDigit name="age" label="年龄" initialValue={52} />
          <ProFormDigit name="visit_freq" label="月均到店频次" initialValue={3} />
          <ProFormDigit name="last_gap_days" label="距上次间隔(天)" initialValue={30} />
        </ProForm>
        {result && (
          <Descriptions style={{ marginTop: 16 }} column={2} bordered size="small">
            <Descriptions.Item label="客户ID">{result.customer_id}</Descriptions.Item>
            <Descriptions.Item label="模型版本">{result.model_version ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="复诊概率">
              {result.next_visit_prob == null ? '-' : `${(result.next_visit_prob * 100).toFixed(1)}%`}
            </Descriptions.Item>
            <Descriptions.Item label="复购概率">
              {result.repurchase_prob == null ? '-' : `${(result.repurchase_prob * 100).toFixed(1)}%`}
            </Descriptions.Item>
            <Descriptions.Item label="风险等级">{result.risk_level ?? '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      <ProTable<RepurchasePrediction>
        rowKey="id"
        headerTitle="预测历史"
        actionRef={actionRef}
        columns={columns}
        search={false}
        pagination={{ pageSize: 20 }}
        request={async (params) => {
          const res = await listRepurchase({
            page: params.current,
            page_size: params.pageSize,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
    </PageContainer>
  )
}
