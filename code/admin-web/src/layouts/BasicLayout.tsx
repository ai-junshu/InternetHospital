import { ProLayout } from '@ant-design/pro-components'
import { Link, Outlet, useLocation } from 'react-router-dom'

export default function BasicLayout() {
  const location = useLocation()
  return (
    <ProLayout
      title="互联网医疗中心平台"
      layout="mix"
      location={{ pathname: location.pathname }}
      route={{
        path: '/',
        routes: [
          { path: '/customer', name: '客户管理' },
          { path: '/repurchase', name: '复购预测' },
          { path: '/risk', name: '风险画像' },
          { path: '/store', name: '门店管理' },
          { path: '/data', name: '数据中台' },
          {
            path: '/ih',
            name: '互联网医院管理',
            routes: [
              { path: '/ih/hospital', name: '医院管理' },
              { path: '/ih/operations', name: '运营数据' },
              { path: '/ih/patients', name: '患者管理' },
              { path: '/ih/orders', name: '订单管理' },
              { path: '/ih/consultations', name: '问诊会话' },
              { path: '/ih/schedules', name: '医生排班' },
              { path: '/ih/rx-review', name: '处方审核' },
              { path: '/ih/drug-catalog', name: '药品目录' },
              { path: '/ih/complaints', name: '投诉与售后' },
            ],
          },
          {
            path: '/therapist',
            name: '调理师工作台',
            routes: [
              { path: '/therapist/customers', name: '客户管理' },
              { path: '/therapist/plans', name: '调理方案' },
              { path: '/therapist/records', name: '治疗记录' },
              { path: '/therapist/adherence', name: '依从性管理' },
            ],
          },
          {
            path: '/plat',
            name: '平台管理',
            routes: [
              { path: '/plat/ai-models', name: 'AI模型目录' },
              { path: '/plat/data-assets', name: '数据资产目录' },
              { path: '/plat/compliance', name: '合规大脑' },
              { path: '/plat/data-governance', name: '治疗数据沉淀' },
              { path: '/plat/ih-supervision', name: '互联网医院监管' },
              { path: '/plat/sales-supervision', name: '产品销售监管' },
              { path: '/plat/data-asset-dashboard', name: '数据资产看板' },
              { path: '/plat/compliance-review', name: '合规采集审核' },
            ],
          },
        ],
      }}
      menuItemRender={(item, dom) => <Link to={item.path || '/'}>{dom}</Link>}
    >
      <Outlet />
    </ProLayout>
  )
}
