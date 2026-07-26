import React from 'react'
import { useEffect, useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormSelect,
  ProFormCheckbox,
  ProFormTextArea,
  type ProColumns,
  type ActionType,
} from '@ant-design/pro-components'
import { Tag, App, Typography } from 'antd'
import {
  listStores,
  listStoreTherapists,
  listTherapistSchedules,
  createTherapistSchedule,
  deleteTherapistSchedule,
  listTherapistTags,
  assignTherapistTag,
  unassignTherapistTag,
  listTherapistTagCatalog,
  type Store,
  type Therapist,
  type TherapistSchedule,
  type TherapistTagRel,
} from '@/services/mt'

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const SLOT_LABELS = ['上午', '下午', '晚上']
const LABEL_TO_WEEKDAY: Record<string, number> = {
  周一: 1, 周二: 2, 周三: 3, 周四: 4, 周五: 5, 周六: 6, 周日: 7,
}
const SLOT_TO_AM: Record<string, string> = { 上午: 'morning', 下午: 'afternoon', 晚上: 'evening' }
const AM_TO_SLOT: Record<string, string> = { morning: '上午', afternoon: '下午', evening: '晚上' }
const AM_TIME: Record<string, [string, string]> = {
  morning: ['08:00', '12:00'],
  afternoon: ['14:00', '18:00'],
  evening: ['19:00', '22:00'],
}

function weekdayOf(dateStr: string): number {
  const [y, m, d] = dateStr.split('-').map(Number)
  return ((new Date(y, m - 1, d).getDay() + 6) % 7) + 1
}

function nextDate(weekday: number, weeksAhead = 0): string {
  const now = new Date()
  const todayDow = (now.getDay() + 6) % 7
  const target = weekday - 1
  let diff = (target - todayDow + 7) % 7
  if (diff === 0) diff = 7
  const dt = new Date(now)
  dt.setDate(now.getDate() + diff + weeksAhead * 7)
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const day = String(dt.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const CUSTOMERS_KEY = 'therapistCustomers'

export default function StorePage() {
  const actionRef = useRef<ActionType>()
  const { message } = App.useApp()
  const [stores, setStores] = useState<Store[]>([])
  const [tagOptions, setTagOptions] = useState<{ label: string; value: number }[]>([])
  const [recordsByTherapist, setRecordsByTherapist] = useState<Record<number, TherapistSchedule[]>>({})
  const [presentByTherapist, setPresentByTherapist] = useState<Record<number, Set<string>>>({})
  const [tagsByTherapist, setTagsByTherapist] = useState<Record<number, number[]>>({})
  const [editId, setEditId] = useState<number | null>(null)
  const [editInit, setEditInit] = useState<Record<string, unknown>>({})
  const [editLoading, setEditLoading] = useState(false)

  useEffect(() => {
    listStores({ page_size: 200 })
      .then((res) => setStores(res.items))
      .catch(() => {})
    listTherapistTagCatalog({ page_size: 200 })
      .then((res) => setTagOptions(res.items.map((t) => ({ label: t.name, value: t.id }))))
      .catch(() => {})
  }, [])

  const openEdit = async (tid: number) => {
    setEditLoading(true)
    try {
      let schedRes = { items: [] as TherapistSchedule[] }
      try {
        schedRes = await listTherapistSchedules(tid, { page: 1, page_size: 200 })
      } catch {}
      let tagRes: TherapistTagRel[] = []
      try {
        tagRes = await listTherapistTags(tid)
      } catch {}
      const present = new Set(schedRes.items.map((r) => `${weekdayOf(r.work_date)}-${r.am_pm}`))
      setRecordsByTherapist((prev) => ({ ...prev, [tid]: schedRes.items }))
      setPresentByTherapist((prev) => ({ ...prev, [tid]: present }))
      setTagsByTherapist((prev) => ({ ...prev, [tid]: tagRes.map((t) => t.tag_id) }))
      const cur = JSON.parse(localStorage.getItem(CUSTOMERS_KEY) || '{}')
      setEditInit({
        days: Array.from(new Set([...present].map((k) => DAY_LABELS[Number(k.split('-')[0]) - 1]))).filter(
          Boolean,
        ),
        shift: Array.from(new Set([...present].map((k) => AM_TO_SLOT[k.split('-')[1]]))).filter(Boolean),
        tags: tagRes.map((t) => t.tag_id),
        customers: cur[tid] || '',
      })
      setEditId(tid)
    } catch {
      message.error('加载调理师排班失败')
    } finally {
      setEditLoading(false)
    }
  }

  const onFinish = async (values: {
    days?: string[]
    shift?: string[]
    tags?: number[]
    customers?: string
  }) => {
    if (editId == null) return false
    const tid = editId
    const desired = new Set<string>()
    ;(values.days || []).forEach((dl) =>
      (values.shift || []).forEach((sl) => {
        const w = LABEL_TO_WEEKDAY[dl]
        const am = SLOT_TO_AM[sl]
        if (w && am) desired.add(`${w}-${am}`)
      }),
    )
    const existing = recordsByTherapist[tid] || []
    const present = presentByTherapist[tid] || new Set<string>()
    try {
      await Promise.all(
        existing
          .filter((r) => !desired.has(`${weekdayOf(r.work_date)}-${r.am_pm}`))
          .map((r) => deleteTherapistSchedule(tid, r.id).catch(() => null)),
      )
      const adds: Promise<unknown>[] = []
      for (const key of desired) {
        if (!present.has(key)) {
          const [, am] = key.split('-')
          const [st, et] = AM_TIME[am]
          adds.push(
            createTherapistSchedule(tid, {
              work_date: nextDate(Number(key.split('-')[0]), 0),
              am_pm: am,
              start_time: st,
              end_time: et,
            }).catch(() => null),
          )
        }
      }
      await Promise.all(adds)
      const prevTags = tagsByTherapist[tid] || []
      const nextTags: number[] = values.tags || []
      await Promise.all([
        ...prevTags
          .filter((id) => !nextTags.includes(id))
          .map((id) => unassignTherapistTag(tid, id).catch(() => null)),
        ...nextTags
          .filter((id) => !prevTags.includes(id))
          .map((id) => assignTherapistTag(tid, id).catch(() => null)),
      ])
      const cur = JSON.parse(localStorage.getItem(CUSTOMERS_KEY) || '{}')
      localStorage.setItem(CUSTOMERS_KEY, JSON.stringify({ ...cur, [tid]: values.customers || '' }))
      const [schedRes, tagRes] = await Promise.all([
        listTherapistSchedules(tid, { page: 1, page_size: 200 }).catch(() => ({
          items: [] as TherapistSchedule[],
        })),
        listTherapistTags(tid).catch(() => [] as TherapistTagRel[]),
      ])
      setRecordsByTherapist((prev) => ({ ...prev, [tid]: schedRes.items }))
      setPresentByTherapist((prev) => ({
        ...prev,
        [tid]: new Set(schedRes.items.map((r) => `${weekdayOf(r.work_date)}-${r.am_pm}`)),
      }))
      setTagsByTherapist((prev) => ({ ...prev, [tid]: tagRes.map((t) => t.tag_id) }))
      message.success('已保存到后端')
      actionRef.current?.reload()
      return true
    } catch {
      message.error('保存失败，请重试')
      return false
    }
  }

  const tagName = (id: number) => tagOptions.find((o) => o.value === id)?.label || `标签${id}`

  const columns: ProColumns<Therapist>[] = [
    {
      title: '选择门店',
      dataIndex: 'storeId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        options: stores.map((s) => ({ label: `${s.name || s.id}`, value: s.id })),
        placeholder: '先选择门店',
      },
    },
    {
      title: '门店',
      dataIndex: 'store_id',
      hideInSearch: true,
      render: (_, r) => stores.find((s) => s.id === r.store_id)?.name || r.store_id,
    },
    { title: '调理师', dataIndex: 'name' },
    { title: '执业编号', dataIndex: 'license_no' },
    {
      title: '排班',
      dataIndex: 'id',
      hideInSearch: true,
      render: (_, r) => {
        const present = presentByTherapist[r.id]
        if (!present || present.size === 0)
          return <Typography.Text type="secondary">未排班</Typography.Text>
        return (
          <Typography.Text>
            {Array.from(present)
              .map((k) => `${DAY_LABELS[Number(k.split('-')[0]) - 1]}${AM_TO_SLOT[k.split('-')[1]]}`)
              .join('、')}
          </Typography.Text>
        )
      },
    },
    {
      title: '能力标签',
      dataIndex: 'id',
      hideInSearch: true,
      render: (_, r) => {
        const ids = tagsByTherapist[r.id] || []
        if (!ids.length) return <Typography.Text type="secondary">—</Typography.Text>
        return ids.map((id) => <Tag key={id}>{tagName(id)}</Tag>)
      },
    },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) => [
        <a key="edit" onClick={() => openEdit(r.id)}>
          排班 / 分配
        </a>,
      ],
    },
  ]

  return (
    <PageContainer title="门店管理">
      <ProTable<Therapist>
        headerTitle="门店调理师"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        options={{ reload: true, setting: true }}
        request={async (params) => {
          const storeId = (params as { storeId?: number }).storeId
          if (!storeId) return { data: [], success: true }
          const res = await listStoreTherapists(storeId, {
            page: params.current,
            page_size: params.pageSize,
          })
          return { data: res.items, success: true, total: res.total }
        }}
        pagination={{ pageSize: 10 }}
      />
      <ModalForm
        title="排班 / 能力标签分配"
        open={editId != null}
        initialValues={editInit}
        onOpenChange={(v) => {
          if (!v) setEditId(null)
        }}
        onFinish={onFinish}
        width={560}
      >
        <ProFormCheckbox.Group name="days" label="可服务日" options={DAY_LABELS} />
        <ProFormSelect
          name="shift"
          label="班次"
          mode="multiple"
          options={SLOT_LABELS.map((s) => ({ label: s, value: s }))}
        />
        <ProFormSelect
          name="tags"
          label="能力标签"
          mode="multiple"
          options={tagOptions}
          placeholder="从标签库选择"
        />
        <ProFormTextArea
          name="customers"
          label="客户分配"
          extra="客户分配为本地备注，不提交后端"
          placeholder="请输入客户分配说明"
        />
      </ModalForm>
    </PageContainer>
  )
}
