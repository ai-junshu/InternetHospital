import { View, Text, ScrollView, Button, Input } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'
import { useState } from 'react'
import { listRepurchasePredictions, predictRepurchase, type RepurchasePrediction } from '@/services/mt'

export default function MtRepurchase() {
  const [list, setList] = useState<RepurchasePrediction[]>([])
  const [customerId, setCustomerId] = useState('')
  const [visitFreq, setVisitFreq] = useState('')
  const [lastGap, setLastGap] = useState('')

  const load = () => {
    listRepurchasePredictions({ page: 1, page_size: 20 })
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
    Taro.showLoading({ title: 'AI 预测中' })
    predictRepurchase({
      customer_id: cid,
      visit_freq: visitFreq ? Number(visitFreq) : undefined,
      last_gap_days: lastGap ? Number(lastGap) : undefined,
    })
      .then(() => {
        Taro.showToast({ title: '预测完成', icon: 'success' })
        load()
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '预测失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  const levelText = (lvl?: string) => (lvl === 'high' ? '高复购' : lvl === 'low' ? '低复购' : lvl || '-')

  return (
    <View className='mt-page'>
      <View className='mt-form'>
        <Text className='mt-label'>客户 ID</Text>
        <Input className='mt-input' type='number' placeholder='如 1' value={customerId} onInput={(e) => setCustomerId(e.detail.value)} />
        <Text className='mt-label'>到店频次</Text>
        <Input className='mt-input' type='number' placeholder='选填' value={visitFreq} onInput={(e) => setVisitFreq(e.detail.value)} />
        <Text className='mt-label'>最近到店间隔(天)</Text>
        <Input className='mt-input' type='number' placeholder='选填' value={lastGap} onInput={(e) => setLastGap(e.detail.value)} />
        <Button className='mt-btn' onClick={predict}>触发 AI 复购预测</Button>
      </View>
      <ScrollView scrollY className='mt-scroll'>
        {list.map((r) => (
          <View className='mt-card' key={r.id}>
            <View className='mt-card-row'>
              <Text className='mt-card-title'>客户 #{r.customer_id}</Text>
              <Text className='mt-tag'>{levelText(r.risk_level)}</Text>
            </View>
            <Text className='mt-card-sub'>
              复购概率 {r.repurchase_prob != null ? `${(r.repurchase_prob * 100).toFixed(0)}%` : '-'} ·
              下次到店 {r.next_visit_prob != null ? `${(r.next_visit_prob * 100).toFixed(0)}%` : '-'}
            </Text>
            {r.model_version && <Text className='mt-card-sub'>模型 {r.model_version}</Text>}
          </View>
        ))}
        {list.length === 0 && <Text className='mt-tip'>暂无预测记录</Text>}
      </ScrollView>
    </View>
  )
}
