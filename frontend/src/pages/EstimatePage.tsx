import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, pdfUrl, type Estimate } from '../api'
import { DRAFT_KEY } from '../draft'
import { dateTime, money, number, percent } from '../format'

export function EstimatePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [estimate, setEstimate] = useState<Estimate | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [shareExpires, setShareExpires] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [email, setEmail] = useState('')
  const [emailComment, setEmailComment] = useState('')
  const [sending, setSending] = useState(false)
  const [emailResult, setEmailResult] = useState<{ status: 'sent' | 'outbox'; detail: string } | null>(
    null,
  )
  const [emailError, setEmailError] = useState<string | null>(null)

  useEffect(() => {
    const numericId = Number(id)
    if (!Number.isFinite(numericId)) {
      setError('Некорректный номер расчёта')
      return
    }
    api
      .getEstimate(numericId)
      .then((data) => {
        setEstimate(data)
        setEmail(data.contractor_email ?? '')
        if (data.share_token) {
          setShareUrl(`${window.location.origin}/share/${data.share_token}`)
          setShareExpires(data.share_expires_at)
        }
      })
      .catch((err: Error) => setError(err.message))
  }, [id])

  async function handleShare() {
    if (!estimate) return
    try {
      const share = await api.shareEstimate(estimate.id)
      const url = `${window.location.origin}/share/${share.token}`
      setShareUrl(url)
      setShareExpires(share.expires_at)
      await navigator.clipboard.writeText(url).catch(() => undefined)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function handleRevokeShare() {
    if (!estimate) return
    if (!window.confirm('Отозвать ссылку? Подрядчик больше не сможет её открыть.')) return
    try {
      await api.revokeShare(estimate.id)
      setShareUrl(null)
      setShareExpires(null)
      setCopied(false)
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

  async function handleSendEmail() {
    if (!estimate || !email.trim()) return
    setSending(true)
    setEmailResult(null)
    setEmailError(null)
    try {
      const result = await api.sendEmail(estimate.id, {
        to: email.trim(),
        message: emailComment.trim() || null,
      })
      setEmailResult(result)
    } catch (err) {
      setEmailError((err as Error).message)
    } finally {
      setSending(false)
    }
  }

  function handleRepeat() {
    if (!estimate) return
    const draft = {
      productTypeId: String(estimate.product_type_id),
      complexityId: String(estimate.complexity_id),
      quantity: String(estimate.quantity),
      hasLining: estimate.has_lining,
      hasHood: estimate.has_hood,
      hasPockets: estimate.has_pockets,
      fabricId: estimate.fabric_id ? String(estimate.fabric_id) : '',
      fabricWidth: String(estimate.fabric_width_cm),
      fabricPrice: String(estimate.fabric_price_per_m),
      waste: String(Math.round(estimate.waste_coefficient * 1000) / 10),
      seam: String(estimate.seam_allowance_cm),
      parts: estimate.parts.map((part) => ({
        name: part.name,
        length: String(part.length_cm),
        width: String(part.width_cm),
        count: String(part.count_per_unit),
      })),
      hardwareQty: Object.fromEntries(
        estimate.hardware_items
          .filter((item) => item.hardware_id !== null)
          .map((item) => [String(item.hardware_id), String(item.qty_per_unit)]),
      ),
      brandingPos: Object.fromEntries(
        estimate.branding_items
          .filter((item) => item.branding_id !== null)
          .map((item) => [String(item.branding_id), String(item.positions)]),
      ),
      contractorName: estimate.contractor_name ?? '',
      notes: estimate.notes ?? '',
    }
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
    navigate('/')
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
    <div className="page page--estimate">
      <header className="page__header page__header--row">
        <div className="page__heading">
          <p className="eyebrow">04 / коммерческое предложение</p>
          <h1>
            Коммерческое <em>предложение</em>
            <span className="h1__doc">№ {estimate.number}</span>
          </h1>
          <p className="page__subtitle">
            {dateTime(estimate.created_at)} · автор: {estimate.author_name ?? '—'}
          </p>
        </div>
        <div className="actions actions--tight">
          <a className="button" href={pdfUrl(estimate.id)} target="_blank" rel="noreferrer">
            Скачать PDF
          </a>
          <button type="button" className="button button--ghost" onClick={handleRepeat}>
            Повторить расчёт
          </button>
          <button type="button" className="button button--ghost" onClick={handleShare}>
            {copied ? 'Ссылка скопирована' : 'Ссылка для подрядчика'}
          </button>
        </div>
      </header>

      {shareUrl && (
        <div className="notice notice--ok">
          <p>
            Ссылка: <code>{shareUrl}</code>
          </p>
          <p className="hint">
            {shareExpires
              ? `Действует до ${dateTime(shareExpires)}. `
              : 'Срок действия не ограничен. '}
            Ссылку можно отозвать в любой момент.
          </p>
          <div className="actions actions--tight">
            <button type="button" className="button button--ghost" onClick={handleRevokeShare}>
              Отозвать ссылку
            </button>
          </div>
        </div>
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
        <h2 className="h3">Отправить КП на email</h2>
        <div className="grid grid--2">
          <label className="field">
            <span>Email получателя</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="client@example.com"
            />
          </label>
          <label className="field">
            <span>Комментарий в письме</span>
            <input
              value={emailComment}
              onChange={(event) => setEmailComment(event.target.value)}
              placeholder="Необязательно"
            />
          </label>
        </div>
        <div className="actions actions--top">
          <button
            type="button"
            className="button"
            onClick={handleSendEmail}
            disabled={sending || !email.trim()}
          >
            {sending ? 'Отправляем…' : 'Отправить PDF на email'}
          </button>
        </div>
        {emailError && (
          <p className="alert" role="alert">
            {emailError}
          </p>
        )}
        {emailResult && (
          <p className={emailResult.status === 'sent' ? 'notice notice--ok' : 'notice'}>
            {emailResult.detail}
          </p>
        )}
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
