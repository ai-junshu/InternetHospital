import { Button, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { loginWx } from '@/services/ih'

export default function Login() {
  const handleLogin = async () => {
    try {
      const { code } = await Taro.login()
      // 未配置 wx_appid/secret 时走开发模式：code 直接作为 openid 标识
      const data = await loginWx(code)
      Taro.setStorageSync('token', data.access_token)
      Taro.setStorageSync('user', data.user)
      Taro.showToast({ title: '登录成功', icon: 'success' })
      try {
        await Taro.navigateBack()
      } catch {
        Taro.reLaunch({ url: '/pages/index/index' })
      }
    } catch (e) {
      // request 已弹 toast
    }
  }

  return (
    <View style={{ padding: '48px 32px', textAlign: 'center' }}>
      <Text style={{ display: 'block', marginBottom: '32px', fontSize: '18px' }}>
        互联网医疗中心平台
      </Text>
      <Button type='primary' onClick={handleLogin}>
        微信一键登录（患者）
      </Button>
      <Button
        style={{ marginTop: '16px' }}
        onClick={() => Taro.navigateTo({ url: '/pages/doctor-workbench/index' })}
      >
        医师工作台（医生）
      </Button>
    </View>
  )
}
