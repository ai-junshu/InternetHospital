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
import { listSchedules, createSchedule, deleteSchedule, type IhSchedule } from '@/services/ih'

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
    { title: '号源容量', dataIndex: 'capacity', width: 100, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      search: false,
      render: (_, r) => <Tag color={r.status === 'open' ? 'green' : 'default'}>{r.status || '-'}</Tag>,
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
                    await deleteSchedule(r.id)
                    message.success('已删除')
                    actionRef.current?.reload()
                  } catch (e: any) {
                    message.error(e?.response?.data?.message || '删除失败')
                  }
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
          onFinish={async (v: {
            doctor_id: number
            date: string
            am_pm: string
            start_time: string
            end_time: string
            capacity?: number
          }) => {
            try {
              await createSchedule({
                doctor_id: v.doctor_id,
                work_date: v.date,
                am_pm: v.am_pm,
                start_time: v.start_time,
                end_time: v.end_time,
                capacity: v.capacity,
              })
              message.success('已新增排班')
              actionRef.current?.reload()
              return true
            } catch (e: any) {
              message.error(e?.response?.data?.message || '新增失败')
              return false
            }
          }}
        >
          <ProFormDigit name="doctor_id" label="医生ID" min={1} rules={[{ required: true }]} />
          <ProFormText name="date" label="出诊日期" placeholder="YYYY-MM-DD" rules={[{ required: true }]} />
          <ProFormText name="am_pm" label="时段" placeholder="morning/afternoon/evening" initialValue="morning" rules={[{ required: true }]} />
          <ProFormText name="start_time" label="开始时间" placeholder="09:00" rules={[{ required: true }]} />
          <ProFormText name="end_time" label="结束时间" placeholder="12:00" rules={[{ required: true }]} />
          <ProFormDigit name="capacity" label="号源容量" min={1} initialValue={1} />
        </ModalForm>
      )}
    </PageContainer>
  )
}
