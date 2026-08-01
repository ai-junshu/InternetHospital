import { useCallback, useEffect, useState } from 'react'
import { Button, Input, ScrollView, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  createConsultation,
  getDoctors,
  listPatientConsultations,
  type Consultation,
  type Doctor,
} from '@/services/ih'

const STATUS_TEXT: Record<string, string> = {
  open: '等待接诊',
  ongoing: '问诊中',
  ended: '已结束',
}
const STATUS_COLOR: Record<string, string> = {
  open: '#FA8C16',
  ongoing: '#1677FF',
  ended: '#8c8c8c',
}

export default function PatientConsultList() {
  const patientId = Taro.getStorageSync('patientId') as number
  const [list, setList] = useState<Consultation[]>([])
  const [loading, setLoading] = useState(false)
  const [showPicker, setShowPicker] = useState(false)
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [picked, setPicked] = useState<number>()
  const [complaint, setComplaint] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const refresh = useCallback(async () => {
    if (!patientId) return
    setLoading(true)
    try {
      const r = await listPatientConsultations({ patient_id: patientId, page: 1, page_size: 20 })
      setList(r.items)
    } finally {
      setLoading(false)
    }
  }, [patientId])

  useEffect(() => {
    refresh()
  }, [refresh])

  const openPicker = async () => {
    const r = await getDoctors({ page: 1, page_size: 20 })
    setDoctors(r.items)
    setPicked(undefined)
    setComplaint('')
    setShowPicker(true)
  }

  const onStart = async () => {
    if (!picked) {
      Taro.showToast({ title: '请选择医师', icon: 'none' })
      return
    }
    setSubmitting(true)
    try {
      const c = await createConsultation({
        patient_id: patientId,
        doctor_id: picked,
        chief_complaint: complaint || '在线复诊咨询',
      })
      setShowPicker(false)
      Taro.navigateTo({ url: `/pages/patient-chat/index?id=${c.id}` })
    } finally {
      setSubmitting(false)
    }
  }

  const goChat = (id: number) => Taro.navigateTo({ url: `/pages/patient-chat/index?id=${id}` })

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', padding: '12px' }}>
      <View
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
        }}
      >
        <Text style={{ fontSize: '20px', fontWeight: 600 }}>我的问诊</Text>
        <Button size='mini' type='primary' onClick={openPicker}>
          发起复诊
        </Button>
      </View>

      {loading && <Text style={{ color: '#8c8c8c', fontSize: '13px' }}>加载中…</Text>}

      {!loading && list.length === 0 && (
        <View
          style={{
            marginTop: '60px',
            textAlign: 'center',
            color: '#8c8c8c',
          }}
        >
          <Text style={{ fontSize: '14px' }}>暂无问诊记录，点击右上角发起复诊</Text>
        </View>
      )}

      <ScrollView scrollY style={{ maxHeight: '82vh' }}>
        {list.map((c) => (
          <View
            key={c.id}
            onClick={() => goChat(c.id)}
            style={{
              background: '#fff',
              borderRadius: '12px',
              padding: '14px',
              marginBottom: '10px',
            }}
          >
            <View style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={{ fontSize: '15px', fontWeight: 500 }}>医师 #{c.doctor_id}</Text>
              <Text style={{ fontSize: '12px', color: STATUS_COLOR[c.status] || '#8c8c8c' }}>
                {STATUS_TEXT[c.status] || c.status}
              </Text>
            </View>
            <Text
              style={{
                display: 'block',
                fontSize: '13px',
                color: '#595959',
                marginTop: '6px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              主诉：{c.chief_complaint}
            </Text>
            <Text style={{ display: 'block', fontSize: '12px', color: '#bfbfbf', marginTop: '4px' }}>
              会话号 {c.consultation_no}
            </Text>
          </View>
        ))}
      </ScrollView>

      {showPicker && (
        <View
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.45)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <View style={{ width: '90%', height: '80vh', background: '#fff', borderRadius: '14px', padding: '16px' }}>
            <Text style={{ fontSize: '16px', fontWeight: 600 }}>发起复诊</Text>
            <Text style={{ display: 'block', fontSize: '12px', color: '#8c8c8c', margin: '6px 0 10px' }}>
              选择医师并描述主诉
            </Text>

            <ScrollView scrollY style={{ height: '46vh' }}>
              {doctors.map((d) => (
                <View
                  key={d.id}
                  onClick={() => setPicked(d.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '10px 12px',
                    borderRadius: '10px',
                    marginBottom: '8px',
                    background: picked === d.id ? '#E6F0FF' : '#F5F7FA',
                    border: picked === d.id ? '1px solid #1677FF' : '1px solid transparent',
                  }}
                >
                  <Text style={{ fontSize: '14px', fontWeight: 500 }}>医师 #{d.id}</Text>
                  <Text style={{ fontSize: '12px', color: '#8c8c8c', marginLeft: '10px' }}>
                    {d.dept} · {d.title}
                  </Text>
                </View>
              ))}
            </ScrollView>

            <Text style={{ fontSize: '13px', color: '#595959', marginTop: '8px' }}>主诉</Text>
            <Input
              value={complaint}
              onInput={(e) => setComplaint(e.detail.value)}
              placeholder='如：腰部酸痛反复，想复诊开方'
              style={{ background: '#F5F7FA', borderRadius: '8px', padding: '8px 12px', marginTop: '6px' }}
            />

            <View style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '14px' }}>
              <Button onClick={() => setShowPicker(false)}>取消</Button>
              <Button type='primary' onClick={onStart} loading={submitting} style={{ marginLeft: '10px' }}>
                发起问诊
              </Button>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
