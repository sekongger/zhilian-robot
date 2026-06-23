import React from 'react'
import { Button, Card, Space, Tag, Typography } from 'antd'
import { RocketOutlined } from '@ant-design/icons'

const { Text } = Typography

const StepExecutePanel = ({ loading, result, error, onRun }) => {
  const runtimeProfile = result?.runtime_profile || 'kag_openspg'
  const builderResult = result?.builder_submit_result || result
  const builderOk = builderResult?.meta?.effective_success !== false && builderResult?.response?.success !== false
  const builderColor = builderResult?.mode === 'skip' ? 'default' : builderOk ? 'success' : 'error'
  const runtimeBinding = result?.runtime_binding || {}

  return (
    <Card title="Step5 执行" size="small" extra={<Button icon={<RocketOutlined />} onClick={onRun} loading={loading}>执行</Button>}>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Text type="secondary">提交 Builder 任务并执行图物化，回收统一的 Run / Artifact / Release 绑定对象。</Text>
        {result ? (
          <Space wrap>
            <Tag color="processing">{`job_id: ${builderResult?.job_id || '-'}`}</Tag>
            <Tag color={builderColor}>{`builder: ${builderResult?.mode || 'unknown'}`}</Tag>
            <Tag color="blue">{`artifact: ${(runtimeBinding?.artifact || {}).artifact_id || '-'}`}</Tag>
            <Tag color="cyan">{`release: ${(runtimeBinding?.release || {}).release_id || '-'}`}</Tag>
            <Tag color="purple">{`bridge_run: ${result?.bridge_last_run?.run_id || result?.run_id || '-'}`}</Tag>
          </Space>
        ) : <Tag>尚未执行</Tag>}
        {error ? <Text type="danger">{error}</Text> : null}
      </Space>
    </Card>
  )
}

export default StepExecutePanel
