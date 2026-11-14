import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, pdfUrl, type Estimate } from '../api'
import { dateTime, money, number, percent } from '../format'

export function EstimatePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [estimate, setEstimate] = useState<Estimate | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const numericId = Number(id)
    if (!Number.isFinite(numericId)) {
      setError('Некорректный номер расчёта')
      return
    }
    api
      .getEstimate(numericId)
      .then(setEstimate)
      .catch((err: Error) => setError(err.message))
  }, [id])

  async function handleShare() {
    if (!estimate) return
    try {
      const share = await api.shareEstimate(estimate.id)
      const url = `${window.location.origin}/share/${share.token}`
      setShareUrl(url)
      await navigator.clipboard.writeText(url).catch(() => undefined)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function handleDelete() {
    if (!estimate) return
    if (!window.confirm(`Удалить расчёт ${estimate.number}?`)) return
    try {
      await api.deleteEstimate(estimate.id)
      navigate('/estimates', { replace: true })
    } catch (err) {
      setError((err as Error).message)
    }
  }

  if (error) {
    return (
      <div className="page">
        <p className="alert" role="alert">{error}</p>
        <Link className="button button--ghost" to="/estimates">
          К истории
        </Link>
      </div>
    )
  }

  if (!estimate) {
    return (
      <div className="page">
        <p className="hint">Загружаем расчёт…</p>
      </div>
    )
  }

  const rows = [
    {
      label: 'Материал',
      note: `${estimate.fabric_name} · ${number(estimate.material_length_m, 3)} м × ${money(estimate.fabric_price_per_m)}`,
      value: estimate.material_cost,
    },
    {
      label: 'Раскрой',
      note: `${number(estimate.cutting_hours, 2)} ч × ${money(estimate.cutting_normohour)}`,
      value: estimate.cutting_cost,
    },
    {
      label: 'Пошив',
      note: `${number(estimate.sewing_hours, 2)} ч × ${money(estimate.sewing_normohour)}`,
      value: estimate.sewing_cost,
    },
  ]

  return (
    <div className="page">
      <header className="page__header page__header--row">
        <div>
          <h1>Коммерческое предложение № {estimate.number}</h1>
          <p className="page__subtitle">
            {dateTime(estimate.created_at)} · автор: {estimate.author_name ?? '—'}
          </p>
        </div>
        <div className="actions actions--tight">
          <a className="button" href={pdfUrl(estimate.id)} target="_blank" rel="noreferrer">
            Скачать PDF
          </a>
          <button type="button" className="button button--ghost" onClick={handleShare}>
            {copied ? 'Ссылка скопирована' : 'Ссылка для подрядчика'}
          </button>
        </div>
      </header>

      {shareUrl && (
        <p className="notice notice--ok">
          Ссылка: <code>{shareUrl}</code>
        </p>
      )}

      <section className="card">
        <dl className="facts">
          <div>
            <dt>Заказчик</dt>
            <dd>{estimate.contractor_name ?? '—'}</dd>
          </div>
          <div>
            <dt>Изделие</dt>
            <dd>
              {estimate.product_type_name} · {estimate.quantity} шт.
            </dd>
          </div>
          <div>
            <dt>Сложность</dt>
            <dd>
              {estimate.complexity_name} (×{number(estimate.complexity_factor, 2)})
            </dd>
          </div>
          <div>
            <dt>Ткань</dt>
            <dd>
              {estimate.fabric_name}, {number(estimate.fabric_width_cm, 1)} см
            </dd>
          </div>
          <div>
            <dt>Отходы / припуск</dt>
            <dd>
              {percent(estimate.waste_coefficient)} / {number(estimate.seam_allowance_cm, 1)} см
            </dd>
          </div>
          <div>
            <dt>Срок изготовления</dt>
            <dd>{estimate.lead_time_days} раб. дн.</dd>
          </div>
        </dl>
        {(estimate.has_lining || estimate.has_hood || estimate.has_pockets) && (
          <p className="hint">
            Дополнительно:{' '}
            {[
              estimate.has_lining ? 'подкладка' : null,
              estimate.has_hood ? 'капюшон' : null,
              estimate.has_pockets ? 'карманы' : null,
            ]
              .filter(Boolean)
              .join(', ')}
          </p>
        )}
      </section>

      <section className="card">
        <table className="table">
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <td>{row.label}</td>
                <td className="table__muted">{row.note}</td>
                <td className="table__num">{money(row.value)}</td>
              </tr>
            ))}
            {estimate.hardware_items.map((item) => (
              <tr key={`hw-${item.name}`}>
                <td>Фурнитура: {item.name}</td>
                <td className="table__muted">
                  {item.unit === 'per_item' ? 'на изделие' : `${number(item.qty_per_unit, 2)} шт/изд.`} ×{' '}
                  {money(item.price)}
                </td>
                <td className="table__num">{money(item.total)}</td>
              </tr>
            ))}
            {estimate.branding_items.map((item) => (
              <tr key={`br-${item.name}`}>
                <td>Брендирование: {item.name}</td>
                <td className="table__muted">
                  {item.positions} поз. × {money(item.price)}
                </td>
                <td className="table__num">{money(item.total)}</td>
              </tr>
            ))}
            <tr className="table__total">
              <td colSpan={2}>Итого за тираж</td>
              <td className="table__num">{money(estimate.total_cost)}</td>
            </tr>
            <tr>
              <td colSpan={2}>Себестоимость единицы</td>
              <td className="table__num">{money(estimate.unit_cost)}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2 className="h3">Детали кроя</h2>
        <table className="table table--compact">
          <thead>
            <tr>
              <th>Деталь</th>
              <th className="table__num">Длина, см</th>
              <th className="table__num">Ширина, см</th>
              <th className="table__num">В комплекте</th>
            </tr>
          </thead>
          <tbody>
            {estimate.parts.map((part) => (
              <tr key={part.name}>
                <td>{part.name}</td>
                <td className="table__num">{number(part.length_cm, 1)}</td>
                <td className="table__num">{number(part.width_cm, 1)}</td>
                <td className="table__num">{part.count_per_unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {estimate.notes && <p className="hint">Комментарий: {estimate.notes}</p>}
      </section>

      <div className="actions">
        <Link className="button button--ghost" to="/">
          Новый расчёт
        </Link>
        <Link className="button button--ghost" to="/estimates">
          История
        </Link>
        <button type="button" className="button button--danger button--ghost" onClick={handleDelete}>
          Удалить расчёт
        </button>
      </div>
    </div>
  )
}
