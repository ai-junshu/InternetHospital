import { View, Text, Input, Button, ScrollView } from '@tarojs/components'
import Taro, { useLoad, useRouter } from '@tarojs/taro'
import { useState } from 'react'
import { createTreatmentRecord, listTreatmentRecords, reviseTreatmentRecord, type TreatmentRecord } from '@/services/mt'

export default function MtRecords() {
  const router = useRouter()
  const customerId = Number(router.params.customer_id)
  const [storeId, setStoreId] = useState<number | undefined>(undefined)
  const [nps, setNps] = useState('')
  const [remark, setRemark] = useState('')
  const [list, setList] = useState<TreatmentRecord[]>([])
  const [revising, setRevising] = useState<TreatmentRecord | null>(null)
  const [revReason, setRevReason] = useState('')

  useLoad(() => {
    if (!customerId) {
      Taro.showToast({ title: '缺少客户ID，请从客户详情进入', icon: 'none' })
      return
    }
    loadList()
  })

  const loadList = () => {
    if (!customerId) return
    listTreatmentRecords({ customer_id: customerId, page: 1, page_size: 20 })
      .then((r) => setList(r.items || []))
      .catch(() => {})
  }

  const submit = () => {
    if (!customerId) {
      Taro.showToast({ title: '缺少客户ID，请从客户详情进入', icon: 'none' })
      return
    }
    if (!storeId) {
      Taro.showToast({ title: '请选择门店', icon: 'none' })
      return
    }
    const n = nps ? Number(nps) : undefined
    Taro.showLoading({ title: '提交中' })
    createTreatmentRecord({ customer_id: customerId, store_id: storeId, nps: n, remark })
      .then(() => {
        Taro.showToast({ title: '已记录', icon: 'success' })
        setNps(''); setRemark('')
        loadList()
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '保存失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  // 合规强规则2：治疗记录不可删，仅可更正留痕
  const submitRevise = () => {
    if (!revising) return
    if (!revReason.trim()) {
      Taro.showToast({ title: '请填写更正原因', icon: 'none' })
      return
    }
    Taro.showLoading({ title: '更正中' })
    reviseTreatmentRecord(revising.id, { reason: revReason.trim() })
      .then(() => {
        Taro.showToast({ title: '已更正（留痕）', icon: 'success' })
        setRevising(null); setRevReason('')
        loadList()
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '更正失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  return (
    <View className='mt-page'>
      <View className='mt-card'>
        <Text className='mt-card-title'>治疗记录</Text>
        <Text className='mt-card-sub'>客户 #{customerId}</Text>
      </View>
      <View className='mt-form'>
        <Text className='mt-label'>门店 ID（必填，默认取所属门店）</Text>
        <Input className='mt-input' type='number' placeholder='如 1' value={storeId == null ? '' : String(storeId)} onInput={(e) => setStoreId(Number(e.detail.value) || undefined)} />
        <Text className='mt-label'>NPS 满意度 (0-10)</Text>
        <Input className='mt-input' type='number' placeholder='选填' value={nps} onInput={(e) => setNps(e.detail.value)} />
        <Text className='mt-label'>备注</Text>
        <Input className='mt-input' placeholder='选填' value={remark} onInput={(e) => setRemark(e.detail.value)} />
        <Button className='mt-btn' onClick={submit}>提交记录</Button>
      </View>
      <Text className='mt-label'>历史记录（不可删，可更正留痕）</Text>
      <ScrollView scrollY className='mt-scroll'>
        {list.map((r) => (
          <View className='mt-card' key={r.id}>
            <View className='mt-card-row'>
              <Text className='mt-card-title'>记录 #{r.id}</Text>
              <Text className='mt-link' onClick={() => { setRevising(r); setRevReason('') }}>更正</Text>
            </View>
            <Text className='mt-card-sub'>门店{r.store_id} · NPS{r.nps ?? '-'} · {r.service_time || r.created_at || ''}</Text>
          </View>
        ))}
        {list.length === 0 && <Text className='mt-tip'>暂无记录</Text>}
      </ScrollView>
      {revising && (
        <View className='mt-modal'>
          <Text className='mt-card-title'>更正记录 #{revising.id}（留痕，不可删）</Text>
          <Input className='mt-input' placeholder='更正原因（必填）' value={revReason} onInput={(e) => setRevReason(e.detail.value)} />
          <Button className='mt-btn' onClick={submitRevise}>提交更正</Button>
          <Button className='mt-btn-ghost' onClick={() => setRevising(null)}>取消</Button>
        </View>
      )}
    </View>
  )
}
