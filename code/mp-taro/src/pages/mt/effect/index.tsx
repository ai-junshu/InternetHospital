import { View, Text, Input, Button, ScrollView, Picker } from '@tarojs/components'
import Taro, { useLoad, useRouter } from '@tarojs/taro'
import { useState } from 'react'
import { createEffectTracking, listEffectTracking } from '@/services/mt'

const EFFECT_LEVELS = ['significant', 'effective', 'ineffective', 'worsened']

export default function MtEffect() {
  const router = useRouter()
  const customerId = Number(router.params.customer_id)
  const [list, setList] = useState<any[]>([])
  const [planId, setPlanId] = useState('')
  const [levelIdx, setLevelIdx] = useState(0)
  const [baselinePain, setBaselinePain] = useState('')
  const [latestPain, setLatestPain] = useState('')
  const [nps, setNps] = useState('')
  const [repurchaseCount, setRepurchaseCount] = useState('')

  const load = () => {
    if (!customerId) {
      Taro.showToast({ title: '缺少客户ID，请从客户详情进入', icon: 'none' })
      return
    }
    listEffectTracking({ customer_id: customerId, page: 1, page_size: 20 })
      .then((r) => setList(r.items || []))
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '加载失败', icon: 'none' }))
  }
  useLoad(() => load())

  const submit = () => {
    if (!customerId) {
      Taro.showToast({ title: '缺少客户ID，请从客户详情进入', icon: 'none' })
      return
    }
    if (!planId) {
      Taro.showToast({ title: '请填写关联照护计划ID', icon: 'none' })
      return
    }
    const body: Record<string, unknown> = {
      customer_id: customerId,
      plan_id: Number(planId),
      effect_level: EFFECT_LEVELS[levelIdx],
    }
    if (baselinePain) body.baseline_pain = Number(baselinePain)
    if (latestPain) body.latest_pain = Number(latestPain)
    if (nps) body.nps = Number(nps)
    if (repurchaseCount) body.repurchase_count = Number(repurchaseCount)
    Taro.showLoading({ title: '提交中' })
    createEffectTracking(body as any)
      .then(() => {
        Taro.showToast({ title: '已记录效果', icon: 'success' })
        setPlanId(''); setBaselinePain(''); setLatestPain(''); setNps(''); setRepurchaseCount('')
        load()
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '保存失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  return (
    <View className='mt-page'>
      <View className='mt-card'>
        <Text className='mt-card-title'>效果四档</Text>
        <Text className='mt-card-sub'>客户 #{customerId}</Text>
      </View>
      <View className='mt-form'>
        <Text className='mt-label'>关联照护计划 ID</Text>
        <Input className='mt-input' type='number' placeholder='必填' value={planId} onInput={(e) => setPlanId(e.detail.value)} />
        <Text className='mt-label'>效果四档</Text>
        <Picker mode='selector' range={EFFECT_LEVELS} value={levelIdx} onChange={(e) => setLevelIdx(Number(e.detail.value))}>
          <View className='mt-input'>{EFFECT_LEVELS[levelIdx]}</View>
        </Picker>
        <Text className='mt-label'>基线疼痛评分（选填）</Text>
        <Input className='mt-input' type='number' placeholder='0-10' value={baselinePain} onInput={(e) => setBaselinePain(e.detail.value)} />
        <Text className='mt-label'>最新疼痛评分（选填）</Text>
        <Input className='mt-input' type='number' placeholder='0-10' value={latestPain} onInput={(e) => setLatestPain(e.detail.value)} />
        <Text className='mt-label'>NPS 满意度（选填）</Text>
        <Input className='mt-input' type='number' placeholder='0-10' value={nps} onInput={(e) => setNps(e.detail.value)} />
        <Text className='mt-label'>复购次数（选填）</Text>
        <Input className='mt-input' type='number' placeholder='选填' value={repurchaseCount} onInput={(e) => setRepurchaseCount(e.detail.value)} />
        <Button className='mt-btn' onClick={submit}>提交效果</Button>
      </View>
      <Text className='mt-label'>历史效果</Text>
      <ScrollView scrollY className='mt-scroll'>
        {list.map((r) => (
          <View className='mt-card' key={r.id}>
            <View className='mt-card-row'>
              <Text className='mt-card-title'>效果 #{r.id}</Text>
              <Text className='mt-tag'>{r.effect_level || '未分级'}</Text>
            </View>
            <Text className='mt-card-sub'>计划{r.plan_id} · 疼痛 {r.baseline_pain ?? '-'}→{r.latest_pain ?? '-'}</Text>
            {(r.nps != null) && <Text className='mt-card-sub'>NPS {r.nps}</Text>}
            {(r.repurchase_count != null) && <Text className='mt-card-sub'>复购 {r.repurchase_count} 次</Text>}
            {r.generated_at && <Text className='mt-card-sub'>{r.generated_at}</Text>}
          </View>
        ))}
        {list.length === 0 && <Text className='mt-tip'>暂无效果记录</Text>}
      </ScrollView>
    </View>
  )
}
