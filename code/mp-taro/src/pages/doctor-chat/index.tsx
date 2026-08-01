import { useCallback, useEffect, useRef, useState } from 'react'
import { Button, Input, ScrollView, Switch, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  createPrescription,
  endConsultation,
  getConsultation,
  listMessages,
  sendMessage,
  startConsultation,
  type Consultation,
  type ConsultationMessage,
  type PrescriptionItem,
} from '@/services/ih'

export default function DoctorChat() {
  const id = Number(Taro.getCurrentInstance().router?.params?.id) || 0
  const doctorId = Taro.getStorageSync('doctorId') as number
  const [conv, setConv] = useState<Consultation>()
  const [msgs, setMsgs] = useState<ConsultationMessage[]>([])
  const [text, setText] = useState('')
  const [prescribing, setPrescribing] = useState(false)
  const pollRef = useRef<number>()

  const refresh = useCallback(async () => {
    const c = await getConsultation(id)
    setConv(c)
    const m = await listMessages(id, { page: 1, page_size: 200 })
    setMsgs(m.items)
  }, [id])

  useEffect(() => {
    if (!id) return
    refresh()
    // S6 轮询：4s 拉取患者新消息，会话结束则停止轮询
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

  const onSend = async () => {
    if (!text.trim()) return
    await sendMessage(id, { sender_role: 'doctor', sender_id: doctorId, content: text })
    setText('')
    refresh()
  }

  const onStart = async () => {
    await startConsultation(id, doctorId)
    refresh()
  }
  const onEnd = async () => {
    await endConsultation(id, doctorId)
    refresh()
  }

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', paddingBottom: '80px' }}>
      <View style={{ padding: '14px 16px', background: '#fff' }}>
        <Text style={{ fontSize: '15px', fontWeight: 600 }}>会话 {conv?.consultation_no}</Text>
        <Text style={{ display: 'block', fontSize: '12px', color: '#8c8c8c' }}>
          状态：{conv?.status} · 患者ID {conv?.patient_id}
        </Text>
      </View>

      <ScrollView scrollY style={{ height: '58vh', padding: '12px' }}>
        {msgs.map((m) => {
          const mine = m.sender_role === 'doctor'
          return (
            <View
              key={m.id}
              style={{
                display: 'flex',
                justifyContent: mine ? 'flex-end' : 'flex-start',
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

      {conv?.status === 'open' && (
        <Button type='primary' onClick={onStart}>
          接诊
        </Button>
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
          placeholder='输入回复…'
          style={{ flex: 1, background: '#F5F7FA', borderRadius: '18px', padding: '8px 14px' }}
        />
        <Button size='mini' type='primary' onClick={onSend}>
          发送
        </Button>
        <Button size='mini' onClick={() => setPrescribing(true)}>
          开方
        </Button>
        {conv?.status === 'ongoing' && (
          <Button size='mini' onClick={onEnd} style={{ color: '#FF4D4F', borderColor: '#FF4D4F' }}>
            结束
          </Button>
        )}
      </View>

      {prescribing && (
        <PrescriptionModal
          patientId={conv?.patient_id}
          doctorId={doctorId}
          onClose={() => setPrescribing(false)}
          onDone={() => {
            setPrescribing(false)
            Taro.showToast({ title: '处方已提交审核', icon: 'success' })
          }}
        />
      )}
    </View>
  )
}

function PrescriptionModal({
  patientId,
  doctorId,
  onClose,
  onDone,
}: {
  patientId?: number
  doctorId: number
  onClose: () => void
  onDone: () => void
}) {
  const [diagnose, setDiagnose] = useState('')
  const [items, setItems] = useState<PrescriptionItem[]>([{ name: '', dosage: '', freq: '' }])
  const [signed, setSigned] = useState(false)

  const addItem = () => setItems([...items, { name: '', dosage: '', freq: '' }])
  const updateItem = (i: number, patch: Partial<PrescriptionItem>) =>
    setItems(items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)))

  const submit = async () => {
    const valid = items.filter((it) => it.name)
    if (valid.length === 0) {
      Taro.showToast({ title: '请至少添加一项药品', icon: 'none' })
      return
    }
    if (!signed) {
      Taro.showToast({ title: '请先电子签名确认', icon: 'none' })
      return
    }
    await createPrescription({
      patient_id: patientId as number,
      doctor_id: doctorId,
      diagnose,
      items: valid,
      signature_url: 'signed',
    })
    onDone()
  }

  return (
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
      <View style={{ width: '90%', height: '82vh', background: '#fff', borderRadius: '14px', padding: '16px' }}>
        <Text style={{ fontSize: '16px', fontWeight: 600 }}>开具电子处方</Text>
        <Text style={{ display: 'block', fontSize: '12px', color: '#8c8c8c', margin: '6px 0 10px' }}>
          患者ID {patientId} · 提交后进入药师审核
        </Text>

        <ScrollView scrollY style={{ height: '64vh' }}>
          <Text style={{ fontSize: '13px', color: '#595959' }}>临床诊断</Text>
          <Input
            value={diagnose}
            onInput={(e) => setDiagnose(e.detail.value)}
            placeholder='如：腰椎间盘突出伴坐骨神经痛'
            style={{ background: '#F5F7FA', borderRadius: '8px', padding: '8px 12px', margin: '6px 0 12px' }}
          />

          {items.map((it, i) => (
            <View key={i} style={{ background: '#F5F7FA', borderRadius: '10px', padding: '10px', marginBottom: '10px' }}>
              <Input
                value={it.name}
                onInput={(e) => updateItem(i, { name: e.detail.value })}
                placeholder='药品名称'
                style={{ background: '#fff', borderRadius: '8px', padding: '6px 10px', marginBottom: '6px' }}
              />
              <View style={{ display: 'flex' }}>
                <Input
                  value={it.dosage}
                  onInput={(e) => updateItem(i, { dosage: e.detail.value })}
                  placeholder='用量'
                  style={{ flex: 1, background: '#fff', borderRadius: '8px', padding: '6px 10px', marginRight: '6px' }}
                />
                <Input
                  value={it.freq}
                  onInput={(e) => updateItem(i, { freq: e.detail.value })}
                  placeholder='频次'
                  style={{ flex: 1, background: '#fff', borderRadius: '8px', padding: '6px 10px' }}
                />
              </View>
            </View>
          ))}

          <Button size='mini' onClick={addItem}>
            + 添加药品
          </Button>

          <View style={{ display: 'flex', alignItems: 'center', marginTop: '12px' }}>
            <Text style={{ fontSize: '13px' }}>电子签名确认（已核对无误）</Text>
            <Switch checked={signed} onChange={(e) => setSigned(e.detail.value)} style={{ marginLeft: '12px' }} />
          </View>
        </ScrollView>

        <View style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
          <Button onClick={onClose}>取消</Button>
          <Button type='primary' onClick={submit} style={{ marginLeft: '10px' }}>
            提交处方
          </Button>
        </View>
      </View>
    </View>
  )
}
