export default {
  // 生产：经网关/域名访问（对应 infra/nginx/dev.conf 的 /api/v1 转发）
  env: {
    API_BASE: 'https://api.ihm.example.com/api/v1',
    AI_BASE: 'https://api.ihm.example.com/ai',
  },
  defineConstants: {},
  mini: {},
  h5: {},
}
