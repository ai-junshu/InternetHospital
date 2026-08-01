import { View, Text, Button } from '@tarojs/components'
import Taro, { useLoad, useRouter } from '@tarojs/taro'
import { useEffect, useState } from 'react'
import { listCarePlans, listPainAssessments, listTreatmentRecords, type Customer } from '@/services/mt'

export default function MtCustomerDetail() {
  const router = useRouter()
  const id = Number(router.params.id)
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [plans, setPlans] = useState<number>(0)
  const [pains, setPains] = useState<number>(0)
  const [records, setRecords] = useState<number>(0)

  useLoad(() => {
    listCarePlans({ customer_id: id, page_size: 1 }).then((r) => setPlans(r.total ?? 0)).catch(() => {})
    listPainAssessments({ customer_id: id, page_size: 1 }).then((r) => setPains(r.total ?? 0)).catch(() => {})
    listTreatmentRecords({ customer_id: id, page_size: 1 }).then((r) => setRecords(r.total ?? 0)).catch(() => {})
  })

  useEffect(() => {
    if (id) setCustomer({ id, auth_status: 'authorized' })
  }, [id])

  return (
    <View className='mt-page'>
      <View className='mt-card'>
        <Text className='mt-card-title'>客户 #{id}</Text>
        <Text className='mt-card-sub'>{customer?.name_mask || '匿名客户'}</Text>
      </View>
      <View className='mt-stat-row'>
        <View className='mt-stat'><Text className='mt-stat-num'>{pains}</Text><Text className='mt-stat-label'>疼痛评估</Text></View>
        <View className='mt-stat'><Text className='mt-stat-num'>{plans}</Text><Text className='mt-stat-label'>照护计划</Text></View>
        <View className='mt-stat'><Text className='mt-stat-num'>{records}</Text><Text className='mt-stat-label'>治疗记录</Text></View>
      </View>
      <Button className='mt-btn' onClick={() => Taro.navigateTo({ url: `/pages/mt/pain/index?customer_id=${id}` })}>新增疼痛评估</Button>
      <Button className='mt-btn' onClick={() => Taro.navigateTo({ url: `/pages/mt/plans/index?customer_id=${id}` })}>新建照护计划</Button>
      <Button className='mt-btn' onClick={() => Taro.navigateTo({ url: `/pages/mt/records/index?customer_id=${id}` })}>录入治疗记录</Button>
    </View>
  )
}
