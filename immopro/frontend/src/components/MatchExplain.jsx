const SYMBOL = { ok: '✓', partiel: '~', ecart: '✕', manquant: '?', non_contraint: '–' }
const STATUS_TEXT = { ok: 'Satisfait', partiel: 'Écart partiel', ecart: 'Non satisfait', manquant: 'Information manquante', non_contraint: 'Non exprimé' }

export default function MatchExplain({ result, compact }) {
  if (!result) return null
  return (
    <div className="stack" style={{ gap: 12 }}>
      {result.eliminated && (
        <div className="alert danger"><b>Éliminé par un critère impératif :</b> {result.eliminated_by.join(' ; ')}</div>
      )}
      {result.score_potential > result.score && (
        <div className="alert warn small">
          Score {result.score}/100 — jusqu'à {result.score_potential}/100 si les informations manquantes s'avèrent favorables. Les informations manquantes ne sont pas considérées comme validées.
        </div>
      )}
      {result.groups.map((g) => (
        <div key={g.group}>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <b className="small">{g.label}</b>
            <span className="small muted">{g.earned} / {g.weight.toFixed(0)} pts</span>
          </div>
          <div className="group-bar" aria-hidden="true" style={{ margin: '5px 0 6px' }}>
            <s style={{ width: `${(g.potential / g.weight) * 100 || 0}%` }} />
            <i style={{ width: `${(g.earned / g.weight) * 100 || 0}%` }} />
          </div>
          {!compact && (
            <div className="criteria">
              {g.checks.filter((c) => c.constrained).map((c, i) => (
                <div key={i} className={`crit ${c.status}`}>
                  <span className="dot" title={STATUS_TEXT[c.status]}>{SYMBOL[c.status]}</span>
                  <span>
                    <b>{c.label}</b>{c.imperative && <span className="badge danger" style={{ marginLeft: 6 }}>Impératif</span>}
                    {c.message && <span className="muted"> — {c.message}</span>}
                  </span>
                </div>
              ))}
              {!g.checks.some((c) => c.constrained) && <div className="crit non_contraint"><span className="dot">–</span><span className="muted">Critère non exprimé par le client</span></div>}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
