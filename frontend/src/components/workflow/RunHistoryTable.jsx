import React from 'react'
import { Button, Table, Tag } from 'antd'

const STATUS_COLOR = {
  queued: 'default',
  running: 'processing',
  success: 'success',
  failed: 'error',
  partial_success: 'warning',
}

const formatTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString('zh-CN', { hour12: false })
}

const RunHistoryTable = ({ runs, loading, onReplay }) => {
  const columns = [
    { title: 'run_id', dataIndex: 'run_id', key: 'run_id', width: 220 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value) => <Tag color={STATUS_COLOR[value] || 'default'}>{value || '-'}</Tag>,
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 180,
      render: formatTime,
    },
    {
      title: '结束时间',
      dataIndex: 'finished_at',
      key: 'finished_at',
      width: 180,
      render: formatTime,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Button size="small" onClick={() => onReplay(record.run_id)}>回放</Button>
      ),
    },
  ]

  return (
    <Table
      rowKey={(row) => row.run_id}
      loading={loading}
      dataSource={runs || []}
      columns={columns}
      pagination={{ pageSize: 8 }}
      scroll={{ x: 820 }}
    />
  )
}

export default RunHistoryTable
