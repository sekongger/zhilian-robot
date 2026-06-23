import React, { useState } from 'react'
import { Card, Form, Input, Button, Typography, message } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import { login, isAuthenticated } from '../utils/auth'

const { Title, Text } = Typography

const LoginPage = () => {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/news-pipeline'

  React.useEffect(() => {
    if (isAuthenticated()) {
      navigate('/news-pipeline', { replace: true })
    }
  }, [navigate])

  const handleSubmit = async (values) => {
    setLoading(true)
    try {
      const ok = login(values.username, values.password)
      if (!ok) {
        message.error('用户名或密码错误')
        return
      }
      message.success('登录成功')
      navigate(from, { replace: true })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#0f172a', padding: 24 }}>
      <Card style={{ width: 380, background: '#1e293b', border: '1px solid #334155' }}>
        <Title level={3} style={{ marginTop: 0, color: '#e2e8f0' }}>
          浙大AI产业知识中心实验平台
        </Title>
        <Text type="secondary">请输入账号密码继续访问</Text>
        <Form layout="vertical" style={{ marginTop: 16 }} onFinish={handleSubmit}>
          <Form.Item name="username" label={<Text style={{ color: '#94a3b8' }}>用户名</Text>} rules={[{ required: true, message: '请输入用户名' }]}>
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" label={<Text style={{ color: '#94a3b8' }}>密码</Text>} rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  )
}

export default LoginPage
