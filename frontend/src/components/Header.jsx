import { Link } from 'react-router-dom'
import Navigation from './Navigation.jsx'

export default function Header() {
  return (
    <header className="site-header">
      <Link className="brand" to="/">충남온</Link>
      <Navigation />
    </header>
  )
}
