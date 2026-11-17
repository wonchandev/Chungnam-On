import { useEffect, useRef, useState } from 'react'
import { Mic, Square, Volume2 } from 'lucide-react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import FormSelect from '../../../components/FormSelect.jsx'
import { communicationRequest, errorMessage } from '../api.js'

const titles = { text: '텍스트 번역', voice: '음성 번역', image: '사진 번역' }
export default function TranslationDialog({ mode, languages, tts, onClose }) {
  const [source, setSource] = useState(mode === 'voice' ? 'ko' : 'auto')
  const [target, setTarget] = useState('vi')
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [recording, setRecording] = useState(false)
  const [starting, setStarting] = useState(false)
  const [audioUrl, setAudioUrl] = useState('')
  const [speaking, setSpeaking] = useState(false)
  const recorder = useRef(null)
  const stream = useRef(null)
  const timer = useRef(null)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => { alive.current = false; clearTimeout(timer.current); if (recorder.current?.state === 'recording') recorder.current.stop(); stream.current?.getTracks().forEach(track => track.stop()) }
  }, [])
  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl) }, [audioUrl])
  function reset() { setResult(null); setError(''); setAudioUrl('') }
  async function record() {
    if (recording) { recorder.current?.stop(); return }
    setError(''); setStarting(true)
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') throw new Error('이 브라우저에서는 녹음을 지원하지 않습니다. 음성 파일을 선택해 주세요.')
      const media = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!alive.current) { media.getTracks().forEach(track => track.stop()); return }
      stream.current = media
      const instance = new MediaRecorder(media)
      const chunks = []
      instance.ondataavailable = event => { if (event.data.size) chunks.push(event.data) }
      instance.onstop = () => {
        clearTimeout(timer.current); media.getTracks().forEach(track => track.stop())
        if (!alive.current) return
        const ext = instance.mimeType.includes('mp4') ? 'm4a' : instance.mimeType.includes('ogg') ? 'ogg' : 'webm'
        setFile(new File(chunks, `recording.${ext}`, { type: instance.mimeType })); setRecording(false)
      }
      instance.onerror = () => { media.getTracks().forEach(track => track.stop()); setRecording(false); setError('녹음을 완료하지 못했습니다. 다시 시도해 주세요.') }
      recorder.current = instance; reset(); setFile(null); instance.start(); setRecording(true)
      timer.current = setTimeout(() => { if (instance.state === 'recording') instance.stop() }, 280000)
    } catch (failure) { stream.current?.getTracks().forEach(track => track.stop()); setError(failure.message) }
    finally { if (alive.current) setStarting(false) }
  }
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    reset(); setBusy(true)
    try {
      let body = { source, target, text: text.trim() }
      if (mode !== 'text') {
        if (!file) throw new Error('번역할 파일을 선택해 주세요.')
        if (file.size > (mode === 'image' ? 10 : 25) * 1024 * 1024) throw new Error(mode === 'image' ? '사진은 10MB 이하여야 합니다.' : '음성은 25MB 이하여야 합니다.')
        body = new FormData(); body.set(mode === 'image' ? 'image' : 'audio', file); body.set('source', source); body.set('target', target)
      }
      setResult(await communicationRequest(`translate/${mode}/`, { method: 'POST', body }))
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setBusy(false) }
  }
  async function speak() {
    setSpeaking(true); setError('')
    try {
      const blob = await communicationRequest('translate/tts/', { method: 'POST', body: { text: result.translated_text, language: result.target }, responseType: 'blob' })
      setAudioUrl(URL.createObjectURL(blob))
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setSpeaking(false) }
  }
  const languageOptions = languages.map(language => ({ value: language.code, label: language.native_name }))
  return <HomeDialog title={titles[mode]} onClose={onClose} wide>
    <form className="comm-dialog-content" onSubmit={submit}>
      <fieldset disabled={busy || recording || starting} className="comm-language-pair">
        <FormSelect label="원문 언어" name="source" value={source} onChange={event => { setSource(event.target.value); reset() }} options={mode === 'voice' ? languageOptions : [{ value: 'auto', label: '자동 감지' }, ...languageOptions]} />
        <FormSelect label="번역 언어" name="target" value={target} onChange={event => { setTarget(event.target.value); reset() }} options={languageOptions} />
      </fieldset>
      {mode === 'text' ? <label className="comm-input-label">번역할 내용<textarea value={text} onChange={event => { setText(event.target.value); reset() }} maxLength={5000} rows={5} required placeholder="현장에서 전하고 싶은 말을 입력하세요" disabled={busy} /><span>{text.length} / 5,000자</span></label> : <>
        {mode === 'voice' && <button className={`comm-record ${recording ? 'is-recording' : ''}`} type="button" disabled={busy || starting} onClick={record}>{recording ? <Square size={18} /> : <Mic size={18} />}{starting ? '마이크 연결 중…' : recording ? '녹음 종료' : '마이크로 녹음하기'}</button>}
        <label className="comm-input-label">{mode === 'image' ? '사진 선택 (최대 10MB)' : '음성 파일 선택 (최대 5분·25MB)'}<input type="file" accept={mode === 'image' ? 'image/*' : 'audio/*'} disabled={busy || recording} onChange={event => { setFile(event.target.files?.[0] || null); reset() }} /></label>
        {file && <p className="comm-file-name">선택된 파일: {file.name}</p>}
      </>}
      <button className="comm-primary" disabled={busy || recording || starting || !languages.length || (mode === 'text' ? !text.trim() : !file)}>{busy ? '번역 중…' : '번역하기'}</button>
      {error && <p role="alert" className="comm-error">{error}</p>}
      {result && <div className="comm-translation-result" aria-live="polite">
        {(result.transcript || result.detected_text) && <><h3>인식한 원문</h3><p>{result.transcript || result.detected_text}</p></>}
        <h3>번역 결과</h3><p>{result.translated_text || '인식된 내용이 없습니다. 다른 파일로 시도해 주세요.'}</p>
        {!!result.regions?.length && <details><summary>글자 영역별 결과</summary>{result.regions.map((region, index) => <p key={index}>{region.text} → {region.translated_text}</p>)}</details>}
        {tts && result.translated_text && <button className="comm-secondary" type="button" onClick={speak} disabled={speaking}><Volume2 size={17} />{speaking ? '음성 준비 중…' : '번역문 듣기'}</button>}
        {audioUrl && <audio src={audioUrl} controls autoPlay aria-label="번역문 음성" />}
      </div>}
    </form>
  </HomeDialog>
}
