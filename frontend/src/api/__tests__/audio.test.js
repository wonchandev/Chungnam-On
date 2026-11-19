import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'

const source = readFileSync(new URL('../../../public/audio/pcm-recorder.js', import.meta.url), 'utf8')
function recorder(sampleRate) {
  const frames = []
  let Processor
  vm.runInNewContext(source, {
    sampleRate,
    AudioWorkletProcessor: class { constructor() { this.port = { postMessage: buffer => frames.push(buffer) } } },
    registerProcessor: (name, implementation) => { assert.equal(name, 'pcm-recorder'); Processor = implementation },
  })
  return { processor: new Processor(), frames }
}
test('streams 48kHz audio as backend-compatible 20ms mono PCM16 little-endian frames', () => {
  const { processor, frames } = recorder(48000)
  // AudioWorklet supplies blocks of 128 samples, including across frame boundaries.
  for (let block = 0; block < 15; block++) processor.process([[new Float32Array(128).fill(.5)]])
  assert.equal(frames.length, 2)
  for (const frame of frames) {
    assert.equal(frame.byteLength, 640)
    assert.equal(new DataView(frame).getInt16(0, true), 16384)
    assert.equal(new DataView(frame).getInt16(638, true), 16384)
  }
})
test('mixes stereo into mono and clips peaks to signed PCM16 range', () => {
  const { processor, frames } = recorder(16000)
  processor.process([[new Float32Array(320).fill(1), new Float32Array(320).fill(-1)]])
  assert.equal(new DataView(frames[0]).getInt16(0, true), 0)
  processor.process([[new Float32Array(320).fill(2)]])
  assert.equal(new DataView(frames[1]).getInt16(0, true), 32767)
  processor.process([[new Float32Array(320).fill(-2)]])
  assert.equal(new DataView(frames[2]).getInt16(0, true), -32768)
})
