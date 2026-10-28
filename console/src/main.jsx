import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import { applySavedTheme } from './theme.js'
import '../../design/tokens.css'
import '../../design/primitives.css'
import './styles/app.css'

applySavedTheme()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
