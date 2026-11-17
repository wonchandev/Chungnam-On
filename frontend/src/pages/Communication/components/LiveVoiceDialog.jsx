import { useEffect, useRef, useState } from 'react'
import { Mic, Square } from 'lucide-react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import FormSelect from '../../../components/FormSelect.jsx'
import { socketUrl } from '../api.js'

const messages = { google_key_missing: '음성 통역 서비스가 아직 설정되지 않았습니다.', voice_stream_timeout: '통역 시간이 초과되었습니다. 다시 시작해 주세요.', speech_stream_error: '음성 인식 서비스에 연결하지 못했습니다.', voice_stream_busy: '음성 처리량이 많습니다. 잠시 후 다시 시작해 주세요.', voice_stream_limit: '최대 통역 시간에 도달했습니다.', invalid_voice_languages: '선택한 언어는 실시간 음성 인식을 지원하지 않습니다.' }
export default function LiveVoiceDialog({ languages, onClose }) {
  const [source, setSource] = useState('ko')
  const [target, setTarget] = useState('vi')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [segments, setSegments] = useState({})
  const resources = useRef({})
  const alive = useRef(true)
  function releaseAudio() {
    const current = resources.current
    clearTimeout(current.limit)
    current.node?.disconnect(); current.input?.disconnect(); current.stream?.getTracks().forEach(track => track.stop())
    current.context?.close().catch(() => {})
    current.node = null; current.input = null; current.stream = null; current.context = null
  }
  useEffect(() => {
    alive.current = true
    return () => { alive.current = false; clearTimeout(resources.current.wait); clearTimeout(resources.current.connection); releaseAudio(); resources.current.ws?.close() }
  }, [])
  function stop() {
    releaseAudio()
    if (resources.current.ws?.readyState === WebSocket.OPEN) {
      resources.current.ws.send(JSON.stringify({ type: 'stop' })); setStatus('finishing')
      resources.current.wait = setTimeout(() => { resources.current.ws?.close(); if (alive.current) { setStatus('idle'); setError('최종 결과를 기다리는 시간이 초과되었습니다.') } }, 20000)
    } else { resources.current.ws?.close(); setStatus('idle') }
  }
  async function start() {
    if (status !== 'idle') return
    setStatus('connecting'); setError(''); setSegments({})
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode) throw new Error('이 브라우저에서는 실시간 통역을 지원하지 않습니다. 음성 번역을 이용해 주세요.')
      const current = resources.current = {}
      current.context = new AudioContext(); await current.context.resume()
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true } })
      if (!alive.current) { stream.getTracks().forEach(track => track.stop()); return }
      current.stream = stream
      await current.context.audioWorklet.addModule('/audio/pcm-recorder.js')
      if (!alive.current) return
      const ws = current.ws = new WebSocket(socketUrl('/ws/translate/voice/'))
      current.connection = setTimeout(() => { ws.close(); releaseAudio(); if (alive.current) { setStatus('idle'); setError('통역 서버 연결 시간이 초과되었습니다.') } }, 10000)
      ws.onopen = () => ws.send(JSON.stringify({ type: 'start', source, target }))
      ws.onmessage = event => {
        if (!alive.current) return
        let data
        try { data = JSON.parse(event.data) } catch { return }
        if (data.type === 'ready') {
          clearTimeout(current.connection)
          current.input = current.context.createMediaStreamSource(stream)
          current.node = new AudioWorkletNode(current.context, 'pcm-recorder')
          current.node.port.onmessage = frame => {
            if (ws.readyState !== WebSocket.OPEN) return
            if (ws.bufferedAmount > 64000) { setError('네트워크 연결이 느려 통역을 중단했습니다.'); stop(); return }
            ws.send(frame.data)
          }
          const mute = current.context.createGain(); mute.gain.value = 0
          current.input.connect(current.node); current.node.connect(mute); mute.connect(current.context.destination)
          setStatus('recording'); current.limit = setTimeout(stop, 275000)
        }
        if (data.type === 'transcript' || data.type === 'translation') setSegments(value => ({ ...value, [data.segment]: { ...value[data.segment], ...data } }))
        if (data.type === 'error') { setError(messages[data.code] || '통역을 처리하지 못했습니다. 다시 시도해 주세요.'); releaseAudio(); ws.close() }
        if (data.type === 'complete') { clearTimeout(current.wait); releaseAudio(); setStatus('idle'); ws.close() }
      }
      ws.onclose = event => {
        clearTimeout(current.wait); clearTimeout(current.connection); releaseAudio()
        if (alive.current) { setStatus('idle'); if (event.code !== 1000) setError(value => value || (event.code === 4401 ? '로그인이 만료되었습니다. 다시 로그인해 주세요.' : '통역 연결이 종료되었습니다. 다시 시작해 주세요.')) }
      }
      ws.onerror = () => { if (alive.current) setError('통역 서버에 연결하지 못했습니다.') }
    } catch (failure) { releaseAudio(); if (alive.current) { setError(failure.message); setStatus('idle') } }
  }
  const options = languages.map(language => ({ value: language.code, label: language.native_name }))
  return <HomeDialog title="AI 실시간 현장 통역" onClose={onClose} wide><div className="comm-dialog-content">
    <p>마이크로 말하면 문장별 원문과 번역을 보여드려요. 한 번에 최대 약 4분 30초까지 이용할 수 있어요.</p>
    <fieldset disabled={status !== 'idle'} className="comm-language-pair"><FormSelect label="말하는 언어" name="source" value={source} onChange={event => setSource(event.target.value)} options={options} /><FormSelect label="번역 언어" name="target" value={target} onChange={event => setTarget(event.target.value)} options={options} /></fieldset>
    <button className={`comm-record ${status === 'recording' ? 'is-recording' : ''}`} onClick={status === 'recording' ? stop : start} disabled={status === 'connecting' || status === 'finishing' || !languages.length}>{status === 'recording' ? <Square size={20} /> : <Mic size={20} />}{status === 'recording' ? '통역 종료' : status === 'connecting' ? '연결 중…' : status === 'finishing' ? '마지막 문장 번역 중…' : '통역 시작'}</button>
    {status === 'recording' && <p role="status">듣고 있어요. 마이크에 가까이 말씀해 주세요.</p>}
    {error && <p className="comm-error" role="alert">{error}</p>}
    <div className="comm-live-results" aria-live="polite">{Object.entries(segments).map(([id, segment]) => <div key={id}><p>{segment.corrected_text || segment.text}</p>{segment.translated_text && <strong>{segment.translated_text}</strong>}</div>)}</div>
  </div></HomeDialog>
}
