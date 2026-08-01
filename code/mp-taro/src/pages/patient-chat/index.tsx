import { useCallback, useEffect, useRef, useState } from 'react'
import { Button, Input, ScrollView, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  endConsultation,
  getConsultation,
  listMessages,
  sendMessage,
  type Consultation,
  type ConsultationMessage,
} from '@/services/ih'

const STATUS_TEXT: Record<string, string> = {
  open: '等待医师接诊',
  ongoing: '问诊中',
  ended: '问诊已结束',
}

export default function PatientChat() {
  const id = Number(Taro.getCurrentInstance().router?.params?.id) || 0
  const patientId = Taro.getStorageSync('patientId') as number
  const [conv, setConv] = useState<Consultation>()
  const [msgs, setMsgs] = useState<ConsultationMessage[]>([])
  const [text, setText] = useState('')
  const pollRef = useRef<number>()

  const refresh = useCallback(async () => {
    if (!id) return
    const c = await getConsultation(id)
    setConv(c)
    const m = await listMessages(id, { page: 1, page_size: 200 })
    setMsgs(m.items)
  }, [id])

  const onSend = async () => {
    if (!text.trim() || conv?.status === 'ended' || conv?.status === 'open') return
    await sendMessage(id, { sender_role: 'patient', sender_id: patientId, content: text })
    setText('')
    refresh()
  }

  const onEnd = async () => {
    await endConsultation(id, patientId)
    refresh()
  }

  useEffect(() => {
    refresh()
    // S6 轮询：4s 拉取医师新消息，会话结束则停止
    pollRef.current = setInterval(async () => {
      const c = await getConsultation(id).catch(() => null)
      if (c?.status === 'ended') {
        if (pollRef.current) clearInterval(pollRef.current)
        setConv(c)
      }
      const m = await listMessages(id, { page: 1, page_size: 200 }).catch(() => null)
      if (m) setMsgs(m.items)
    }, 4000) as unknown as number
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [id, refresh])

  const ended = conv?.status === 'ended'
  const waiting = conv?.status === 'open'

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', paddingBottom: '80px' }}>
      <View style={{ padding: '14px 16px', background: '#fff' }}>
        <Text style={{ fontSize: '15px', fontWeight: 600 }}>会话 {conv?.consultation_no}</Text>
        <Text style={{ display: 'block', fontSize: '12px', color: '#8c8c8c' }}>
          状态：{STATUS_TEXT[conv?.status || ''] || conv?.status} · 医师ID {conv?.doctor_id}
        </Text>
      </View>

      <ScrollView scrollY style={{ height: '58vh', padding: '12px' }}>
        {msgs.map((m) => {
          const mine = m.sender_role === 'patient'
          return (
            <View
              key={m.id}
              style={{
                display: 'flex',
                justifyContent: mine ? 'flex-start' : 'flex-end',
                marginBottom: '10px',
              }}
            >
              <View
                style={{
                  maxWidth: '75%',
                  background: mine ? '#1677FF' : '#fff',
                  color: mine ? '#fff' : '#1f1f1f',
                  padding: '10px 12px',
                  borderRadius: '12px',
                }}
              >
                <Text style={{ fontSize: '14px' }}>{m.content}</Text>
              </View>
            </View>
          )
        })}
      </ScrollView>

      {waiting && (
        <View style={{ padding: '10px 16px', background: '#FFF7E6' }}>
          <Text style={{ fontSize: '13px', color: '#FA8C16' }}>已提交，请耐心等待医师接诊…</Text>
        </View>
      )}

      <View
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          background: '#fff',
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        <Input
          value={text}
          onInput={(e) => setText(e.detail.value)}
          placeholder={ended ? '问诊已结束' : waiting ? '等待接诊中…' : '输入消息…'}
          disabled={ended || waiting}
          style={{ flex: 1, background: '#F5F7FA', borderRadius: '18px', padding: '8px 14px' }}
        />
        <Button
          size='mini'
          type='primary'
          onClick={onSend}
          disabled={ended || waiting}
        >
          发送
        </Button>
        {conv?.status === 'ongoing' && (
          <Button size='mini' onClick={onEnd} style={{ color: '#FF4D4F', borderColor: '#FF4D4F', marginLeft: '6px' }}>
            结束
          </Button>
        )}
      </View>
    </View>
  )
}
