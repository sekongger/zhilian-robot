import React from 'react'
import { Drawer, Empty, Tabs } from 'antd'

const JsonBlock = ({ data }) => {
  if (!data) return <Empty description="暂无数据" />
  return (
    <pre
      style={{
        margin: 0,
        maxHeight: '70vh',
        overflow: 'auto',
        background: '#f6f9fc',
        border: '1px solid #dbe5ef',
        borderRadius: 8,
        padding: 12,
        fontSize: 12,
        lineHeight: 1.5,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}
    >
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

const ArtifactsDrawer = ({ open, run, onClose }) => {
  const items = [
    { key: 'request', label: 'request', children: <JsonBlock data={run?.request} /> },
    { key: 'steps', label: 'step_statuses', children: <JsonBlock data={run?.step_statuses} /> },
    { key: 'warnings', label: 'warnings', children: <JsonBlock data={run?.warnings} /> },
    { key: 'ingest', label: 'ingest_result', children: <JsonBlock data={run?.ingest_result} /> },
    { key: 'bridge', label: 'bridge_run', children: <JsonBlock data={run?.bridge_run} /> },
    { key: 'schema', label: 'schema_apply', children: <JsonBlock data={run?.schema_apply_result} /> },
    { key: 'builder', label: 'builder_submit', children: <JsonBlock data={run?.builder_submit_result} /> },
    { key: 'headlines', label: 'headlines_snapshot', children: <JsonBlock data={run?.headlines_snapshot} /> },
  ]

  return (
    <Drawer
      title="阶段产物详情"
      open={open}
      onClose={onClose}
      width={880}
      destroyOnClose
    >
      <Tabs defaultActiveKey="request" items={items} />
    </Drawer>
  )
}

export default ArtifactsDrawer
