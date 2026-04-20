import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Load syntax highlighting theme matching system color scheme
if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
  import('highlight.js/styles/github-dark.min.css')
} else {
  import('highlight.js/styles/github.min.css')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
