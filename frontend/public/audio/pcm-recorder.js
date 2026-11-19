class PcmRecorder extends AudioWorkletProcessor {
  constructor() { super(); this.position = 0; this.samples = [] }
  process(inputs) {
    const channels = inputs[0]
    if (!channels?.[0]) return true
    for (let index = 0; index < channels[0].length; index++) {
      this.position += 16000
      if (this.position < sampleRate) continue
      this.position -= sampleRate
      let sample = 0
      for (const channel of channels) sample += channel[index] / channels.length
      sample = Math.max(-1, Math.min(1, sample))
      this.samples.push(Math.round(sample * (sample < 0 ? 32768 : 32767)))
      if (this.samples.length === 320) {
        const buffer = new ArrayBuffer(640)
        const view = new DataView(buffer)
        this.samples.forEach((value, offset) => view.setInt16(offset * 2, value, true))
        this.port.postMessage(buffer, [buffer]); this.samples = []
      }
    }
    return true
  }
}
registerProcessor('pcm-recorder', PcmRecorder)
