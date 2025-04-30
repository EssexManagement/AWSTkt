import * as esbuild from 'esbuild'

await esbuild.build({
platform: 'node',
  target: 'ES2022',
  entryPoints: ['src/handlers/SleepRandom.ts'],
  bundle: true,
  outfile: 'dist/index.js',
})
