import { View, Text, Input, Button } from '@tarojs/components'
import Taro, { useLoad, useRouter } from '@tarojs/taro'
import { useState } from 'react'
import { createTreatmentRecord } from '@/services/mt'

export default function MtRecords() {
  const router = useRouter()
  const customerId = Number(router.params.customer_id)
  const [storeId, setStoreId] = useState('')
  const [nps, setNps] = useState('')
  const [remark, setRemark] = useState('')

  useLoad(() => {
    if (!customerId) Taro.showToast({ title: '缺少客户ID', icon: 'none' })
  })

  const submit = () => {
    if (!customerId) return
    const sid = Number(storeId)
    if (!Number.isFinite(sid) || sid <= 0) {
      Taro.showToast({ title: '请输入门店ID', icon: 'none' })
      return
    }
    const n = nps ? Number(nps) : undefined
    Taro.showLoading({ title: '提交中' })
    createTreatmentRecord({ customer_id: customerId, store_id: sid, nps: n, remark })
      .then(() => {
        Taro.showToast({ title: '已记录', icon: 'success' })
        Taro.navigateBack()
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '保存失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  return (
    <View className='mt-page'>
      <View className='mt-card'>
        <Text className='mt-card-title'>治疗记录</Text>
        <Text className='mt-card-sub'>客户 #{customerId}</Text>
      </View>
      <View className='mt-form'>
        <Text className='mt-label'>门店 ID</Text>
        <Input className='mt-input' type='number' placeholder='如 1' value={storeId} onInput={(e) => setStoreId(e.detail.value)} />
        <Text className='mt-label'>NPS 满意度 (0-10)</Text>
        <Input className='mt-input' type='number' placeholder='选填' value={nps} onInput={(e) => setNps(e.detail.value)} />
        <Text className='mt-label'>备注</Text>
        <Input className='mt-input' placeholder='选填' value={remark} onInput={(e) => setRemark(e.detail.value)} />
        <Button className='mt-btn' onClick={submit}>提交记录</Button>
      </View>
    </View>
  )
}
