import React from 'react'
import { Button, Card, Input, Space, Tag, Typography } from 'antd'
import { BuildOutlined } from '@ant-design/icons'

const { Text } = Typography
const { TextArea } = Input

const StepModelPanel = ({ loading, result, error, schemaScript, onRun }) => {
  const commitResult = result?.schema_commit_result || result?.schema_apply_result || result
  const applyOk = commitResult?.meta?.effective_success !== false && commitResult?.response?.success !== false
  const namespace = result?.kag_schema_export?.namespace || result?.namespace || 'OpenKSNews'
  const schemaSource = result?.schema_source || 'openks_module'

  return (
    <Card title="Step1 建模" size="small" extra={<Button icon={<BuildOutlined />} onClick={onRun} loading={loading}>执行</Button>}>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Text type="secondary">从 OpenKS `news_kg.describe()` 编译 Schema，导出 KAG 项目并提交到 OpenSPG。</Text>
        <TextArea
          rows={8}
          value={schemaScript}
          readOnly
          placeholder="当前会显示已编译的 OpenKS Schema 预览"
        />
        {result ? (
          <Space wrap>
            <Tag color={applyOk ? 'success' : 'error'}>commit: {commitResult?.mode || 'unknown'}</Tag>
            <Tag color="blue">namespace: {namespace}</Tag>
            <Tag color="geekblue">source: {schemaSource}</Tag>
            <Tag color="cyan">activate done</Tag>
          </Space>
        ) : <Tag>尚未执行</Tag>}
        {error ? <Text type="danger">{error}</Text> : null}
      </Space>
    </Card>
  )
}

export default StepModelPanel
