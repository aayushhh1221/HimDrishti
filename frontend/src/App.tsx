/**
 * HimDrishti — Application Root
 * SIH 2026 · PS 26059
 *
 * Wraps ApplicationShell in BrowserRouter.
 * All routing is handled inside ApplicationShell.
 */

import { BrowserRouter } from 'react-router-dom'
import ApplicationShell from './components/layout/ApplicationShell'
import './index.css'

export default function App() {
  return (
    <BrowserRouter>
      <ApplicationShell />
    </BrowserRouter>
  )
}
