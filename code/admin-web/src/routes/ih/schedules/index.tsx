import { useRef } from 'react'
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormDigit,
  ProFormSwitch,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { Button, App, Popconfirm } from 'antd'
import { listSchedules, type IhSchedule } from '@/services/ih'

export default function ScheduleAdmin() {
  const actionRef = useRef<ActionType>()
  const { message } = App.useApp()
  const role = localStorage.getItem('role')
  const canEdit = role === 'platform' || role === 'doctor'

  const columns: ProColumns<IhSchedule>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    { title: '医生ID', dataIndex: 'doctor_id', width: 90 },
    { title: '出诊日期', dataIndex: 'work_date', width: 130 },
    {
      title: '时段',
      dataIndex: 'am_pm',
      width: 100,
      search: false,
      render: (_, r) => {
        const m: Record<string, string> = { morning: '上午', afternoon: '下午', evening: '晚上' }
        return m[r.am_pm] || r.am_pm || '-'
      },
    },
    {
      title: '时间',
      dataIndex: 'start_time',
      width: 140,
      search: false,
      render: (_, r) => `${r.start_time || ''}~${r.end_time || ''}`,
    },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) =>
        canEdit
          ? [
              <Popconfirm
                key="del"
                title="确认删除该排班？"
                onConfirm={async () => {
                  try {
                    message.success('已删除（需后端 DELETE 支持）')
                    actionRef.current?.reload()
                  } catch {}
                }}
              >
                <a>删除</a>
              </Popconfirm>,
            ]
          : [],
    },
  ]

  return (
    <PageContainer title="医生排班管理（ih）">
      <ProTable<IhSchedule>
        rowKey="id"
        headerTitle="排班列表"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const res = await listSchedules({
            page: params.current,
            page_size: params.pageSize,
            doctor_id: params.doctor_id as number | undefined,
            work_date: params.work_date as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
      {canEdit && (
        <ModalForm
          title="新增排班"
          trigger={<Button type="primary">新增排班</Button>}
          width={480}
          onFinish={async (v: { doctor_id: number; date: string; am?: boolean; pm?: boolean }) => {
            message.info('新增排班接口（POST /ih/schedules）待联调')
            return true
          }}
        >
          <ProFormDigit name="doctor_id" label="医生ID" min={1} rules={[{ required: true }]} />
          <ProFormText name="date" label="出诊日期" placeholder="YYYY-MM-DD" rules={[{ required: true }]} />
          <ProFormSwitch name="am" label="上午出诊" />
          <ProFormSwitch name="pm" label="下午出诊" />
        </ModalForm>
      )}
    </PageContainer>
  )
}
