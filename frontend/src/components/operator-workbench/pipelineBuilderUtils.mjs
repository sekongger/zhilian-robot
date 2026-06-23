export const buildCustomNode = (operatorName, operatorMap, sequence) => {
  const operator = operatorMap[operatorName]
  const fallbackTitle = operator?.description?.split('，')?.[0] || operatorName
  return {
    key: `custom-${sequence}-${operatorName}`,
    operator: operatorName,
    title: fallbackTitle,
    lane: sequence,
  }
}

export const relaneNodes = (nodes = []) =>
  nodes.map((node, index) => ({
    ...node,
    lane: index,
  }))

export const applyCatalogDrop = ({ operatorName, operatorMap, currentNodes = [], index }) => {
  const nextNodes = [...currentNodes]
  const insertIndex = typeof index === 'number' ? index : nextNodes.length
  nextNodes.splice(insertIndex, 0, buildCustomNode(operatorName, operatorMap, currentNodes.length + 1))
  return relaneNodes(nextNodes)
}

export const moveNode = (nodes, fromIndex, toIndex) => {
  if (fromIndex === toIndex || fromIndex < 0 || fromIndex >= nodes.length) {
    return nodes
  }

  const nextNodes = [...nodes]
  const [moved] = nextNodes.splice(fromIndex, 1)
  const adjustedTarget = fromIndex < toIndex ? toIndex - 1 : toIndex
  nextNodes.splice(adjustedTarget, 0, moved)
  return relaneNodes(nextNodes)
}
