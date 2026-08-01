import { View, Text, ScrollView, Button, Input } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'
import { useState } from 'react'
import { listRiskProfiles, predictRisk, type RiskProfile } from '@/services/mt'

export default function MtRisk() {
  const [list, setList] = useState<RiskProfile[]>([])
  const [customerId, setCustomerId] = useState('')
  const [age, setAge] = useState('')
  const [bmi, setBmi] = useState('')
  const [comorbidity, setComorbidity] = useState('')

  const load = () => {
    listRiskProfiles({ page: 1, page_size: 20 })
      .then((r) => setList(r.items || []))
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '加载失败', icon: 'none' }))
  }
  useLoad(() => load())

  const predict = () => {
    const cid = Number(customerId)
    if (!Number.isFinite(cid) || cid <= 0) {
      Taro.showToast({ title: '请输入客户ID', icon: 'none' })
      return
    }
    Taro.showLoading({ title: 'AI 评估中' })
    predictRisk({
      customer_id: cid,
      age: age ? Number(age) : undefined,
      bmi: bmi ? Number(bmi) : undefined,
      comorbidity_count: comorbidity ? Number(comorbidity) : undefined,
    })
      .then(() => {
        Taro.showToast({ title: '评估完成', icon: 'success' })
        load()
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '评估失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  const levelText = (lvl?: string) => (lvl === 'high' ? '高风险' : lvl === 'medium' ? '中风险' : lvl === 'low' ? '低风险' : lvl || '-')

  return (
    <View className='mt-page'>
      <View className='mt-form'>
        <Text className='mt-label'>客户 ID</Text>
        <Input className='mt-input' type='number' placeholder='如 1' value={customerId} onInput={(e) => setCustomerId(e.detail.value)} />
        <Text className='mt-label'>年龄</Text>
        <Input className='mt-input' type='number' placeholder='选填' value={age} onInput={(e) => setAge(e.detail.value)} />
        <Text className='mt-label'>BMI</Text>
        <Input className='mt-input' type='number' placeholder='选填' value={bmi} onInput={(e) => setBmi(e.detail.value)} />
        <Text className='mt-label'>合并症数量</Text>
        <Input className='mt-input' type='number' placeholder='选填' value={comorbidity} onInput={(e) => setComorbidity(e.detail.value)} />
        <Button className='mt-btn' onClick={predict}>触发 AI 风险画像</Button>
      </View>
      <ScrollView scrollY className='mt-scroll'>
        {list.map((r) => (
          <View className='mt-card' key={r.id}>
            <View className='mt-card-row'>
              <Text className='mt-card-title'>客户 #{r.customer_id}</Text>
              <Text className='mt-tag'>{levelText(r.pain_risk)}</Text>
            </View>
            {r.comorbidity_risk && <Text className='mt-card-sub'>合并症风险：{levelText(r.comorbidity_risk)}</Text>}
            {r.model_version && <Text className='mt-card-sub'>模型 {r.model_version}</Text>}
          </View>
        ))}
        {list.length === 0 && <Text className='mt-tip'>暂无风险画像</Text>}
      </ScrollView>
    </View>
  )
}
