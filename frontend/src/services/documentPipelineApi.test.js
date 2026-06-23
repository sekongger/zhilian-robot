import { documentPipelineService } from './documentPipelineApi'

test('document pipeline api exists', () => {
  expect(documentPipelineService.getStats).toBeDefined()
})
