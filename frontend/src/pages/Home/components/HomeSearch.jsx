import { useState } from 'react'
import { Search } from 'lucide-react'

export default function HomeSearch({ query, onSearch }) {
  const [draft, setDraft] = useState(query)
  return (
    <form className="home-search" role="search" onSubmit={(event) => { event.preventDefault(); onSearch(draft.trim()) }}>
      <label className="home-sr-only" htmlFor="home-search-input">검색어</label>
      <input id="home-search-input" name="q" type="search" placeholder="어떤 일자리를 찾으세요?" value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={100} />
      <button type="submit" aria-label="검색"><Search size={20} /></button>
      {query && <button type="button" onClick={() => { setDraft(''); onSearch('') }}>초기화</button>}
    </form>
  )
}
