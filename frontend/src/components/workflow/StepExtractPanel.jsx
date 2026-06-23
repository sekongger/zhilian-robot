import React from 'react'
import { Button, Card, Space, Statistic, Tag, Typography } from 'antd'
import { BranchesOutlined } from '@ant-design/icons'

const { Text } = Typography

const StepExtractPanel = ({ loading, result, error, onRun }) => {
  const runtimeProfile = result?.runtime_profile || result?.meta?.runtime_profile || 'kag_openspg'

  return (
    <Card title="Step4 抽取" size="small" extra={<Button icon={<BranchesOutlined />} onClick={onRun} loading={loading}>执行</Button>}>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Text type="secondary">执行 KAG bridge 导出，生成待写入 OpenSPG 的批次与对象映射预览。</Text>
        {result ? (
          <Space wrap>
            <Statistic
              title="导出条数"
              value={result.export_count || 0}
              valueStyle={{ fontSize: 18 }}
            />
            <Tag color="processing">{`run_id: ${result.run_id || '-'}`}</Tag>
            <Tag color="blue">{runtimeProfile}</Tag>
          </Space>
        ) : <Tag>尚未执行</Tag>}
        {error ? <Text type="danger">{error}</Text> : null}
      </Space>
    </Card>
  )
}

export default StepExtractPanel
