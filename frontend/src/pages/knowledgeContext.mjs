export function parseArtifactContext(searchParams) {
  const params = searchParams instanceof URLSearchParams ? searchParams : new URLSearchParams(searchParams || '')
  const artifactId = String(params.get('artifact_id') || '').trim()
  const artifactVersion = String(params.get('artifact_version') || '').trim()
  return {
    artifactId,
    artifactVersion,
    hasArtifactContext: Boolean(artifactId),
  }
}

export function parseReleaseContext(searchParams) {
  const params = searchParams instanceof URLSearchParams ? searchParams : new URLSearchParams(searchParams || '')
  const releaseId = String(params.get('release_id') || '').trim()
  const releaseVersion = String(params.get('release_version') || '').trim()
  return {
    releaseId,
    releaseVersion,
    hasReleaseContext: Boolean(releaseId),
  }
}
