import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { initAuth } from './api/client.js'
import { applySavedTheme } from './theme.js'
import '../../design/tokens.css'
import './styles/base.css'

applySavedTheme()
initAuth()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
