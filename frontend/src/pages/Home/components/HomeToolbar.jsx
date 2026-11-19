import { Menu, Search } from 'lucide-react'
import RegionPicker from './RegionPicker.jsx'
import { rows } from '../utils/formatters.js'

export default function HomeToolbar({ region, regions, onRegionChange, searchOpen, onSearchToggle, menuOpen, onMenuOpen }) {
  return (
    <>
      <div className="home-toolbar">
        <RegionPicker value={region} regions={rows(regions.data)} onChange={onRegionChange} loading={regions.loading} />
        <div className="home-toolbar-actions">
          <button type="button" aria-label="일자리 검색" aria-expanded={searchOpen} onClick={onSearchToggle}><Search size={21} /></button>
          <button type="button" aria-label="전체 메뉴" aria-expanded={menuOpen} onClick={onMenuOpen}><Menu size={23} /></button>
        </div>
      </div>
      {regions.error && (
        <div className="home-region-error" role="status">
          지역 목록을 불러오지 못했어요. <button type="button" onClick={regions.retry}>다시 시도</button>
        </div>
      )}
    </>
  )
}
