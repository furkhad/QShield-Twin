#!/usr/bin/env node
// Regression check: the browser bundle must never contain the backend API token.
//
// 1. Static guard: client source must not reference a VITE_-prefixed token
//    (Vite would inline it into the public bundle).
// 2. Build the production bundle with a sentinel value placed in both the
//    VITE_-prefixed and the non-VITE token variables, then verify the sentinel
//    does not appear anywhere in the output.
//
// Run with: npm run check:secrets
import { spawnSync } from 'node:child_process'
import { readFileSync, readdirSync, rmSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const srcDir = path.join(root, 'src')
const outDir = path.join(root, '.bundle-secret-check')
const SENTINEL = 'QSHIELD_SENTINEL_8f4c1d2e_do_not_ship'

function walk(dir) {
  const files = []
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry)
    if (statSync(full).isDirectory()) files.push(...walk(full))
    else files.push(full)
  }
  return files
}

// 1. Static guard: client source must not *access* a VITE_-prefixed token
//    (Vite would inline it into the public bundle). A mention in a comment is
//    harmless; `import.meta.env.VITE_...TOKEN` is not.
const forbidden = /import\.meta\.env\.VITE_[A-Z0-9_]*TOKEN/
for (const file of walk(srcDir)) {
  if (forbidden.test(readFileSync(file, 'utf8'))) {
    console.error(
      `FAIL: ${path.relative(root, file)} references a VITE_-prefixed token; ` +
        'Vite would publish it in the browser bundle.',
    )
    process.exit(1)
  }
}

// 2. Build and scan.
rmSync(outDir, { recursive: true, force: true })
const build = spawnSync(
  'npm',
  ['run', 'build', '--', '--outDir', path.relative(root, outDir), '--emptyOutDir'],
  {
    cwd: root,
    stdio: 'inherit',
    env: {
      ...process.env,
      VITE_API_TOKEN: SENTINEL,
      QSHIELD_API_TOKEN: SENTINEL,
    },
  },
)
if (build.status !== 0) {
  console.error('FAIL: production build failed; cannot verify the bundle.')
  process.exit(1)
}

const leaked = []
for (const file of walk(outDir)) {
  if (readFileSync(file).includes(SENTINEL)) leaked.push(path.relative(root, file))
}
rmSync(outDir, { recursive: true, force: true })

if (leaked.length > 0) {
  console.error('FAIL: API token leaked into the production bundle:')
  for (const file of leaked) console.error(`  - ${file}`)
  process.exit(1)
}
console.log('OK: no API token present in the production bundle.')
