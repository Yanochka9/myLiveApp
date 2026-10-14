// Индикатор активности iOS: 8 лепестков с затуханием по кругу.
export function Spinner({ large = false, label = 'Загрузка' }: { large?: boolean; label?: string }) {
  return (
    <span className={large ? 'spinner lg' : 'spinner'} role="status" aria-label={label}>
      {Array.from({ length: 8 }, (_, i) => (
        <i key={i} style={{ transform: `rotate(${i * 45}deg)`, animationDelay: `${(i - 8) * 0.1}s` }} />
      ))}
    </span>
  )
}

export function SkeletonRows({ rows = 3 }: { rows?: number }) {
  return (
    <div className="list" aria-hidden>
      {Array.from({ length: rows }, (_, i) => (
        <div className="task" key={i}>
          <div className="skeleton" style={{ width: 24, height: 24, borderRadius: '50%' }} />
          <div style={{ flex: 1, paddingTop: 3 }}>
            <div className="skeleton" style={{ height: 14, width: `${70 - i * 15}%` }} />
            <div className="skeleton" style={{ height: 10, width: '30%', marginTop: 8 }} />
          </div>
        </div>
      ))}
    </div>
  )
}
