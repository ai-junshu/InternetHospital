import { useState } from 'react'
import { Button, Input, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { createPrescription, type PrescriptionItem, type IhDrug } from '@/services/ih'

export default function DoctorRxCreate() {
  const params = Taro.getCurrentInstance().router?.params || {}
  const patientId = Number(params.patient_id || Taro.getStorageSync('user')?.id || 0)
  const doctorId = Number(params.doctor_id || 0)
  const consultationId = params.consultation_id ? Number(params.consultation_id) : undefined

  const [diagnose, setDiagnose] = useState('')
  const [items, setItems] = useState<PrescriptionItem[]>([
    { name: '', spec: '', dosage: '', freq: '', qty: 1 },
  ])
  const [busy, setBusy] = useState(false)

  const updateItem = (idx: number, patch: Partial<PrescriptionItem>) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)))
  }

  // S4 药品联动：从药品目录选药后回填（drug-catalog?mode=picker 经 Storage 回传）
  Taro.useDidShow(() => {
    const picked = Taro.getStorageSync('picked_drug') as IhDrug | ''
    if (!picked || typeof picked !== 'object') return
    Taro.removeStorageSync('picked_drug')
    const filled: PrescriptionItem = {
      drug_id: picked.id,
      name: picked.name,
      spec: picked.spec || '',
      otc_type: picked.otc_type,
      unit: picked.unit || '',
      price: picked.price || 0,
      qty: 1,
    }
    setItems((prev) => {
      const emptyIdx = prev.findIndex((it) => !it.name.trim())
      if (emptyIdx >= 0) {
        return prev.map((it, i) => (i === emptyIdx ? { ...it, ...filled } : it))
      }
      return [...prev, filled]
    })
    Taro.showToast({ title: `已选：${picked.name}`, icon: 'none' })
  })

  const openDrugPicker = () => {
    Taro.navigateTo({ url: '/pages/drug-catalog/index?mode=picker' })
  }

  const handleSubmit = async () => {
    if (!diagnose.trim()) return Taro.showToast({ title: '请填写诊断', icon: 'none' })
    if (items.some((it) => !it.name.trim())) return Taro.showToast({ title: '请补全药品名称', icon: 'none' })
    setBusy(true)
    try {
      const rx = await createPrescription({
        patient_id: patientId,
        doctor_id: doctorId,
        diagnose,
        items: items.map((it) => ({ ...it, qty: Number(it.qty) || 1 })),
      })
      Taro.showToast({ title: '开方成功，待药师审核', icon: 'success' })
      // 开方后引导患者凭处方下单（处方药凭方购买）
      Taro.navigateTo({ url: `/pages/order/index?prescription_id=${rx.id}&patient_id=${patientId}` })
    } catch {
      // request 已弹 toast
    } finally {
      setBusy(false)
    }
  }

  return (
    <View style={{ padding: '16px', background: '#F5F7FA', minHeight: '100vh' }}>
      <Text style={{ display: 'block', fontSize: '18px', fontWeight: 600, marginBottom: '12px' }}>在线开方</Text>

      <Text style={{ display: 'block', fontSize: '13px', color: '#888', marginBottom: '4px' }}>
        患者ID {patientId} · 医师ID {doctorId}
        {consultationId ? ` · 会话 ${consultationId}` : ''}
      </Text>

      <Button onClick={openDrugPicker} style={{ marginBottom: '12px', background: '#E6F0FF', color: '#1677FF' }}>
        从药品目录选药
      </Button>

      <Input
        placeholder="诊断结论"
        value={diagnose}
        onInput={(e) => setDiagnose(e.detail.value)}
        style={{ background: '#fff', borderRadius: '8px', padding: '10px', marginBottom: '12px' }}
      />

      <Text style={{ display: 'block', fontSize: '14px', marginBottom: '6px' }}>处方明细</Text>
      {items.map((it, idx) => (
        <View
          key={idx}
          style={{ background: '#fff', borderRadius: '10px', padding: '10px', marginBottom: '10px' }}
        >
          <Input placeholder="药品名称" value={it.name} onInput={(e) => updateItem(idx, { name: e.detail.value })} style={rowStyle} />
          <Input placeholder="规格" value={it.spec} onInput={(e) => updateItem(idx, { spec: e.detail.value })} style={rowStyle} />
          <Input placeholder="用法用量" value={it.dosage} onInput={(e) => updateItem(idx, { dosage: e.detail.value })} style={rowStyle} />
          <Input placeholder="频次" value={it.freq} onInput={(e) => updateItem(idx, { freq: e.detail.value })} style={rowStyle} />
          <Input
            placeholder="数量"
            value={String(it.qty ?? 1)}
            onInput={(e) => updateItem(idx, { qty: Number(e.detail.value) || 1 })}
            style={rowStyle}
          />
        </View>
      ))}

      <Button onClick={() => setItems((p) => [...p, { name: '', qty: 1 }])} style={{ marginBottom: '12px' }}>
        + 增加药品
      </Button>

      <Button type="primary" loading={busy} onClick={handleSubmit} style={{ background: '#1677FF' }}>
        提交处方
      </Button>
    </View>
  )
}

const rowStyle: React.CSSProperties = {
  background: '#F5F7FA',
  borderRadius: '6px',
  padding: '8px',
  marginBottom: '6px',
}
