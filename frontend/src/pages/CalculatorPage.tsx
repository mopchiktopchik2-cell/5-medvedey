import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Dictionaries, type EstimatePreview, type EstimateRequest } from '../api'
import { money, number, percent, plural } from '../format'

type PartRow = { key: string; name: string; length: string; width: string; count: string }

type FormState = {
  productTypeId: string
  complexityId: string
  quantity: string
  hasLining: boolean
  hasHood: boolean
  hasPockets: boolean
  fabricId: string
  fabricWidth: string
  fabricPrice: string
  waste: string
  seam: string
  parts: PartRow[]
  hardwareQty: Record<string, string>
  brandingPos: Record<string, string>
  contractorName: string
  notes: string
}

const DRAFT_KEY = 'mir-estimate-draft-v1'

const PART_PRESETS: Record<string, Omit<PartRow, 'key'>[]> = {
  Футболка: [
    { name: 'Перед', length: '70', width: '50', count: '1' },
    { name: 'Спинка', length: '70', width: '50', count: '1' },
    { name: 'Рукав', length: '60', width: '25', count: '2' },
  ],
  Худи: [
    { name: 'Перед', length: '72', width: '58', count: '1' },
    { name: 'Спинка', length: '72', width: '58', count: '1' },
    { name: 'Рукав', length: '62', width: '30', count: '2' },
    { name: 'Капюшон', length: '40', width: '55', count: '1' },
  ],
  Шоппер: [
    { name: 'Полотно', length: '42', width: '38', count: '2' },
    { name: 'Ручка', length: '70', width: '5', count: '2' },
  ],
  Бейсболка: [
    { name: 'Клин', length: '20', width: '15', count: '6' },
    { name: 'Козырёк', length: '20', width: '8', count: '1' },
    { name: 'Околыш', length: '58', width: '4', count: '1' },
  ],
}

function emptyForm(): FormState {
  return {
    productTypeId: '',
    complexityId: '',
    quantity: '100',
    hasLining: false,
    hasHood: false,
    hasPockets: false,
    fabricId: '',
    fabricWidth: '',
    fabricPrice: '',
    waste: '18',
    seam: '1.5',
    parts: [],
    hardwareQty: {},
    brandingPos: {},
    contractorName: '',
    notes: '',
  }
}

let keyCounter = 0
function nextKey(): string {
  keyCounter += 1
  return `part-${keyCounter}`
}

function withKeys(rows: Omit<PartRow, 'key'>[]): PartRow[] {
  return rows.map((row) => ({ ...row, key: nextKey() }))
}

function loadDraft(): FormState | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as FormState
    if (!parsed || !Array.isArray(parsed.parts)) return null
    return { ...emptyForm(), ...parsed, parts: withKeys(parsed.parts) }
  } catch {
    return null
  }
}

function parseNumber(value: string): number {
  const normalized = value.replace(',', '.').trim()
  return normalized === '' ? Number.NaN : Number(normalized)
}

export function CalculatorPage() {
  const navigate = useNavigate()
  const [dictionaries, setDictionaries] = useState<Dictionaries | null>(null)
  const [form, setForm] = useState<FormState>(() => loadDraft() ?? emptyForm())
  const [preview, setPreview] = useState<EstimatePreview | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const touched = useRef(false)

  useEffect(() => {
    api
      .dictionaries()
      .then((data) => {
        setDictionaries(data)
        setForm((current) => {
          const patch: Partial<FormState> = {}
          if (!current.productTypeId && data.product_types[0]) {
            patch.productTypeId = String(data.product_types[0].id)
          }
          if (!current.complexityId) {
            const base = data.complexity_levels.find((level) => level.code === 'base')
            patch.complexityId = String((base ?? data.complexity_levels[0]).id)
          }
          if (!current.fabricId && data.fabrics[0]) {
            patch.fabricId = String(data.fabrics[0].id)
            patch.fabricWidth = String(data.fabrics[0].width_cm)
            patch.fabricPrice = String(data.fabrics[0].price_per_m)
          }
          if (!current.parts.length) {
            const product = data.product_types.find(
              (item) => String(item.id) === (patch.productTypeId ?? current.productTypeId),
            )
            const preset = product ? PART_PRESETS[product.name] : undefined
            if (preset) patch.parts = withKeys(preset)
          }
          if (patch.waste === undefined && data.settings) {
            patch.waste = String(Math.round(data.settings.waste_coefficient * 100))
            patch.seam = String(data.settings.seam_allowance_cm)
          }
          return { ...current, ...patch }
        })
      })
      .catch((err: Error) => setPreviewError(err.message))
  }, [])

  useEffect(() => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(form))
  }, [form])

  const payload = useMemo<EstimateRequest | null>(() => {
    if (!form.productTypeId || !form.complexityId || !form.fabricId) return null
    const quantity = parseNumber(form.quantity)
    if (!Number.isFinite(quantity) || quantity < 1) return null

    const parts = form.parts
      .map((row) => ({
        name: row.name.trim(),
        length_cm: parseNumber(row.length),
        width_cm: parseNumber(row.width),
        count_per_unit: parseNumber(row.count),
      }))
      .filter(
        (row) =>
          row.name &&
          Number.isFinite(row.length_cm) &&
          row.length_cm > 0 &&
          Number.isFinite(row.width_cm) &&
          row.width_cm > 0 &&
          Number.isFinite(row.count_per_unit) &&
          row.count_per_unit >= 1,
      )

    if (!parts.length) return null

    const hardware = Object.entries(form.hardwareQty)
      .map(([id, qty]) => ({ hardware_id: Number(id), qty_per_unit: parseNumber(qty) || 0 }))
      .filter((line) => line.qty_per_unit > 0)

    const branding = Object.entries(form.brandingPos)
      .map(([id, positions]) => ({ branding_id: Number(id), positions: parseNumber(positions) || 0 }))
      .filter((line) => line.positions > 0)

    const result: EstimateRequest = {
      product_type_id: Number(form.productTypeId),
      complexity_id: Number(form.complexityId),
      quantity: Math.round(quantity),
      has_lining: form.hasLining,
      has_hood: form.hasHood,
      has_pockets: form.hasPockets,
      fabric_id: Number(form.fabricId),
      parts,
      hardware,
      branding,
      contractor_name: form.contractorName.trim() || null,
      notes: form.notes.trim() || null,
    }

    const width = parseNumber(form.fabricWidth)
    if (Number.isFinite(width) && width > 0) result.fabric_width_cm = width
    const price = parseNumber(form.fabricPrice)
    if (Number.isFinite(price) && price >= 0) result.fabric_price_per_m = price
    const waste = parseNumber(form.waste)
    if (Number.isFinite(waste) && waste >= 0) result.waste_coefficient = waste / 100
    const seam = parseNumber(form.seam)
    if (Number.isFinite(seam) && seam >= 0) result.seam_allowance_cm = seam

    return result
  }, [form])

  useEffect(() => {
    if (!payload) {
      setPreview(null)
      return
    }
    let cancelled = false
    setLoadingPreview(true)
    const timer = setTimeout(() => {
      api
        .preview(payload)
        .then((data) => {
          if (cancelled) return
          setPreview(data)
          setPreviewError(null)
        })
        .catch((err: Error) => {
          if (cancelled) return
          setPreview(null)
          setPreviewError(err.message)
        })
        .finally(() => {
          if (!cancelled) setLoadingPreview(false)
        })
    }, 350)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [payload])

  const product = dictionaries?.product_types.find((item) => String(item.id) === form.productTypeId)
  const fabric = dictionaries?.fabrics.find((item) => String(item.id) === form.fabricId)

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    touched.current = true
    setForm((current) => ({ ...current, [key]: value }))
  }

  function applyProduct(productId: string) {
    const selected = dictionaries?.product_types.find((item) => String(item.id) === productId)
    const preset = selected ? PART_PRESETS[selected.name] : undefined
    setForm((current) => ({
      ...current,
      productTypeId: productId,
      parts: preset ? withKeys(preset) : current.parts,
      hasHood: selected?.name === 'Худи' ? current.hasHood : false,
    }))
    touched.current = true
  }

  function applyFabric(fabricId: string) {
    const selected = dictionaries?.fabrics.find((item) => String(item.id) === fabricId)
    setForm((current) => ({
      ...current,
      fabricId,
      fabricWidth: selected ? String(selected.width_cm) : current.fabricWidth,
      fabricPrice: selected ? String(selected.price_per_m) : current.fabricPrice,
    }))
  }

  function updatePart(key: string, field: keyof Omit<PartRow, 'key'>, value: string) {
    setForm((current) => ({
      ...current,
      parts: current.parts.map((row) => (row.key === key ? { ...row, [field]: value } : row)),
    }))
  }

  function addPart() {
    setForm((current) => ({
      ...current,
      parts: [...current.parts, { key: nextKey(), name: '', length: '', width: '', count: '1' }],
    }))
  }

  function removePart(key: string) {
    setForm((current) => ({ ...current, parts: current.parts.filter((row) => row.key !== key) }))
  }

  function toggleHardware(id: number, checked: boolean) {
    setForm((current) => {
      const next = { ...current.hardwareQty }
      if (checked) next[String(id)] = next[String(id)] ?? '1'
      else delete next[String(id)]
      return { ...current, hardwareQty: next }
    })
  }

  function toggleBranding(id: number, checked: boolean) {
    setForm((current) => {
      const next = { ...current.brandingPos }
      if (checked) next[String(id)] = next[String(id)] ?? '1'
      else delete next[String(id)]
      return { ...current, brandingPos: next }
    })
  }

  async function handleSave() {
    if (!payload || !preview) return
    setSaving(true)
    setSaveError(null)
    try {
      const estimate = await api.createEstimate(payload)
      localStorage.removeItem(DRAFT_KEY)
      navigate(`/estimates/${estimate.id}`)
    } catch (err) {
      setSaveError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const rollWidth = parseNumber(form.fabricWidth) || fabric?.width_cm || 0

  return (
    <div className="page">
      <header className="page__header page__header--row">
        <div>
          <h1>Расчёт изделия</h1>
          <p className="page__subtitle">
            Экспресс-смета: материал, раскрой, пошив, фурнитура и брендирование
          </p>
        </div>
        <button
          type="button"
          className="button button--ghost button--small"
          onClick={() => {
            setForm(emptyForm())
            localStorage.removeItem(DRAFT_KEY)
          }}
        >
          Очистить
        </button>
      </header>

      <div className="calc">
        <div className="calc__form">
          <section className="card">
            <h2 className="h3">1. Изделие</h2>
            <div className="grid grid--2">
              <label className="field">
                <span>Тип изделия</span>
                <select value={form.productTypeId} onChange={(event) => applyProduct(event.target.value)}>
                  {dictionaries?.product_types.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Сложность</span>
                <select
                  value={form.complexityId}
                  onChange={(event) => update('complexityId', event.target.value)}
                >
                  {dictionaries?.complexity_levels.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} · ×{number(item.factor, 2)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Тираж, шт.</span>
                <input
                  inputMode="numeric"
                  value={form.quantity}
                  onChange={(event) => update('quantity', event.target.value)}
                />
              </label>

              <div className="field">
                <span>Дополнительно</span>
                <div className="checks">
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={form.hasLining}
                      onChange={(event) => update('hasLining', event.target.checked)}
                    />
                    подкладка
                  </label>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={form.hasHood}
                      onChange={(event) => update('hasHood', event.target.checked)}
                    />
                    капюшон
                  </label>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={form.hasPockets}
                      onChange={(event) => update('hasPockets', event.target.checked)}
                    />
                    карманы
                  </label>
                </div>
              </div>
            </div>
            {product && (
              <p className="hint">
                Базовое время пошива «{product.name}» — {number(product.base_sewing_hours, 2)} ч/ед.
              </p>
            )}
          </section>

          <section className="card">
            <h2 className="h3">2. Материал</h2>
            <div className="grid grid--2">
              <label className="field">
                <span>Ткань</span>
                <select value={form.fabricId} onChange={(event) => applyFabric(event.target.value)}>
                  {dictionaries?.fabrics
                    .filter((item) => item.is_active)
                    .map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                </select>
              </label>

              <label className="field">
                <span>Ширина рулона, см</span>
                <input
                  inputMode="decimal"
                  value={form.fabricWidth}
                  onChange={(event) => update('fabricWidth', event.target.value)}
                />
              </label>

              <label className="field">
                <span>Цена, ₽/пог. м</span>
                <input
                  inputMode="decimal"
                  value={form.fabricPrice}
                  onChange={(event) => update('fabricPrice', event.target.value)}
                />
              </label>

              <label className="field">
                <span>Межлекальные отходы, %</span>
                <input
                  inputMode="decimal"
                  value={form.waste}
                  onChange={(event) => update('waste', event.target.value)}
                />
              </label>

              <label className="field">
                <span>Припуск на шов, см</span>
                <input
                  inputMode="decimal"
                  value={form.seam}
                  onChange={(event) => update('seam', event.target.value)}
                />
              </label>
            </div>
            {fabric?.density && <p className="hint">Состав: {fabric.density}</p>}
          </section>

          <section className="card">
            <div className="card__head">
              <h2 className="h3">3. Детали кроя</h2>
              <button type="button" className="button button--ghost button--small" onClick={addPart}>
                + Деталь
              </button>
            </div>

            <table className="table table--compact">
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Длина, см</th>
                  <th>Ширина, см</th>
                  <th>В комплекте</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {form.parts.map((row) => (
                  <tr key={row.key}>
                    <td>
                      <input
                        value={row.name}
                        onChange={(event) => updatePart(row.key, 'name', event.target.value)}
                        placeholder="Перед"
                      />
                    </td>
                    <td>
                      <input
                        inputMode="decimal"
                        value={row.length}
                        onChange={(event) => updatePart(row.key, 'length', event.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        inputMode="decimal"
                        value={row.width}
                        onChange={(event) => updatePart(row.key, 'width', event.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        inputMode="numeric"
                        value={row.count}
                        onChange={(event) => updatePart(row.key, 'count', event.target.value)}
                      />
                    </td>
                    <td className="table__action">
                      <button
                        type="button"
                        className="icon-button"
                        onClick={() => removePart(row.key)}
                        aria-label="Удалить деталь"
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!form.parts.length && <p className="hint">Добавьте хотя бы одну деталь кроя.</p>}
            <p className="hint">
              Припуск {number(parseNumber(form.seam) || 0, 1)} см добавляется с каждой стороны детали.
            </p>
          </section>

          <section className="card">
            <h2 className="h3">4. Фурнитура</h2>
            <div className="lines">
              {dictionaries?.hardware
                .filter((item) => item.is_active)
                .map((item) => {
                  const checked = form.hardwareQty[String(item.id)] !== undefined
                  return (
                    <div key={item.id} className="line">
                      <label className="check check--grow">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(event) => toggleHardware(item.id, event.target.checked)}
                        />
                        {item.name}
                        <span className="line__hint">{money(item.price)}</span>
                      </label>
                      {checked && item.unit === 'piece' && (
                        <input
                          className="line__input"
                          inputMode="decimal"
                          value={form.hardwareQty[String(item.id)]}
                          onChange={(event) =>
                            setForm((current) => ({
                              ...current,
                              hardwareQty: {
                                ...current.hardwareQty,
                                [String(item.id)]: event.target.value,
                              },
                            }))
                          }
                          aria-label="Количество на изделие"
                        />
                      )}
                      {checked && item.unit === 'per_item' && (
                        <span className="line__hint">на изделие</span>
                      )}
                    </div>
                  )
                })}
            </div>
          </section>

          <section className="card">
            <h2 className="h3">5. Брендирование</h2>
            <div className="lines">
              {dictionaries?.branding
                .filter((item) => item.is_active)
                .map((item) => {
                  const checked = form.brandingPos[String(item.id)] !== undefined
                  return (
                    <div key={item.id} className="line">
                      <label className="check check--grow">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(event) => toggleBranding(item.id, event.target.checked)}
                        />
                        {item.name}
                        <span className="line__hint">{money(item.price)}</span>
                      </label>
                      {checked && (
                        <input
                          className="line__input"
                          inputMode="numeric"
                          value={form.brandingPos[String(item.id)]}
                          onChange={(event) =>
                            setForm((current) => ({
                              ...current,
                              brandingPos: {
                                ...current.brandingPos,
                                [String(item.id)]: event.target.value,
                              },
                            }))
                          }
                          aria-label="Количество позиций"
                        />
                      )}
                    </div>
                  )
                })}
            </div>
            <p className="hint">Количество позиций — сколько нанесений на одно изделие.</p>
          </section>

          <section className="card">
            <h2 className="h3">6. Заказчик</h2>
            <div className="grid grid--2">
              <label className="field">
                <span>Подрядчик</span>
                <input
                  list="contractors"
                  value={form.contractorName}
                  onChange={(event) => update('contractorName', event.target.value)}
                  placeholder="Название или выберите из списка"
                />
                <datalist id="contractors">
                  {dictionaries?.contractors.map((item) => (
                    <option key={item.id} value={item.name} />
                  ))}
                </datalist>
              </label>

              <label className="field">
                <span>Комментарий для КП</span>
                <input
                  value={form.notes}
                  onChange={(event) => update('notes', event.target.value)}
                  placeholder="Например: макет согласован"
                  maxLength={2000}
                />
              </label>
            </div>
          </section>
        </div>

        <aside className="calc__summary">
          <div className="card summary">
            <h2 className="h3">Смета</h2>

            {previewError && (
              <p className="alert" role="alert">
                {previewError}
              </p>
            )}

            {!preview && !previewError && <p className="hint">Заполните параметры расчёта.</p>}

            {preview && (
              <>
                <div className="summary__total">
                  <span className="muted">Итого за тираж</span>
                  <strong>{money(preview.totals.total_cost)}</strong>
                  <span className="muted">
                    {money(preview.totals.unit_cost)} за единицу · {preview.totals.quantity}{' '}
                    {plural(preview.totals.quantity, 'шт.', 'шт.', 'шт.')}
                  </span>
                </div>

                <table className="table table--compact">
                  <tbody>
                    <tr>
                      <td>
                        Материал
                        <div className="table__muted">
                          {preview.material.fabric_name} ·{' '}
                          {number(preview.material.length_with_waste_m, 3)} м
                        </div>
                      </td>
                      <td className="table__num">{money(preview.totals.material_cost)}</td>
                    </tr>
                    <tr>
                      <td>
                        Раскрой
                        <div className="table__muted">
                          {preview.cutting.pieces_total} дет. · {number(preview.cutting.hours, 2)} ч
                        </div>
                      </td>
                      <td className="table__num">{money(preview.totals.cutting_cost)}</td>
                    </tr>
                    <tr>
                      <td>
                        Пошив
                        <div className="table__muted">
                          {number(preview.sewing.hours, 2)} ч × {money(preview.sewing.normohour)}
                        </div>
                      </td>
                      <td className="table__num">{money(preview.totals.sewing_cost)}</td>
                    </tr>
                    {preview.hardware.map((line) => (
                      <tr key={`hw-${line.hardware_id}`}>
                        <td>{line.name}</td>
                        <td className="table__num">{money(line.total)}</td>
                      </tr>
                    ))}
                    {preview.branding.map((line) => (
                      <tr key={`br-${line.branding_id}`}>
                        <td>{line.name}</td>
                        <td className="table__num">{money(line.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="summary__meta">
                  <span>Отходы {percent(preview.material.waste_coefficient)}</span>
                  <span>Срок: {preview.lead_time_days} раб. дн.</span>
                </div>

                {preview.warnings.map((warning) => (
                  <p key={warning} className="notice">
                    {warning}
                  </p>
                ))}

                <details className="layout">
                  <summary>
                    Раскладка: {preview.cutting.rows_total}{' '}
                    {plural(preview.cutting.rows_total, 'полоса', 'полосы', 'полос')}
                    {preview.cutting.rows_truncated ? ' (показаны первые)' : ''}
                  </summary>
                  <div className="layout__rows">
                    {preview.cutting.rows.slice(0, 18).map((row, index) => (
                      <div key={index} className="layout__row">
                        <span className="layout__label">×{row.pieces}</span>
                        <span
                          className="layout__bar"
                          style={{ width: `${Math.min(100, (row.used_width_cm / rollWidth) * 100)}%` }}
                        />
                        <span className="layout__value">{number(row.height_cm, 1)} см</span>
                      </div>
                    ))}
                  </div>
                  {preview.cutting.approximate && (
                    <p className="hint">Большой тираж: длина рассчитана по партии и масштабирована.</p>
                  )}
                </details>

                {saveError && (
                  <p className="alert" role="alert">
                    {saveError}
                  </p>
                )}

                <button type="button" className="button button--wide" onClick={handleSave} disabled={saving}>
                  {saving ? 'Сохраняем…' : 'Сохранить расчёт'}
                </button>
                {loadingPreview && <p className="hint">Пересчитываем…</p>}
              </>
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}
