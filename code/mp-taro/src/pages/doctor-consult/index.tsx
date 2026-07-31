import { useState } from 'react'
import { Button, Input, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  createConsultation,
  listMessages,
  sendMessage,
  type Consultation,
  type ConsultationMessage,
} from '@/services/ih'

export default function DoctorConsult() {
  const [patientId, setPatientId] = useState('')
  const [doctorId, setDoctorId] = useState('')
  const [complaint, setComplaint] = useState('')
  const [consult, setConsult] = useState<Consultation>()
  const [messages, setMessages] = useState<ConsultationMessage[]>([])
  const [draft, setDraft] = useState('')

  const refreshMessages = async (id: number) => {
    const res = await listMessages(id, { page: 1, page_size: 100 })
    setMessages(res.items)
  }

  const handleCreate = async () => {
    try {
      const c = await createConsultation({
        patient_id: Number(patientId),
        doctor_id: Number(doctorId),
        chief_complaint: complaint,
      })
      setConsult(c)
      await refreshMessages(c.id)
      Taro.showToast({ title: '会话已创建', icon: 'success' })
    } catch (e) {
      // request 已弹 toast
    }
  }

  const handleSend = async () => {
    if (!consult || !draft.trim()) return
    await sendMessage(consult.id, {
      sender_role: 'patient',
      sender_id: Number(patientId),
      content: draft,
    })
    setDraft('')
    await refreshMessages(consult.id)
  }

  return (
    <View style={{ padding: '16px' }}>
      <Text style={{ display: 'block', marginBottom: '8px' }}>在线复诊（图文沟通）</Text>

      {!consult ? (
        <View>
          <Input placeholder='患者ID' value={patientId} onInput={(e) => setPatientId(e.detail.value)} />
          <Input placeholder='医师ID' value={doctorId} onInput={(e) => setDoctorId(e.detail.value)} />
          <Input placeholder='主诉' value={complaint} onInput={(e) => setComplaint(e.detail.value)} />
          <Button type='primary' onClick={handleCreate}>
            创建会话
          </Button>
        </View>
      ) : (
        <View>
          <Text style={{ display: 'block', margin: '8px 0', color: '#888' }}>
            会话号 {consult.consultation_no} · 状态 {consult.status}
          </Text>
          <View style={{ background: '#f5f5f5', padding: '8px', borderRadius: '8px', minHeight: '120px' }}>
            {messages.map((m) => (
              <View key={m.id} style={{ margin: '4px 0' }}>
                <Text>
                  [{m.sender_role}] {m.content}
                </Text>
              </View>
            ))}
            {messages.length === 0 && <Text style={{ color: '#aaa' }}>暂无消息</Text>}
          </View>
          <Input placeholder='输入消息' value={draft} onInput={(e) => setDraft(e.detail.value)} />
          <Button type='primary' onClick={handleSend}>
            发送
          </Button>
          <Button
            style={{ marginTop: '8px' }}
            onClick={() =>
              Taro.navigateTo({
                url: `/pages/doctor-rx-create/index?patient_id=${patientId}&doctor_id=${doctorId}&consultation_id=${consult?.id || ''}`,
              })
            }
          >
            结束问诊并开方
          </Button>
        </View>
      )}
    </View>
  )
}
