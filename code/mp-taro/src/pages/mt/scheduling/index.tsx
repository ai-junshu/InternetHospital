import { View, Text, Input, Button, ScrollView, Picker } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'
import { useState } from 'react'
import {
  assignTag,
  createSchedule,
  listSchedules,
  listStores,
  listTags,
  listTherapists,
  unassignTag,
  type Schedule,
  type Store,
  type Tag,
  type Therapist,
} from '@/services/mt'

const AM_PM = ['morning', 'afternoon', 'evening']

export default function MtScheduling() {
  const [stores, setStores] = useState<Store[]>([])
  const [therapists, setTherapists] = useState<Therapist[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [storeIdx, setStoreIdx] = useState(0)
  const [therapistIdx, setTherapistIdx] = useState(0)
  const [amPmIdx, setAmPmIdx] = useState(0)
  const [workDate, setWorkDate] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [capacity, setCapacity] = useState('')
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [tagIdx, setTagIdx] = useState(0)

  const loadTags = () => {
    listTags({ page_size: 50 }).then((r) => setTags(r.items || [])).catch(() => {})
  }

  const loadSchedules = (therapistId: number) => {
    if (!therapistId) return
    listSchedules(therapistId, { page: 1, page_size: 20 })
      .then((r) => setSchedules(r.items || []))
      .catch(() => setSchedules([]))
  }

  const onStoreChange = (idx: number) => {
    setStoreIdx(idx)
    setTherapistIdx(0)
    const sid = stores[idx]?.id
    if (sid) {
      listTherapists(sid, { page_size: 50 })
        .then((r) => { setTherapists(r.items || []); loadSchedules(r.items?.[0]?.id) })
        .catch(() => setTherapists([]))
    }
  }

  useLoad(() => {
    listStores({ page_size: 50 }).then((r) => {
      setStores(r.items || [])
      const sid = r.items?.[0]?.id
      if (sid) {
        listTherapists(sid, { page_size: 50 })
          .then((rr) => { setTherapists(rr.items || []); loadSchedules(rr.items?.[0]?.id) })
          .catch(() => {})
      }
    }).catch(() => {})
    loadTags()
  })

  const submitSchedule = () => {
    const therapistId = therapists[therapistIdx]?.id
    if (!therapistId) {
      Taro.showToast({ title: '请先选择门店与调理师', icon: 'none' })
      return
    }
    if (!workDate || !startTime || !endTime) {
      Taro.showToast({ title: '请填写日期与时段', icon: 'none' })
      return
    }
    Taro.showLoading({ title: '提交中' })
    createSchedule(therapistId, {
      therapist_id: therapistId,
      work_date: workDate,
      am_pm: AM_PM[amPmIdx],
      start_time: startTime,
      end_time: endTime,
      capacity: capacity ? Number(capacity) : 1,
    })
      .then(() => {
        Taro.showToast({ title: '已排班', icon: 'success' })
        setWorkDate(''); setStartTime(''); setEndTime(''); setCapacity('')
        loadSchedules(therapistId)
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '排班失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  const submitAssignTag = () => {
    const therapistId = therapists[therapistIdx]?.id
    const tagId = tags[tagIdx]?.id
    if (!therapistId || !tagId) {
      Taro.showToast({ title: '请选择调理师与标签', icon: 'none' })
      return
    }
    Taro.showLoading({ title: '分配中' })
    assignTag(therapistId, tagId)
      .then(() => Taro.showToast({ title: '已分配标签', icon: 'success' }))
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '分配失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  const onUnassignTag = (tagId: number) => {
    const therapistId = therapists[therapistIdx]?.id
    if (!therapistId) return
    Taro.showModal({
      title: '解绑标签',
      content: '确认解除该调理师的此标签？',
      success: (res) => {
        if (res.confirm) {
          unassignTag(therapistId, tagId)
            .then(() => Taro.showToast({ title: '已解绑', icon: 'success' }))
            .catch((e) => Taro.showToast({ title: (e?.message as string) || '解绑失败', icon: 'none' }))
        }
      },
    })
  }

  return (
    <View className='mt-page'>
      <Text className='mt-label'>排班管理</Text>
      <View className='mt-form'>
        <Text className='mt-label'>门店</Text>
        <Picker mode='selector' range={stores.map((s) => s.name || `门店#${s.id}`)} value={storeIdx} onChange={(e) => onStoreChange(Number(e.detail.value))}>
          <View className='mt-input'>{stores[storeIdx]?.name || `门店#${stores[storeIdx]?.id}` || '请选择'}</View>
        </Picker>
        <Text className='mt-label'>调理师</Text>
        <Picker mode='selector' range={therapists.map((t) => t.name || t.name_mask || `调理师#${t.id}`)} value={therapistIdx} onChange={(e) => { const i = Number(e.detail.value); setTherapistIdx(i); loadSchedules(therapists[i]?.id) }}>
          <View className='mt-input'>{therapists[therapistIdx]?.name || therapists[therapistIdx]?.name_mask || `调理师#${therapists[therapistIdx]?.id}` || '请选择'}</View>
        </Picker>
        <Text className='mt-label'>工作日期</Text>
        <Input className='mt-input' placeholder='YYYY-MM-DD' value={workDate} onInput={(e) => setWorkDate(e.detail.value)} />
        <Text className='mt-label'>时段（上午/下午/晚上）</Text>
        <Picker mode='selector' range={AM_PM} value={amPmIdx} onChange={(e) => setAmPmIdx(Number(e.detail.value))}>
          <View className='mt-input'>{AM_PM[amPmIdx]}</View>
        </Picker>
        <Text className='mt-label'>开始时间</Text>
        <Input className='mt-input' placeholder='HH:MM' value={startTime} onInput={(e) => setStartTime(e.detail.value)} />
        <Text className='mt-label'>结束时间</Text>
        <Input className='mt-input' placeholder='HH:MM' value={endTime} onInput={(e) => setEndTime(e.detail.value)} />
        <Text className='mt-label'>可约名额（选填）</Text>
        <Input className='mt-input' type='number' placeholder='默认1' value={capacity} onInput={(e) => setCapacity(e.detail.value)} />
        <Button className='mt-btn' onClick={submitSchedule}>提交排班</Button>
      </View>

      <Text className='mt-label'>标签分配</Text>
      <View className='mt-form'>
        <Text className='mt-label'>选择标签</Text>
        <Picker mode='selector' range={tags.map((t) => `${t.name}${t.category ? `（${t.category}）` : ''}`)} value={tagIdx} onChange={(e) => setTagIdx(Number(e.detail.value))}>
          <View className='mt-input'>{tags[tagIdx]?.name || '请选择'}</View>
        </Picker>
        <Button className='mt-btn' onClick={submitAssignTag}>分配给当前调理师</Button>
      </View>

      <Text className='mt-label'>当前调理师排班</Text>
      <ScrollView scrollY className='mt-scroll'>
        {schedules.map((s, i) => (
          <View className='mt-card' key={i}>
            <View className='mt-card-row'>
              <Text className='mt-card-title'>排班</Text>
              <Text className='mt-tag'>{s.status || 'open'}</Text>
            </View>
            <Text className='mt-card-sub'>{s.work_date} · {s.am_pm} · {s.start_time}-{s.end_time}</Text>
            {s.capacity != null && <Text className='mt-card-sub'>名额 {s.capacity}</Text>}
          </View>
        ))}
        {schedules.length === 0 && <Text className='mt-tip'>该调理师暂无排班</Text>}
      </ScrollView>

      <Text className='mt-label'>标签目录</Text>
      <ScrollView scrollY className='mt-scroll'>
        {tags.map((t) => (
          <View className='mt-card' key={t.id}>
            <View className='mt-card-row'>
              <Text className='mt-card-title'>{t.name}</Text>
              <Text className='mt-link' onClick={() => onUnassignTag(t.id)}>解绑</Text>
            </View>
            {t.category && <Text className='mt-card-sub'>{t.category}</Text>}
          </View>
        ))}
        {tags.length === 0 && <Text className='mt-tip'>暂无标签</Text>}
      </ScrollView>
    </View>
  )
}
