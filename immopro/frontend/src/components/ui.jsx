import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import Icon from './Icon.jsx'

// ---------- Notifications ----------
const ToastCtx = createContext(() => {})
export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback((msg, type = 'info') => {
    const id = Math.random()
    setItems((x) => [...x, { id, msg, type }])
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), type === 'error' ? 7000 : 3500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => <div key={t.id} className={`toast ${t.type}`}>{t.msg}</div>)}
      </div>
    </ToastCtx.Provider>
  )
}
export const useToast = () => useContext(ToastCtx)

// ---------- Chargement de données ----------
export function useApi(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const fnRef = useRef(fn)
  fnRef.current = fn
  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await fnRef.current()
      setState({ data, loading: false, error: null })
    } catch (e) {
      setState({ data: null, loading: false, error: e })
    }
  }, [])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load() }, deps)
  return { ...state, reload: load, setData: (d) => setState((s) => ({ ...s, data: typeof d === 'function' ? d(s.data) : d })) }
}

export function Loader({ state, children }) {
  if (state.loading && !state.data) return <div className="spinner" aria-label="Chargement" />
  if (state.error) return <div className="alert danger">{state.error.message}</div>
  return children(state.data)
}

export function Modal({ title, onClose, children, footer, wide }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = '' }
  }, [onClose])
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head"><h2>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Fermer"><Icon name="x" size={20} /></button></div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  )
}

export function Empty({ icon = 'file', children }) {
  return <div className="empty"><Icon name={icon} /><div>{children}</div></div>
}

export function Score({ value, small }) {
  const v = Math.round(value ?? 0)
  return <span className={`score ${small ? 'sm' : ''}`} style={{ '--v': v }} title={`Score ${v}/100`}><span>{v}</span></span>
}

export function DemoBadge({ show }) {
  return show ? <span className="badge demo" title="Donnée de démonstration fictive">DÉMO</span> : null
}

export function Field({ label, hint, children, wide }) {
  return <label className={`field ${wide ? 'wide' : ''}`}>{label}{children}{hint && <span className="hint">{hint}</span>}</label>
}

export function Chips({ options, value = [], onChange, imperative }) {
  const toggle = (k) => onChange(value.includes(k) ? value.filter((x) => x !== k) : [...value, k])
  return (
    <div className="chips">
      {Object.entries(options).map(([k, l]) => (
        <button type="button" key={k} className={`chip ${imperative ? 'imp' : ''} ${value.includes(k) ? 'on' : ''}`} onClick={() => toggle(k)} aria-pressed={value.includes(k)}>{l}</button>
      ))}
    </div>
  )
}

export function Dl({ rows }) {
  return (
    <dl className="dl">
      {rows.map(([k, v]) => [
        <dt key={k + 't'}>{k}</dt>,
        <dd key={k + 'd'} className={v === '—' || v === null || v === undefined || v === '' ? 'na' : ''}>{v === null || v === undefined || v === '' || v === '—' ? 'Non renseigné' : v}</dd>,
      ])}
    </dl>
  )
}

export function Confirm({ message, onConfirm, onClose, confirmLabel = 'Confirmer', danger }) {
  return (
    <Modal title="Confirmation" onClose={onClose} footer={<><button className="btn" onClick={onClose}>Annuler</button><button className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`} onClick={() => { onConfirm(); onClose() }}>{confirmLabel}</button></>}>
      <p style={{ margin: 0 }}>{message}</p>
    </Modal>
  )
}
