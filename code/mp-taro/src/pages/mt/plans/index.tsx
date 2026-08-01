import { View, Text, ScrollView, Button, Input } from '@tarojs/components'
import Taro, { useLoad, useRouter } from '@tarojs/taro'
import { useState } from 'react'
import { listCarePlans, createCarePlan, type CarePlan } from '@/services/mt'

export default function MtPlans() {
  const router = useRouter()
  const customerId = Number(router.params.customer_id)
  const [list, setList] = useState<CarePlan[]>([])
  const [goal, setGoal] = useState('')
  const [cycle, setCycle] = useState('')
  const [painType, setPainType] = useState('')

  const load = () => {
    listCarePlans({ customer_id: customerId, page: 1, page_size: 20 })
      .then((r) => setList(r.items || []))
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '加载失败', icon: 'none' }))
  }
  useLoad(() => load())

  const submit = () => {
    if (!customerId) return
    Taro.showLoading({ title: '提交中' })
    createCarePlan({ customer_id: customerId, doctor_advice_id: 0, goal, cycle, pain_type: painType })
      .then(() => {
        Taro.showToast({ title: '已创建', icon: 'success' })
        setGoal(''); setCycle(''); setPainType('')
        load()
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '创建失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  return (
    <View className='mt-page'>
      <View className='mt-form'>
        <Text className='mt-label'>疼痛类型</Text>
        <Input className='mt-input' placeholder='如 神经病理性' value={painType} onInput={(e) => setPainType(e.detail.value)} />
        <Text className='mt-label'>目标</Text>
        <Input className='mt-input' placeholder='如 两周疼痛降至3分' value={goal} onInput={(e) => setGoal(e.detail.value)} />
        <Text className='mt-label'>周期</Text>
        <Input className='mt-input' placeholder='如 4周' value={cycle} onInput={(e) => setCycle(e.detail.value)} />
        <Button className='mt-btn' onClick={submit}>新建计划</Button>
      </View>
      <ScrollView scrollY className='mt-scroll'>
        {list.map((p) => (
          <View className='mt-card' key={p.id}>
            <View className='mt-card-row'>
              <Text className='mt-card-title'>计划 #{p.id}</Text>
              <Text className='mt-tag'>{p.status}</Text>
            </View>
            <Text className='mt-card-sub'>{p.goal || p.pain_type || '未填写目标'}</Text>
            {p.cycle && <Text className='mt-card-sub'>周期：{p.cycle}</Text>}
          </View>
        ))}
        {list.length === 0 && <Text className='mt-tip'>暂无计划</Text>}
      </ScrollView>
    </View>
  )
}
