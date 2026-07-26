import { useEffect, useState } from 'react'
import { Button, Switch, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  listDoctorSchedules,
  createDoctorSchedule,
  deleteDoctorSchedule,
  type DoctorSchedule,
} from '@/services/ih'

const DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const SLOTS = ['上午', '下午', '晚上'] as const
type Slot = (typeof SLOTS)[number]

const SLOT_TO_AM: Record<Slot, string> = {
  上午: 'morning',
  下午: 'afternoon',
  晚上: 'evening',
}
const AM_TIME: Record<string, [string, string]> = {
  morning: ['08:00', '12:00'],
  afternoon: ['14:00', '18:00'],
  evening: ['19:00', '22:00'],
}

// 周一=1 .. 周日=7
function weekdayOf(dateStr: string): number {
  const [y, m, d] = dateStr.split('-').map(Number)
  return ((new Date(y, m - 1, d).getDay() + 6) % 7) + 1
}

function nextDate(weekday: number, weeksAhead = 0): string {
  const now = new Date()
  const todayDow = (now.getDay() + 6) % 7
  const target = weekday - 1
  let diff = (target - todayDow + 7) % 7
  if (diff === 0) diff = 7
  const dt = new Date(now)
  dt.setDate(now.getDate() + diff + weeksAhead * 7)
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const day = String(dt.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function keyOf(weekday: number, am: string) {
  return `${weekday}-${am}`
}

export default function DoctorSchedule() {
  const [records, setRecords] = useState<DoctorSchedule[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await listDoctorSchedules({ page: 1, page_size: 200 })
      setRecords(res.items)
    } catch {
      // request 拦截器已统一提示
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const isOn = (weekday: number, slot: Slot) =>
    records.some(
      (r) => weekdayOf(r.work_date) === weekday && r.am_pm === SLOT_TO_AM[slot],
    )

  const toggle = (weekday: number, am: string) => {
    if (saving) return
    setRecords((prev) => {
      const exists = prev.some(
        (r) => weekdayOf(r.work_date) === weekday && r.am_pm === am,
      )
      if (exists) {
        return prev.filter(
          (r) => !(weekdayOf(r.work_date) === weekday && r.am_pm === am),
        )
      }
      const [st, et] = AM_TIME[am]
      return [
        ...prev,
        {
          id: -Date.now(),
          doctor_id: 0,
          work_date: nextDate(weekday, 0),
          am_pm: am,
          start_time: st,
          end_time: et,
          status: 'open',
          capacity: 1,
        } as DoctorSchedule,
      ]
    })
  }

  const save = async () => {
    setSaving(true)
    try {
      // 删除被取消的已有记录
      await Promise.all(
        records
          .filter((r) => r.id > 0)
          .map((r) => deleteDoctorSchedule(r.id).catch(() => null)),
      )
      // 重新提交当前开启的时段（未来 4 周）
      const planned: Promise<unknown>[] = []
      DAYS.forEach((_, wi) => {
        const weekday = wi + 1
        SLOTS.forEach((slot) => {
          if (isOn(weekday, slot)) {
            const am = SLOT_TO_AM[slot]
            const [st, et] = AM_TIME[am]
            for (let w = 0; w < 4; w++) {
              planned.push(
                createDoctorSchedule({
                  work_date: nextDate(weekday, w),
                  am_pm: am,
                  start_time: st,
                  end_time: et,
                }).catch(() => null),
              )
            }
          }
        })
      })
      await Promise.all(planned)
      await load()
      Taro.showToast({ title: '已同步云端', icon: 'success' })
    } catch {
      // request 拦截器已统一提示
    } finally {
      setSaving(false)
    }
  }

  const count = DAYS.reduce(
    (acc, _, wi) => acc + SLOTS.filter((s) => isOn(wi + 1, s)).length,
    0,
  )

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', padding: '16px' }}>
      <Text style={{ fontSize: '17px', fontWeight: 600 }}>我的排班</Text>
      <Text
        style={{
          display: 'block',
          fontSize: '12px',
          color: '#8c8c8c',
          marginTop: '4px',
        }}
      >
        设置可接诊时段（共 {count} 个时段）· 已接入后端排班接口
      </Text>

      <View
        style={{
          marginTop: '16px',
          background: '#fff',
          borderRadius: '12px',
          padding: '8px 4px',
        }}
      >
        <View style={{ display: 'flex', borderBottom: '1px solid #f0f0f0' }}>
          <View style={{ width: '60px' }} />
          {SLOTS.map((s) => (
            <View
              key={s}
              style={{
                flex: 1,
                textAlign: 'center',
                padding: '8px 0',
                fontSize: '13px',
                color: '#595959',
              }}
            >
              <Text>{s}</Text>
            </View>
          ))}
        </View>
        {DAYS.map((d, wi) => (
          <View
            key={d}
            style={{
              display: 'flex',
              alignItems: 'center',
              borderBottom: '1px solid #f5f5f5',
            }}
          >
            <View
              style={{
                width: '60px',
                padding: '12px 0',
                fontSize: '14px',
              }}
            >
              <Text>{d}</Text>
            </View>
            {SLOTS.map((s) => (
              <View
                key={s}
                style={{ flex: 1, textAlign: 'center', padding: '10px 0' }}
              >
                <Switch
                  checked={isOn(wi + 1, s)}
                  onChange={() => toggle(wi + 1, SLOT_TO_AM[s])}
                />
              </View>
            ))}
          </View>
        ))}
      </View>

      <Button type='primary' loading={saving} onClick={save} style={{ marginTop: '20px' }}>
        {saving ? '同步中…' : '保存排班'}
      </Button>
    </View>
  )
}
