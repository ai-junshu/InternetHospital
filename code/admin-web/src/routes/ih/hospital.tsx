import { useRef, useState } from 'react'
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
import { Button, Tag, Tabs, Space, Typography, message } from 'antd'
import type { ProColumns } from '@ant-design/pro-components'
import {
  listDoctors,
  approveDoctor,
  rejectDoctor,
  type Doctor,
} from '@/services/ih'

const statusColor: Record<string, string> = {
  active: 'green',
  pending: 'gold',
  disabled: 'red',
}

// 科室（后端接口 /ih/departments 待对接，当前前端演示态）
interface DeptItem {
  id: number
  name: string
  head: string
  doctor_cnt: number
  remark?: string
}

// 合作药房（后端接口 /ih/pharmacies 待对接，当前前端演示态）
interface PharmacyItem {
  id: number
  name: string
  region: string
  license: string
  status: string
}

const DEMO_DEPTS: DeptItem[] = [
  { id: 1, name: '疼痛科', head: '张明', doctor_cnt: 6 },
  { id: 2, name: '康复医学科', head: '李华', doctor_cnt: 4 },
]

const DEMO_PHARMACIES: PharmacyItem[] = [
  { id: 1, name: '星耀互联网药房（北京）', region: '华北', license: '京药许2026-001', status: 'active' },
  { id: 2, name: '星耀互联网药房（上海）', region: '华东', license: '沪药许2026-014', status: 'active' },
]

function DoctorTab() {
  const actionRef = useRef<ActionType>()
  const columns: ProColumns<Doctor>[] = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '执业证号', dataIndex: 'license_no', width: 150 },
    { title: '职称', dataIndex: 'title', width: 100 },
    { title: '科室', dataIndex: 'dept', width: 110 },
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
                await approveDoctor(r.id)
                actionRef.current?.reload()
                message.success('医师已通过')
              }}
            >
              通过
            </a>
            <a
              onClick={async () => {
                await rejectDoctor(r.id)
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
          dept: params.dept as string,
        })
        return { data: res.items, total: res.total, success: true }
      }}
      pagination={{ pageSize: 10 }}
      toolBarRender={() => []}
    />
  )
}

function DeptTab() {
  const [data, setData] = useState<DeptItem[]>(DEMO_DEPTS)
  const columns: ProColumns<DeptItem>[] = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '科室名称', dataIndex: 'name' },
    { title: '科室主任', dataIndex: 'head', width: 120 },
    { title: '医师数', dataIndex: 'doctor_cnt', width: 90 },
    { title: '备注', dataIndex: 'remark', ellipsis: true },
  ]
  return (
    <>
      <ProTable<DeptItem>
        rowKey="id"
        columns={columns}
        dataSource={data}
        search={false}
        pagination={false}
        toolBarRender={() => [
          <ModalForm<DeptItem>
            key="add"
            title="新增科室"
            trigger={<Button type="primary">新增科室</Button>}
            onFinish={async (v) => {
              setData((d) => [...d, { ...v, id: Date.now() }])
              message.success('已新增（演示态，待后端对接）')
              return true
            }}
          >
            <ProFormText name="name" label="科室名称" rules={[{ required: true }]} />
            <ProFormText name="head" label="科室主任" />
            <ProFormDigit name="doctor_cnt" label="医师数" />
            <ProFormTextArea name="remark" label="备注" />
          </ModalForm>,
        ]}
      />
      <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
        注：科室管理后端接口（<code>/ih/departments</code>）待对接，当前为前端演示态。
      </Typography.Paragraph>
    </>
  )
}

function PharmacyTab() {
  const [data, setData] = useState<PharmacyItem[]>(DEMO_PHARMACIES)
  const columns: ProColumns<PharmacyItem>[] = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    { title: '药房名称', dataIndex: 'name' },
    { title: '区域', dataIndex: 'region', width: 90 },
    { title: '药品经营许可证', dataIndex: 'license', width: 160 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (_, r) => <Tag color={r.status === 'active' ? 'green' : 'red'}>{r.status}</Tag>,
    },
  ]
  return (
    <>
      <ProTable<PharmacyItem>
        rowKey="id"
        columns={columns}
        dataSource={data}
        search={false}
        pagination={false}
        toolBarRender={() => [
          <ModalForm<PharmacyItem>
            key="add"
            title="新增合作药房"
            trigger={<Button type="primary">新增药房</Button>}
            onFinish={async (v) => {
              setData((d) => [...d, { ...v, id: Date.now(), status: 'active' }])
              message.success('已新增（演示态，待后端对接）')
              return true
            }}
          >
            <ProFormText name="name" label="药房名称" rules={[{ required: true }]} />
            <ProFormText name="region" label="区域" />
            <ProFormText name="license" label="药品经营许可证" rules={[{ required: true }]} />
          </ModalForm>,
        ]}
      />
      <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
        注：合作药房管理后端接口（<code>/ih/pharmacies</code>）待对接，当前为前端演示态。
      </Typography.Paragraph>
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
