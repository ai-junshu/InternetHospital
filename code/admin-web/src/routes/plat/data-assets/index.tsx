import { useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ModalForm,
  ProFormText,
  ProFormSelect,
  ProFormTextArea,
  type ActionType,
  type ProColumns,
} from '@ant-design/pro-components'
import { Tag, Progress, Button, App, Popconfirm } from 'antd'
import {
  listDataAssets,
  createDataAsset,
  updateDataAsset,
  deleteDataAsset,
  type DataAsset,
} from '@/services/plat'

const SENS_COLOR: Record<string, string> = {
  L1: 'blue',
  L2: 'cyan',
  L3: 'orange',
  L4: 'red',
}

export default function DataAssetsAdmin() {
  const actionRef = useRef<ActionType>()
  const { message } = App.useApp()
  const [edit, setEdit] = useState<DataAsset | null>(null)
  const [open, setOpen] = useState(false)
  const role = localStorage.getItem('role')
  const canEdit = role === 'platform'

  const columns: ProColumns<DataAsset>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    { title: '资产名称', dataIndex: 'name' },
    { title: '归属方', dataIndex: 'owner', width: 140 },
    {
      title: '敏感等级',
      dataIndex: 'sensitivity_level',
      width: 110,
      valueEnum: {
        L1: { text: 'L1' },
        L2: { text: 'L2' },
        L3: { text: 'L3' },
        L4: { text: 'L4' },
      },
      render: (_, r) => (
        <Tag color={SENS_COLOR[r.sensitivity_level ?? 'L1'] ?? 'blue'}>{r.sensitivity_level ?? '-'}</Tag>
      ),
    },
    {
      title: '质量评分',
      dataIndex: 'quality_score',
      width: 140,
      search: false,
      render: (_, r) =>
        r.quality_score == null ? (
          '-'
        ) : (
          <Progress percent={Math.round(r.quality_score * 100)} size="small" />
        ),
    },
    { title: '更新频率', dataIndex: 'update_freq', width: 100, search: false },
    { title: '用途范围', dataIndex: 'usage_scope', search: false, ellipsis: true },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) =>
        canEdit
          ? [
              <a
                key="edit"
                onClick={() => {
                  setEdit(r)
                  setOpen(true)
                }}
              >
                编辑
              </a>,
              <Popconfirm
                key="del"
                title="确认删除该数据资产?"
                onConfirm={async () => {
                  try {
                    await deleteDataAsset(r.id)
                    message.success('已删除')
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
    <PageContainer title="数据资产目录（plat · 第11.2/13章）">
      <ProTable<DataAsset>
        rowKey="id"
        headerTitle="资产分级（L1-L4）与血缘"
        actionRef={actionRef}
        columns={columns}
        pagination={{ pageSize: 20 }}
        toolBarRender={() =>
          canEdit
            ? [
                <Button
                  key="add"
                  type="primary"
                  onClick={() => {
                    setEdit(null)
                    setOpen(true)
                  }}
                >
                  新增资产
                </Button>,
              ]
            : []
        }
        request={async (params) => {
          const res = await listDataAssets({
            page: params.current,
            page_size: params.pageSize,
            name: params.name as string | undefined,
            owner: params.owner as string | undefined,
            sensitivity_level: params.sensitivity_level as string | undefined,
          })
          return { data: res.items, total: res.total, success: true }
        }}
      />
      <ModalForm
        title={edit ? '编辑数据资产' : '新增数据资产'}
        open={open}
        onOpenChange={setOpen}
        width={480}
        initialValues={edit || undefined}
        onFinish={async (v: Partial<DataAsset>) => {
          try {
            if (edit) await updateDataAsset(edit.id, v)
            else await createDataAsset(v)
            message.success('已保存')
            setOpen(false)
            actionRef.current?.reload()
            return true
          } catch {
            return false
          }
        }}
      >
        <ProFormText name="name" label="资产名称" rules={[{ required: true }]} />
        <ProFormText name="owner" label="归属方" />
        <ProFormSelect
          name="sensitivity_level"
          label="敏感等级"
          options={['L1', 'L2', 'L3', 'L4'].map((v) => ({ value: v, label: v }))}
        />
        <ProFormText name="update_freq" label="更新频率" placeholder="如 daily / weekly" />
        <ProFormTextArea name="usage_scope" label="用途范围" />
      </ModalForm>
    </PageContainer>
  )
}
