import React from 'react'
import { Button, Card, Checkbox, Col, Input, InputNumber, Row, Space, Tag, Tooltip, Typography } from 'antd'
import { PlayCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import { ADVANCED_PARAM_KEYS, PARAM_META } from './workflowParamMeta.mjs'

const { Text } = Typography

const GlobalRunControlBar = ({
  params,
  running,
  onChange,
  onRun,
}) => {
  const [showAdvanced, setShowAdvanced] = React.useState(false)

  const renderLabel = (key, extra) => (
    <Space size={4}>
      <Text type="secondary">{PARAM_META[key].label}</Text>
      <Tooltip title={PARAM_META[key].help}>
        <QuestionCircleOutlined style={{ color: '#7b8aa0' }} />
      </Tooltip>
      {extra}
    </Space>
  )

  return (
    <Card>
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Space align="center" wrap>
          <Text type="secondary">主入口固定使用 `kag_openspg` 主链，常规运行直接使用默认参数即可。</Text>
          <Tag color="blue">kag_openspg 主链</Tag>
        </Space>

      <Row gutter={[12, 12]} align="middle">
        <Col xs={12} md={8} lg={4}>
          {renderLabel('hours_ago', <Text type="secondary">默认 {PARAM_META.hours_ago.defaultValue}{PARAM_META.hours_ago.unit}</Text>)}
          <InputNumber
            style={{ width: '100%' }}
            min={1}
            max={168}
            value={params.hours_ago}
            onChange={(value) => onChange('hours_ago', value || 24)}
          />
        </Col>

        <Col xs={12} md={8} lg={4}>
          {renderLabel('max_entries_per_feed', <Text type="secondary">默认 {PARAM_META.max_entries_per_feed.defaultValue}</Text>)}
          <InputNumber
            style={{ width: '100%' }}
            min={1}
            max={50}
            value={params.max_entries_per_feed}
            onChange={(value) => onChange('max_entries_per_feed', value || 5)}
          />
        </Col>

        <Col xs={12} md={8} lg={4}>
          {renderLabel('bridge_limit', <Text type="secondary">默认 {PARAM_META.bridge_limit.defaultValue}</Text>)}
          <InputNumber
            style={{ width: '100%' }}
            min={1}
            max={5000}
            value={params.bridge_limit}
            onChange={(value) => onChange('bridge_limit', value || 200)}
          />
        </Col>

        <Col xs={12} md={8} lg={3}>
          {renderLabel('headlines_top_n', <Text type="secondary">默认 {PARAM_META.headlines_top_n.defaultValue}</Text>)}
          <InputNumber
            style={{ width: '100%' }}
            min={1}
            max={100}
            value={params.headlines_top_n}
            onChange={(value) => onChange('headlines_top_n', value || 20)}
          />
        </Col>

        <Col xs={24} md={24} lg={24}>
          <Space wrap>
            <Checkbox
              checked={params.submit_builder}
              onChange={(e) => onChange('submit_builder', e.target.checked)}
            >
              <Tooltip title={PARAM_META.submit_builder.help}>{PARAM_META.submit_builder.label}</Tooltip>
            </Checkbox>
            <Checkbox
              checked={params.apply_schema}
              onChange={(e) => onChange('apply_schema', e.target.checked)}
            >
              <Tooltip title={PARAM_META.apply_schema.help}>{PARAM_META.apply_schema.label}</Tooltip>
            </Checkbox>
            <Checkbox
              checked={params.force_full}
              onChange={(e) => onChange('force_full', e.target.checked)}
            >
              <Tooltip title={PARAM_META.force_full.help}>{PARAM_META.force_full.label}</Tooltip>
            </Checkbox>
            <Button type="link" onClick={() => setShowAdvanced((prev) => !prev)} style={{ paddingInline: 0 }}>
              {showAdvanced ? '收起高级参数' : '显示高级参数'}
            </Button>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={onRun} loading={running}>
              一键运行
            </Button>
          </Space>
        </Col>
      </Row>

      {showAdvanced ? (
        <Row gutter={[12, 12]} style={{ marginTop: 4 }}>
          {ADVANCED_PARAM_KEYS.includes('project_id') ? (
            <Col xs={24} md={8} lg={5}>
              {renderLabel('project_id', <Text type="secondary">默认 {PARAM_META.project_id.defaultValue}</Text>)}
              <InputNumber
                style={{ width: '100%' }}
                min={1}
                value={params.project_id}
                onChange={(value) => onChange('project_id', value || 1)}
              />
            </Col>
          ) : null}
          {ADVANCED_PARAM_KEYS.includes('builder_command') ? (
            <Col xs={24} md={16} lg={9}>
              {renderLabel('builder_command', <Text type="secondary">可留空</Text>)}
              <Input
                value={params.builder_command}
                onChange={(e) => onChange('builder_command', e.target.value)}
                placeholder="默认使用后端命令"
              />
            </Col>
          ) : null}
        </Row>
      ) : null}
      </Space>
    </Card>
  )
}

export default GlobalRunControlBar
