import { PropsWithChildren } from 'react'
import { useLaunch } from '@tarojs/taro'
import Taro from '@tarojs/taro'

import './app.scss'

export default function App({ children }: PropsWithChildren) {
  useLaunch(() => {
    console.log('App launched.')
  })

  // S7 全局登录守卫：启动校验 token，缺失自动跳转登录页
  const token = Taro.getStorageSync('token')
  if (!token) {
    const cur = Taro.getCurrentInstance().router?.path
    if (cur && cur !== '/pages/login/index') {
      Taro.reLaunch({ url: '/pages/login/index' })
    }
  }

  return children
}
