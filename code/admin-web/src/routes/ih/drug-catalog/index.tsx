import { useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormSelect,
  ProFormDigit,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { Button, Tag, App, Popconfirm } from 'antd'
import { listDrugs, createDrug, updateDrug, deleteDrug, type IhDrug } from '@/services/ih'

const OTC_ENUM = {
  rx: { text: '处方药', status: 'Error' },
  otc: { text: 'OTC', status: 'Success' },
}
const STATUS_ENUM = {
  on: { text: '在售', status: 'Success' },
  off: { text: '下架', status: 'Default' },
}

export default function DrugCatalogAdmin() {
  const actionRef = useRef<ActionType>()
  const { message } = App.useApp()
  const role = localStorage.getItem('role')
  const canEdit = role === 'platform'
  const [editOpen, setEditOpen] = useState(false)
  const [editRecord, setEditRecord] = useState<IhDrug | null>(null)

  const openCreate = () => {
    setEditRecord(null)
    setEditOpen(true)
  }
  const openEdit = (r: IhDrug) => {
    setEditRecord(r)
    setEditOpen(true)
  }

  const columns: ProColumns<IhDrug>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    { title: '药品名称', dataIndex: 'name' },
    { title: '规格', dataIndex: 'spec', search: false },
    { title: '厂商', dataIndex: 'manufacturer', search: false },
    {
      title: 'OTC类型',
      dataIndex: 'otc_type',
      width: 120,
      valueType: 'select',
      valueEnum: OTC_ENUM,
      render: (_, r) => (
        <Tag color={r.otc_type === 'rx' ? 'red' : 'green'}>
          {r.otc_type === 'rx' ? '处方药' : 'OTC'}
        </Tag>
      ),
    },
    { title: '分类', dataIndex: 'category', search: false },
    { title: '单位', dataIndex: 'unit', width: 80, search: false },
    {
      title: '价格',
      dataIndex: 'price',
      width: 100,
      search: false,
      render: (_, r) => `￥${((r.price || 0) / 100).toFixed(2)}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: STATUS_ENUM,
      render: (_, r) => (
        <Tag color={r.status === 'on' ? 'green' : 'default'}>
          {r.status === 'on' ? '在售' : '下架'}
        </Tag>
      ),
    },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) =>
        canEdit
          ? [
              <a key="edit" onClick={() => openEdit(r)}>
                编辑
              </a>,
              <Popconfirm
                key="del"
                title="确认下架该药品？"
                onConfirm={async () => {
                  try {
                    await deleteDrug(r.id)
                    message.success('已下架')
                    actionRef.current?.reload()
                  } catch {}
                }}
              >
                <a>下架</a>
              </Popconfirm>,
            ]
          : [],
    },
  ]

  return (
    <PageContainer title="药品目录（ih · platform 管理）">
      <ProTable<IhDrug>
        rowKey="id"
        headerTitle="药品目录"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() =>
          canEdit ? [<Button key="add" type="primary" onClick={openCreate}>新建药品</Button>] : []
        }
        request={async (params) => {
          const res = await listDrugs({
            page: params.current,
            page_size: params.pageSize,
            keyword: params.name as string | undefined,
            otc_type: params.otc_type as string | undefined,
            category: params.category as string | undefined,
            status: params.status as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
      <ModalForm
        title={editRecord ? '编辑药品' : '新建药品'}
        open={editOpen}
        initialValues={
          editRecord
            ? { ...editRecord, priceYuan: (editRecord.price || 0) / 100 }
            : { status: 'on' }
        }
        onOpenChange={(o) => {
          if (!o) setEditRecord(null)
        }}
        width={520}
        onFinish={async (v: {
          name: string
          spec?: string
          manufacturer?: string
          otc_type: string
          category?: string
          unit?: string
          priceYuan?: number
          status?: string
        }) => {
          const body = {
            name: v.name,
            spec: v.spec,
            manufacturer: v.manufacturer,
            otc_type: v.otc_type,
            category: v.category,
            unit: v.unit,
            price: Math.round((v.priceYuan || 0) * 100),
            status: v.status || 'on',
          }
          try {
            if (editRecord) await updateDrug(editRecord.id, body)
            else await createDrug(body)
            message.success('已保存')
            setEditRecord(null)
            actionRef.current?.reload()
            return true
          } catch {
            return false
          }
        }}
      >
        <ProFormText name="name" label="药品名称" rules={[{ required: true }]} />
        <ProFormText name="spec" label="规格" />
        <ProFormText name="manufacturer" label="生产厂商" />
        <ProFormSelect
          name="otc_type"
          label="OTC类型"
          options={[
            { label: '处方药', value: 'rx' },
            { label: 'OTC', value: 'otc' },
          ]}
          rules={[{ required: true }]}
        />
        <ProFormText name="category" label="分类" />
        <ProFormText name="unit" label="单位" />
        <ProFormDigit
          name="priceYuan"
          label="价格(元)"
          min={0}
          rules={[{ required: true }]}
          fieldProps={{ precision: 2 }}
        />
        <ProFormSelect
          name="status"
          label="状态"
          options={[
            { label: '在售', value: 'on' },
            { label: '下架', value: 'off' },
          ]}
        />
      </ModalForm>
    </PageContainer>
  )
}
