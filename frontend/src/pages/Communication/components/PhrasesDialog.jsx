import { useCallback, useState } from 'react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import useHomeResource from '../../Home/hooks/useHomeResource.js'
import FormSelect from '../../../components/FormSelect.jsx'
import { communicationRequest } from '../api.js'
import LoadState from './LoadState.jsx'

export default function PhrasesDialog({ languages, onClose }) {
  const [language, setLanguage] = useState('vi')
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const load = useCallback(signal => communicationRequest('phrases/', { signal, language, query: { q: search } }), [language, search])
  const resource = useHomeResource(load)
  return <HomeDialog title="현장 필수 표현" onClose={onClose} wide><div className="comm-dialog-content">
    <FormSelect label="표현을 볼 언어" name="language" value={language} onChange={event => setLanguage(event.target.value)} options={languages.map(item => ({ value: item.code, label: item.native_name }))} />
    <form className="comm-search" onSubmit={event => { event.preventDefault(); setSearch(query) }}><input aria-label="한국어 표현 검색" placeholder="한국어 표현 검색" value={query} onChange={event => setQuery(event.target.value)} /><button className="comm-secondary">검색</button></form>
    <LoadState resource={resource} empty="검색한 표현이 없어요.">{data => <div className="comm-phrases">{data.map(phrase => <article key={phrase.id}><span>{phrase.category_label}</span><h3>{phrase.text_ko}</h3><p>{phrase.text}</p></article>)}</div>}</LoadState>
  </div></HomeDialog>
}
