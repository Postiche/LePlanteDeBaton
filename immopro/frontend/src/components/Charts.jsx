// Graphiques simples à une seule série (une teinte, valeurs affichées, pas de légende nécessaire).
export function HBars({ data, onClick }) {
  const max = Math.max(1, ...data.map((d) => d.count))
  if (!data.length) return <div className="muted small">Aucune donnée.</div>
  return (
    <div className="bars" role="table">
      {data.map((d) => (
        <div className="bar-row" key={d.key} role="row" title={`${d.label} : ${d.count}`} onClick={onClick ? () => onClick(d) : undefined} style={{ cursor: onClick ? 'pointer' : 'default' }}>
          <span role="cell" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.label}</span>
          <span className="bar-track" role="cell" aria-hidden="true"><i style={{ width: `${(d.count / max) * 100}%` }} /></span>
          <b role="cell" className="right">{d.count}</b>
        </div>
      ))}
    </div>
  )
}

export function Columns({ data, label }) {
  const max = Math.max(1, ...data.map((d) => d.count))
  return (
    <div>
      <div className="cols" role="img" aria-label={label}>
        {data.map((d) => (
          <div className="col" key={d.week} title={`Semaine du ${new Date(d.week).toLocaleDateString('fr-FR')} : ${d.count}`}>
            {d.count > 0 && <span>{d.count}</span>}
            <i style={{ height: `${(d.count / max) * 100}%` }} />
          </div>
        ))}
      </div>
      <div className="cols-x">
        {data.map((d, i) => <span key={d.week}>{i % Math.ceil(data.length / 6) === 0 ? new Date(d.week).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) : ''}</span>)}
      </div>
    </div>
  )
}
