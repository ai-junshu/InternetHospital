import { View, Text, ScrollView, Button, Input } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'
import { useState } from 'react'
import { listCustomers, authorizeCustomer, listStores, type Customer, type Store } from '@/services/mt'

export default function MtCustomers() {
  const [list, setList] = useState<Customer[]>([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [storeId, setStoreId] = useState<number | undefined>(undefined)

  const load = (p = 1) => {
    setLoading(true)
    listCustomers({ page: p, page_size: 20 })
      .then((res) => {
        setList(res.items || [])
        setPage(p)
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '加载失败', icon: 'none' }))
      .finally(() => setLoading(false))
  }

  useLoad(() => {
    load(1)
    // 默认取首个门店作为新建客户的归属门店（否则 source_store_id=NULL 导致 RLS 失效）
    listStores({ page: 1, page_size: 1 })
      .then((r) => { if (r.items && r.items.length) setStoreId(r.items[0].id) })
      .catch(() => {})
  })

  const addCustomer = () => {
    if (!name.trim()) {
      Taro.showToast({ title: '请输入客户姓名', icon: 'none' })
      return
    }
    Taro.showLoading({ title: '提交中' })
    // 简易建客户（门店员工代录，等保三级要求姓名/手机号脱敏存储）
    import('@/services/mt').then(({ createCustomer }) =>
      createCustomer({ name_mask: name.trim(), phone_mask: phone.trim(), source_store_id: storeId })
        .then(() => {
          Taro.showToast({ title: '已创建', icon: 'success' })
          setName('')
          setPhone('')
          load(1)
        })
        .catch((e) => Taro.showToast({ title: (e?.message as string) || '创建失败', icon: 'none' }))
        .finally(() => Taro.hideLoading())
    )
  }

  const goDetail = (c: Customer) => {
    Taro.navigateTo({ url: `/pages/mt/customers/detail?id=${c.id}` })
  }

  const doAuthorize = (c: Customer) => {
    Taro.showLoading({ title: '授权中' })
    authorizeCustomer(c.id)
      .then(() => {
        Taro.showToast({ title: '已授权', icon: 'success' })
        load(page)
      })
      .catch((e) => Taro.showToast({ title: (e?.message as string) || '授权失败', icon: 'none' }))
      .finally(() => Taro.hideLoading())
  }

  return (
    <View className='mt-page'>
      <View className='mt-form'>
        <Input className='mt-input' placeholder='客户姓名（脱敏）' value={name} onInput={(e) => setName(e.detail.value)} />
        <Input className='mt-input' placeholder='手机号（脱敏）' value={phone} onInput={(e) => setPhone(e.detail.value)} />
        <Button className='mt-btn' onClick={addCustomer}>新增客户</Button>
      </View>
      {loading && <Text className='mt-tip'>加载中…</Text>}
      <ScrollView scrollY className='mt-scroll'>
        {list.map((c) => (
          <View className='mt-card' key={c.id} onClick={() => goDetail(c)}>
            <View className='mt-card-row'>
              <Text className='mt-card-title'>#{c.id} {c.name_mask || '匿名客户'}</Text>
              <Text className='mt-tag'>{c.auth_status === 'authorized' ? '已授权' : '未授权'}</Text>
            </View>
            <View className='mt-card-row'>
              <Text className='mt-card-sub'>{c.gender || '-'} · 门店{c.source_store_id ?? '-'}</Text>
              {c.auth_status !== 'authorized' && (
                <Text className='mt-link' onClick={(e) => { e.stopPropagation(); doAuthorize(c) }}>去授权</Text>
              )}
            </View>
          </View>
        ))}
        {!loading && list.length === 0 && <Text className='mt-tip'>暂无客户</Text>}
      </ScrollView>
    </View>
  )
}
