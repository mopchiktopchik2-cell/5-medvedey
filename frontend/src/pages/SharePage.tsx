import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, sharedPdfUrl, type Estimate } from '../api'
import { dateOnly, money, number, percent } from '../format'

export function SharePage() {
  const { token = '' } = useParams()
  const [estimate, setEstimate] = useState<Estimate | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getSharedEstimate(token)
      .then(setEstimate)
      .catch((err: Error) => setError(err.message))
  }, [token])

  if (error) {
    return (
      <div className="page page--narrow">
        <div className="card">
          <h1 className="h2">Ссылка недействительна</h1>
          <p className="muted">{error}</p>
        </div>
      </div>
    )
  }

  if (!estimate) {
    return (
      <div className="page page--narrow">
        <p className="hint">Загружаем расчёт…</p>
      </div>
    )
  }

  const rows = [
    { label: 'Материал', value: estimate.material_cost, note: `${number(estimate.material_length_m, 3)} м` },
    { label: 'Раскрой', value: estimate.cutting_cost, note: `${number(estimate.cutting_hours, 2)} ч` },
    { label: 'Пошив', value: estimate.sewing_cost, note: `${number(estimate.sewing_hours, 2)} ч` },
  ]
  estimate.hardware_items.forEach((item) =>
    rows.push({ label: `Фурнитура: ${item.name}`, value: item.total, note: '' }),
  )
  estimate.branding_items.forEach((item) =>
    rows.push({ label: `Брендирование: ${item.name}`, value: item.total, note: `${item.positions} поз.` }),
  )

  return (
    <div className="page page--narrow">
      <header className="page__header">
        <h1>Коммерческое предложение № {estimate.number}</h1>
        <p className="page__subtitle">
          от {dateOnly(estimate.created_at)} · {estimate.contractor_name ?? 'Заказчик не указан'}
        </p>
      </header>

      <div className="card">
        <dl className="facts">
          <div>
            <dt>Изделие</dt>
            <dd>{estimate.product_type_name}</dd>
          </div>
          <div>
            <dt>Тираж</dt>
            <dd>{estimate.quantity} шт.</dd>
          </div>
          <div>
            <dt>Сложность</dt>
            <dd>{estimate.complexity_name}</dd>
          </div>
          <div>
            <dt>Ткань</dt>
            <dd>
              {estimate.fabric_name}, {number(estimate.fabric_width_cm, 1)} см
            </dd>
          </div>
          <div>
            <dt>Отходы</dt>
            <dd>{percent(estimate.waste_coefficient)}</dd>
          </div>
          <div>
            <dt>Срок изготовления</dt>
            <dd>{estimate.lead_time_days} раб. дн.</dd>
          </div>
        </dl>
      </div>

      <div className="card">
        <table className="table">
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <td>{row.label}</td>
                <td className="table__muted">{row.note}</td>
                <td className="table__num">{money(row.value)}</td>
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
      </div>

      <div className="actions">
        <a className="button" href={sharedPdfUrl(token)} target="_blank" rel="noreferrer">
          Скачать PDF
        </a>
        <Link className="button button--ghost" to="/login">
          Войти в систему
        </Link>
      </div>
    </div>
  )
}
