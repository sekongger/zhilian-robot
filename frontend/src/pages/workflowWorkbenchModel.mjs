export function buildNewsKgWorkbenchModel(payload = {}) {
  const queue = payload?.queue || {}
  const latestRun = payload?.latest_run || payload?.latestRun || {}

  return {
    kgName: payload?.kg_name || 'news_kg',
    pending: Number(queue?.pending || 0),
    running: Number(queue?.running || 0),
    failed: Number(queue?.failed || 0),
    completed: Number(queue?.completed || 0),
    latestRunId: latestRun?.run_id || '',
    latestRunStatus: latestRun?.status || 'idle',
    latestProcessed: Number(latestRun?.processed || 0),
    latestStatementsWritten: Number(latestRun?.statements_written || 0),
  }
}
