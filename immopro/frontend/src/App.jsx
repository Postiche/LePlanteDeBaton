import { useEffect, useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import Icon from './components/Icon.jsx'
import Login from './pages/Login.jsx'
import ResetPassword from './pages/ResetPassword.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Properties from './pages/Properties.jsx'
import PropertyDetail from './pages/PropertyDetail.jsx'
import PropertyForm from './pages/PropertyForm.jsx'
import Requests from './pages/Requests.jsx'
import RequestDetail from './pages/RequestDetail.jsx'
import RequestForm from './pages/RequestForm.jsx'
import Matches from './pages/Matches.jsx'
import Imports from './pages/Imports.jsx'
import MapPage from './pages/MapPage.jsx'
import Contacts from './pages/Contacts.jsx'
import ContactDetail from './pages/ContactDetail.jsx'
import Companies from './pages/Companies.jsx'
import Visits from './pages/Visits.jsx'
import Reminders from './pages/Reminders.jsx'
import External from './pages/External.jsx'
import Emails from './pages/Emails.jsx'
import Settings from './pages/Settings.jsx'
import Account from './pages/Account.jsx'

const NAV = [
  ['Pilotage', [['/', 'dashboard', 'Tableau de bord'], ['/correspondances', 'link', 'Correspondances'], ['/carte', 'map', 'Carte']]],
  ['Immobilier', [['/offres', 'building', 'Offres'], ['/demandes', 'search', 'Demandes clients'], ['/recherche-externe', 'globe', 'Annonces externes'], ['/imports', 'upload', 'Imports']]],
  ['Commercial', [['/contacts', 'users', 'Contacts'], ['/entreprises', 'briefcase', 'Entreprises'], ['/visites', 'calendar', 'Visites'], ['/relances', 'bell', 'Relances'], ['/emails', 'mail', 'Emails']]],
  ['Administration', [['/parametres', 'settings', 'Paramètres']]],
]

function Layout({ children }) {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const loc = useLocation()
  const nav = useNavigate()
  useEffect(() => setOpen(false), [loc.pathname])
  const initials = (user.full_name || user.username).split(/\s+/).map((x) => x[0]).slice(0, 2).join('').toUpperCase()
  return (
    <div className="app">
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand"><img src="/icons/icon.svg" alt="" /><div>ImmoPro<small>Entreprise</small></div></div>
        <nav className="nav" aria-label="Navigation principale">
          {NAV.map(([section, items]) => (
            <div key={section}>
              <div className="nav-section">{section}</div>
              {items.map(([to, icon, label]) => (
                <NavLink key={to} to={to} end={to === '/'}><Icon name={icon} />{label}</NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <NavLink to="/compte" className="avatar" title="Mon compte">{initials}</NavLink>
          <div className="who"><b>{user.full_name || user.username}</b><span className="small">{user.role}</span></div>
          <button className="icon-btn" style={{ color: '#c9d4e5' }} onClick={logout} title="Se déconnecter" aria-label="Se déconnecter"><Icon name="logout" size={18} /></button>
        </div>
      </aside>
      {open && <div className="modal-back" style={{ zIndex: 39, padding: 0 }} onClick={() => setOpen(false)} />}
      <div className="main">
        <header className="topbar">
          <button className="burger" onClick={() => setOpen(true)} aria-label="Ouvrir le menu"><Icon name="menu" size={24} /></button>
          <form className="search" onSubmit={(e) => { e.preventDefault(); nav(`/offres?q=${encodeURIComponent(q)}`) }} role="search">
            <Icon name="search" />
            <input type="search" placeholder="Rechercher une offre (réf., ville, adresse…)" value={q} onChange={(e) => setQ(e.target.value)} />
          </form>
          <div className="spacer" />
          <NavLink className="btn btn-accent btn-sm hide-sm" to="/offres/nouvelle"><Icon name="plus" />Offre</NavLink>
          <NavLink className="btn btn-sm hide-sm" to="/demandes/nouvelle"><Icon name="plus" />Demande</NavLink>
        </header>
        {user.must_change_password && loc.pathname !== '/compte' && (
          <div className="demo-banner" style={{ background: '#fff1eb', color: '#8a2d07' }}>Mot de passe temporaire : <NavLink to="/compte">changez-le maintenant</NavLink>.</div>
        )}
        <main className="content">{children}</main>
      </div>
      <nav className="mobile-tabbar" aria-label="Navigation mobile">
        <NavLink to="/" end><Icon name="dashboard" />Accueil</NavLink>
        <NavLink to="/offres"><Icon name="building" />Offres</NavLink>
        <NavLink to="/demandes"><Icon name="search" />Demandes</NavLink>
        <NavLink to="/correspondances"><Icon name="link" />Matching</NavLink>
        <NavLink to="/relances"><Icon name="bell" />Relances</NavLink>
      </nav>
    </div>
  )
}

export default function App() {
  const { user } = useAuth()
  const loc = useLocation()
  if (user === undefined) return <div className="spinner" style={{ marginTop: '40vh' }} />
  if (loc.pathname === '/reinitialisation') return <ResetPassword />
  if (!user) return <Login />
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/offres" element={<Properties />} />
        <Route path="/offres/nouvelle" element={<PropertyForm />} />
        <Route path="/offres/:id" element={<PropertyDetail />} />
        <Route path="/offres/:id/modifier" element={<PropertyForm />} />
        <Route path="/demandes" element={<Requests />} />
        <Route path="/demandes/nouvelle" element={<RequestForm />} />
        <Route path="/demandes/:id" element={<RequestDetail />} />
        <Route path="/demandes/:id/modifier" element={<RequestForm />} />
        <Route path="/correspondances" element={<Matches />} />
        <Route path="/imports" element={<Imports />} />
        <Route path="/carte" element={<MapPage />} />
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/contacts/:id" element={<ContactDetail />} />
        <Route path="/entreprises" element={<Companies />} />
        <Route path="/visites" element={<Visits />} />
        <Route path="/relances" element={<Reminders />} />
        <Route path="/recherche-externe" element={<External />} />
        <Route path="/emails" element={<Emails />} />
        <Route path="/parametres" element={<Settings />} />
        <Route path="/compte" element={<Account />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
