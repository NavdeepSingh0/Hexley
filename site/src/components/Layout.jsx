import { Outlet, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Nav from './Nav.jsx'
import Footer from './Footer.jsx'

// A page change starts at the top, and a #hash scrolls to its target once the page has rendered.
function ScrollToTop() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView()
    else window.scrollTo(0, 0)
  }, [pathname, hash])
  return null
}

export default function Layout() {
  return (
    <div className="site-shell">
      <ScrollToTop />
      <Nav />
      <div className="site-main"><Outlet /></div>
      <Footer />
    </div>
  )
}
