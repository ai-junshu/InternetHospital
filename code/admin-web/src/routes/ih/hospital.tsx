import { useEffect, useRef, useState } from 'react'
import {
  PageContainer,
  ProTable,
  ProCard,
  ModalForm,
  ProFormText,
  ProFormTextArea,
  ProFormDigit,
  ActionType,
} from '@ant-design/pro-components'
import { Button, Tag, Tabs, Space, Typography, message, Popconfirm } from 'antd'
import type { ProColumns } from '@ant-design/pro-components'
import {
  listDoctors,
  approveDoctor,
  rejectDoctor,
  listPharmacies,
  createPharmacy,
  deletePharmacy,
  listDepartments,
  createDepartment,
  deleteDepartment,
  type Doctor,
  type Pharmacy,
  type Department,
} from '@/services/ih'

const statusColor: Record<string, string> = {
  active: 'green',
  pending: 'gold',
  disabled: 'red',
}

const role = localStorage.getItem('role')
const canEditPharmacy = role === 'platform'
const canEditDept = role === 'platform'

function DoctorTab() {
  const actionRef = useRef<ActionType>()
  // H6：科室筛选项（从科室列表动态加载）
  const [deptOptions, setDeptOptions] = useState<{ label: string; value: number }[]>([])
  useEffect(() => {
    listDepartments({ page: 1, page_size: 200 }).then((res) =>
      setDeptOptions(res.items.map((d) => ({ label: d.name, value: d.id }))),
    )
  }, [])
  const columns: ProColumns<Doctor>[] = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '执业证号', dataIndex: 'license_no', width: 150 },
    { title: '职称', dataIndex: 'title', width: 100 },
    // H6：优先展示联表返回的 dept_name，兼容旧 dept 字符串
    {
      title: '科室',
      dataIndex: 'dept_name',
      width: 120,
      valueType: 'select',
      fieldProps: { options: deptOptions, allowClear: true, placeholder: '按科室筛选' },
      render: (_, r) => r.dept_name || r.dept || '—',
    },
    { title: '擅长', dataIndex: 'good_at', ellipsis: true },
    { title: '问诊费(分)', dataIndex: 'consult_price', width: 110 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (_, r) => <Tag color={statusColor[r.status]}>{r.status}</Tag>,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, r) =>
        r.status === 'pending' ? (
          <Space>
            <a
              onClick={async () => {
                await approveDoctor(r.id, 1)
                actionRef.current?.reload()
                message.success('医师已通过')
              }}
            >
              通过
            </a>
            <a
              onClick={async () => {
                await rejectDoctor(r.id, 1)
                actionRef.current?.reload()
                message.success('医师已驳回')
              }}
            >
              驳回
            </a>
          </Space>
        ) : (
          <span>—</span>
        ),
    },
  ]
  return (
    <ProTable<Doctor>
      rowKey="id"
      actionRef={actionRef}
      columns={columns}
      search={{ labelWidth: 'auto' }}
      request={async (params) => {
        const res = await listDoctors({
          page: params.current,
          page_size: params.pageSize,
          status: params.status as string,
          dept_id: params.dept_name ? Number(params.dept_name) : undefined,
        })
        return { data: res.items, total: res.total, success: true }
      }}
      pagination={{ pageSize: 10 }}
      toolBarRender={() => []}
    />
  )
}

function DeptTab() {
  const actionRef = useRef<ActionType>()
  const columns: ProColumns<Department>[] = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '科室名称', dataIndex: 'name' },
    { title: '科室主任', dataIndex: 'head', width: 120 },
    { title: '备注', dataIndex: 'remark', ellipsis: true },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) =>
        canEditDept ? (
          <Popconfirm
            key="del"
            title="确认删除该科室？"
            onConfirm={async () => {
              try {
                await deleteDepartment(r.id)
                message.success('已删除')
                actionRef.current?.reload()
              } catch (e: any) {
                message.error(e?.response?.data?.message || '删除失败')
              }
            }}
          >
            <a>删除</a>
          </Popconfirm>
        ) : (
          <span>—</span>
        ),
    },
  ]
  return (
    <>
      <ProTable<Department>
        rowKey="id"
        columns={columns}
        search={false}
        pagination={false}
        actionRef={actionRef}
        request={async () => {
          const res = await listDepartments({ page: 1, page_size: 200 })
          return { data: res.items, success: true }
        }}
        toolBarRender={() =>
          canEditDept
            ? [
                <ModalForm<Department>
                  key="add"
                  title="新增科室"
                  trigger={<Button type="primary">新增科室</Button>}
                  onFinish={async (v) => {
                    try {
                      await createDepartment({ name: v.name, head: v.head ?? undefined, remark: v.remark ?? undefined })
                      message.success('已新增')
                      actionRef.current?.reload()
                      return true
                    } catch (e: any) {
                      message.error(e?.response?.data?.message || '新增失败')
                      return false
                    }
                  }}
                >
                  <ProFormText name="name" label="科室名称" rules={[{ required: true }]} />
                  <ProFormText name="head" label="科室主任" />
                  <ProFormTextArea name="remark" label="备注" />
                </ModalForm>,
              ]
            : []
        }
      />
    </>
  )
}

function PharmacyTab() {
  const actionRef = useRef<ActionType>()
  const columns: ProColumns<Pharmacy>[] = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '药房名称', dataIndex: 'name' },
    { title: '区域', dataIndex: 'region', width: 90 },
    { title: '药品经营许可证', dataIndex: 'license_no', width: 160 },
    { title: '联系人', dataIndex: 'contact', width: 120 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (_, r) => <Tag color={r.status === 'active' ? 'green' : 'red'}>{r.status}</Tag>,
    },
    {
      title: '操作',
      valueType: 'option',
      render: (_, r) =>
        canEditPharmacy
          ? [
              <Popconfirm
                key="del"
                title="确认删除该药房？"
                onConfirm={async () => {
                  try {
                    await deletePharmacy(r.id)
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
    <>
      <ProTable<Pharmacy>
        rowKey="id"
        columns={columns}
        search={false}
        pagination={false}
        actionRef={actionRef}
        request={async () => {
          const res = await listPharmacies({ page: 1, page_size: 200 })
          return { data: res.items, success: true }
        }}
        toolBarRender={() =>
          canEditPharmacy
            ? [
                <ModalForm<Pharmacy>
                  key="add"
                  title="新增合作药房"
                  trigger={<Button type="primary">新增药房</Button>}
                  onFinish={async (v) => {
                    try {
                      await createPharmacy({ name: v.name, region: v.region, license_no: v.license_no, contact: v.contact })
                      message.success('已新增')
                      actionRef.current?.reload()
                      return true
                    } catch (e: any) {
                      message.error(e?.response?.data?.message || '新增失败')
                      return false
                    }
                  }}
                >
                  <ProFormText name="name" label="药房名称" rules={[{ required: true }]} />
                  <ProFormText name="region" label="区域" />
                  <ProFormText name="license_no" label="药品经营许可证" rules={[{ required: true }]} />
                  <ProFormText name="contact" label="联系人/电话" />
                </ModalForm>,
              ]
            : []
        }
      />
    </>
  )
}

export default function IhHospital() {
  return (
    <PageContainer>
      <ProCard>
        <Tabs
          items={[
            { key: 'doctor', label: '医师管理', children: <DoctorTab /> },
            { key: 'dept', label: '科室管理', children: <DeptTab /> },
            { key: 'pharmacy', label: '合作药房管理', children: <PharmacyTab /> },
          ]}
        />
      </ProCard>
    </PageContainer>
  )
}
