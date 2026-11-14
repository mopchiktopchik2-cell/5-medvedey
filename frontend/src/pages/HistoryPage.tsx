import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Dictionaries, type EstimateListItem } from '../api'
import { dateTime, money, plural } from '../format'

export function HistoryPage() {
  const [dictionaries, setDictionaries] = useState<Dictionaries | null>(null)
  const [items, setItems] = useState<EstimateListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [query, setQuery] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [contractorId, setContractorId] = useState('')
  const [productTypeId, setProductTypeId] = useState('')

  useEffect(() => {
    api.dictionaries().then(setDictionaries).catch(() => undefined)
  }, [])

  const params = useMemo(
    () => ({
      q: query.trim() || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      contractor_id: contractorId || undefined,
      product_type_id: productTypeId || undefined,
      limit: 200,
    }),
    [query, dateFrom, dateTo, contractorId, productTypeId],
  )

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    const timer = setTimeout(() => {
      api
        .listEstimates(params)
        .then((data) => {
          if (cancelled) return
          setItems(data.items)
          setTotal(data.total)
          setError(null)
        })
        .catch((err: Error) => {
          if (!cancelled) setError(err.message)
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 250)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [params])

  async function handleDelete(id: number, number: string) {
    if (!window.confirm(`Удалить расчёт ${number}?`)) return
    try {
      await api.deleteEstimate(id)
      setItems((current) => current.filter((item) => item.id !== id))
      setTotal((current) => Math.max(0, current - 1))
    } catch (err) {
      setError((err as Error).message)
    }
  }

  function resetFilters() {
    setQuery('')
    setDateFrom('')
    setDateTo('')
    setContractorId('')
    setProductTypeId('')
  }

  return (
    <div className="page">
      <header className="page__header">
        <h1>История расчётов</h1>
        <p className="page__subtitle">
          {total} {plural(total, 'расчёт', 'расчёта', 'расчётов')} в базе
        </p>
      </header>

      <section className="card">
        <div className="filters">
          <label className="field field--grow">
            <span>Поиск</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Номер, изделие или подрядчик"
            />
          </label>

          <label className="field">
            <span>С даты</span>
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>

          <label className="field">
            <span>По дату</span>
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>

          <label className="field">
            <span>Подрядчик</span>
            <select value={contractorId} onChange={(event) => setContractorId(event.target.value)}>
              <option value="">Все</option>
              {dictionaries?.contractors.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Изделие</span>
            <select value={productTypeId} onChange={(event) => setProductTypeId(event.target.value)}>
              <option value="">Все</option>
              {dictionaries?.product_types.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>

          <button type="button" className="button button--ghost button--small" onClick={resetFilters}>
            Сбросить
          </button>
        </div>
      </section>

      {error && <p className="alert" role="alert">{error}</p>}

      <section className="card card--flush">
        <table className="table">
          <thead>
            <tr>
              <th>Номер</th>
              <th>Дата</th>
              <th>Подрядчик</th>
              <th>Изделие</th>
              <th className="table__num">Тираж</th>
              <th className="table__num">Итого</th>
              <th className="table__num">За ед.</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>
                  <Link className="link" to={`/estimates/${item.id}`}>
                    {item.number}
                  </Link>
                </td>
                <td className="table__muted">{dateTime(item.created_at)}</td>
                <td>{item.contractor_name ?? '—'}</td>
                <td>{item.product_type_name}</td>
                <td className="table__num">{item.quantity}</td>
                <td className="table__num">{money(item.total_cost)}</td>
                <td className="table__num">{money(item.unit_cost)}</td>
                <td className="table__action">
                  <button
                    type="button"
                    className="icon-button"
                    onClick={() => handleDelete(item.id, item.number)}
                    aria-label={`Удалить ${item.number}`}
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!loading && !items.length && (
          <p className="hint hint--pad">Расчётов не найдено. Измените фильтры или создайте новый.</p>
        )}
        {loading && <p className="hint hint--pad">Загружаем…</p>}
      </section>
    </div>
  )
}
