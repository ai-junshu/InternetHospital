import { View, Text, Input, Button } from '@tarojs/components'
import Taro, { useLoad, useRouter } from '@tarojs/taro'
import { useState } from 'react'
import { createPainAssessment } from '@/services/mt'

export default function MtPain() {
  const router = useRouter()
  const customerId = Number(router.params.customer_id)
  const [score, setScore] = useState('')
  const [site, setSite] = useState('')
  const [nature, setNature] = useState('')

  useLoad(() => {
    if (!customerId) Taro.showToast({ title: '缺少客户ID', icon: 'none' })
  })

  const submit = () => {
    const s = Number(score)
    if (!customerId) {
      Taro.showToast({ title: '缺少客户ID，请从客户详情进入', icon: 'none' })
      return
    }
    if (!Number.isFinite(s) || s < 0 || s > 10) {
      Taro.showToast({ title: '疼痛评分 0-10', icon: 'none' })
      return
    }
    Taro.showLoading({ title: '提交中' })
    createPainAssessment({ customer_id: customerId, score: s, pain_site: site, pain_nature: nature, scale_type: 'NRS' })
      .then(() => {
        Taro.showToast({ title: '已保存', icon: 'success' })
        Taro.navigateBack()
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '保存失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  return (
    <View className='mt-page'>
      <View className='mt-card'>
        <Text className='mt-card-title'>疼痛评估</Text>
        <Text className='mt-card-sub'>客户 #{customerId}</Text>
      </View>
      <View className='mt-form'>
        <Text className='mt-label'>NRS 评分 (0-10)</Text>
        <Input className='mt-input' type='number' placeholder='如 6' value={score} onInput={(e) => setScore(e.detail.value)} />
        <Text className='mt-label'>疼痛部位</Text>
        <Input className='mt-input' placeholder='如 腰椎' value={site} onInput={(e) => setSite(e.detail.value)} />
        <Text className='mt-label'>疼痛性质</Text>
        <Input className='mt-input' placeholder='如 钝痛/刺痛' value={nature} onInput={(e) => setNature(e.detail.value)} />
        <Button className='mt-btn' onClick={submit}>提交评估</Button>
      </View>
    </View>
  )
}
