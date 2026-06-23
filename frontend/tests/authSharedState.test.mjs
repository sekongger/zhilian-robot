import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const authPath = path.resolve(__dirname, '../src/utils/auth.js')

test('auth utility persists shared login state across quant-chi subdomains', () => {
  const source = fs.readFileSync(authPath, 'utf8')

  assert.match(source, /document\.cookie/)
  assert.match(source, /quant-chi\.com/)
  assert.match(source, /SameSite=Lax/)
  assert.match(source, /getAuth/)
  assert.match(source, /login/)
})
