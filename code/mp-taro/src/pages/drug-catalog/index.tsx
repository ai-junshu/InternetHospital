import { useEffect, useState } from 'react'
import { Input, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { listDrugs, type IhDrug } from '@/services/ih'

export default function DrugCatalog() {
  const [kw, setKw] = useState('')
  const [list, setList] = useState<IhDrug[]>([])
  const [loading, setLoading] = useState(false)

  const load = async (keyword = '') => {
    setLoading(true)
    try {
      const res = await listDrugs({ keyword, page: 1, page_size: 50 })
      setList(res.items)
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

  return (
    <View style={{ minHeight: '100vh', background: '#F5F7FA', padding: '12px' }}>
      <Text
        style={{
          display: 'block',
          fontSize: '18px',
          fontWeight: 600,
          margin: '4px 4px 12px',
        }}
      >
        药品目录
      </Text>
      <View
        style={{
          background: '#fff',
          borderRadius: '10px',
          padding: '8px 12px',
          marginBottom: '12px',
        }}
      >
        <Input
          value={kw}
          placeholder='搜索药品名称'
          onInput={(e) => setKw(e.detail.value)}
          onConfirm={() => load(kw)}
          style={{ fontSize: '14px' }}
        />
      </View>
      {!loading && list.length === 0 && (
        <Text
          style={{
            display: 'block',
            textAlign: 'center',
            color: '#aaa',
            marginTop: '40px',
          }}
        >
          未找到药品
        </Text>
      )}
      {list.map((d) => (
        <View
          key={d.id}
          style={{
            background: '#fff',
            borderRadius: '12px',
            padding: '14px',
            marginBottom: '10px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
          }}
        >
          <View style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text style={{ fontSize: '15px', fontWeight: 500 }}>{d.name}</Text>
            <Text
              style={{
                fontSize: '13px',
                color: d.status === 'on' ? '#52C41A' : '#bbb',
              }}
            >
              {d.status === 'on' ? '在售' : '下架'}
            </Text>
          </View>
          <Text
            style={{
              display: 'block',
              color: '#8C8C8C',
              fontSize: '12px',
              marginTop: '4px',
            }}
          >
            {[d.spec, d.manufacturer, d.category].filter(Boolean).join(' · ') || '—'}
          </Text>
          <Text style={{ display: 'block', fontSize: '13px', marginTop: '6px' }}>
            {d.otc_type === 'rx' ? '处方药' : 'OTC'} · {d.unit || '—'} · ￥
            {((d.price || 0) / 100).toFixed(2)}
          </Text>
        </View>
      ))}
    </View>
  )
}
