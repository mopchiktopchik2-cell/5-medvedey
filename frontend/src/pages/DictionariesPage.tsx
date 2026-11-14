import { useEffect, useMemo, useState } from 'react'
import { api, logoUrl, type Dictionaries, type LogoMeta } from '../api'
import { number } from '../format'

type FieldDef = {
  key: string
  label: string
  kind?: 'text' | 'number' | 'select' | 'bool'
  options?: { value: string; label: string }[]
}

type RowItem = { id: number; values: Record<string, string> }

type SaveHandler = (values: Record<string, string>, id?: number) => Promise<void>

function EntityTable({
  fields,
  items,
  blank,
  addLabel,
  onSave,
}: {
  fields: FieldDef[]
  items: RowItem[]
  blank: Record<string, string>
  addLabel: string
  onSave: SaveHandler
}) {
  const [rows, setRows] = useState<RowItem[]>(items)
  const [draft, setDraft] = useState<Record<string, string>>(blank)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setRows(items)
  }, [items])

  function updateDraft(key: string, value: string) {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  function updateRow(id: number, key: string, value: string) {
    setRows((current) =>
      current.map((row) => (row.id === id ? { ...row, values: { ...row.values, [key]: value } } : row)),
    )
  }

  async function save(values: Record<string, string>, id?: number) {
    setBusy(id ? String(id) : 'new')
    setError(null)
    try {
      await onSave(values, id)
      if (!id) setDraft(blank)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(null)
    }
  }

  function control(field: FieldDef, value: string, onChange: (value: string) => void) {
    if (field.kind === 'select' || field.kind === 'bool') {
      const options =
        field.kind === 'bool'
          ? [
              { value: 'true', label: 'Активна' },
              { value: 'false', label: 'Скрыта' },
            ]
          : (field.options ?? [])
      return (
        <select value={value} onChange={(event) => onChange(event.target.value)}>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )
    }
    return (
      <input
        inputMode={field.kind === 'number' ? 'decimal' : undefined}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  }

  return (
    <div className="stack">
      {error && <p className="alert" role="alert">{error}</p>}

      <table className="table table--compact">
        <thead>
          <tr>
            {fields.map((field) => (
              <th key={field.key}>{field.label}</th>
            ))}
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {fields.map((field) => (
                <td key={field.key}>
                  {control(field, row.values[field.key] ?? '', (value) =>
                    updateRow(row.id, field.key, value),
                  )}
                </td>
              ))}
              <td className="table__action">
                <button
                  type="button"
                  className="button button--small"
                  onClick={() => void save(row.values, row.id)}
                  disabled={busy === String(row.id)}
                >
                  {busy === String(row.id) ? '…' : 'Сохранить'}
                </button>
              </td>
            </tr>
          ))}

          <tr className="table__new">
            {fields.map((field) => (
              <td key={field.key}>
                {control(field, draft[field.key] ?? '', (value) => updateDraft(field.key, value))}
              </td>
            ))}
            <td className="table__action">
              <button
                type="button"
                className="button button--ghost button--small"
                onClick={() => void save(draft)}
                disabled={busy === 'new'}
              >
                {busy === 'new' ? '…' : addLabel}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

const FABRIC_FIELDS: FieldDef[] = [
  { key: 'name', label: 'Название' },
  { key: 'width_cm', label: 'Ширина, см', kind: 'number' },
  { key: 'price_per_m', label: '₽/пог. м', kind: 'number' },
  { key: 'density', label: 'Состав' },
  { key: 'is_active', label: 'Статус', kind: 'bool' },
]

const HARDWARE_FIELDS: FieldDef[] = [
  { key: 'name', label: 'Название' },
  {
    key: 'unit',
    label: 'Единица',
    kind: 'select',
    options: [
      { value: 'piece', label: 'за штуку' },
      { value: 'per_item', label: 'на изделие' },
    ],
  },
  { key: 'price', label: 'Цена, ₽', kind: 'number' },
  { key: 'is_active', label: 'Статус', kind: 'bool' },
]

const BRANDING_FIELDS: FieldDef[] = [
  { key: 'name', label: 'Название' },
  { key: 'price', label: 'Цена за позицию, ₽', kind: 'number' },
  { key: 'is_active', label: 'Статус', kind: 'bool' },
]

const PRODUCT_FIELDS: FieldDef[] = [
  { key: 'name', label: 'Название' },
  { key: 'base_sewing_hours', label: 'Базовое время, ч', kind: 'number' },
  { key: 'is_active', label: 'Статус', kind: 'bool' },
]

const COMPLEXITY_FIELDS: FieldDef[] = [
  { key: 'code', label: 'Код' },
  { key: 'name', label: 'Название' },
  { key: 'factor', label: 'Коэффициент', kind: 'number' },
]

const FABRIC_BLANK = { name: '', width_cm: '180', price_per_m: '0', density: '', is_active: 'true' }
const HARDWARE_BLANK = { name: '', unit: 'piece', price: '0', is_active: 'true' }
const BRANDING_BLANK = { name: '', price: '0', is_active: 'true' }
const PRODUCT_BLANK = { name: '', base_sewing_hours: '0.6', is_active: 'true' }
const COMPLEXITY_BLANK = { code: '', name: '', factor: '1.0' }

function LogoCard() {
  const [meta, setMeta] = useState<LogoMeta | null>(null)
  const [version, setVersion] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getLogoMeta().then(setMeta).catch(() => undefined)
  }, [])

  async function upload(file: File | undefined) {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      const next = await api.uploadLogo(file)
      setMeta(next)
      setVersion(Date.now())
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    if (!window.confirm('Удалить логотип из КП?')) return
    setBusy(true)
    setError(null)
    try {
      await api.deleteLogo()
      setMeta({ has_logo: false, updated_at: null })
      setVersion(Date.now())
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="logo-card">
      <div className="logo-card__text">
        <h2 className="h3">Логотип в КП</h2>
        <p className="hint">
          PNG, JPEG или WebP до 2 МБ. Показывается в шапке PDF и на публичной странице.
        </p>
      </div>

      {meta?.has_logo ? (
        <div className="logo-card__preview">
          <img src={logoUrl(version || meta.updated_at || undefined)} alt="Логотип цеха" />
        </div>
      ) : (
        <p className="hint">{meta ? 'Логотип не загружен.' : 'Проверяем…'}</p>
      )}

      <div className="actions actions--tight">
        <label className="button button--ghost button--small button--file">
          {busy ? 'Загружаем…' : meta?.has_logo ? 'Заменить' : 'Загрузить логотип'}
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            hidden
            disabled={busy}
            onChange={(event) => {
              void upload(event.target.files?.[0])
              event.target.value = ''
            }}
          />
        </label>
        {meta?.has_logo && (
          <button
            type="button"
            className="button button--ghost button--small"
            onClick={() => void remove()}
            disabled={busy}
          >
            Удалить
          </button>
        )}
      </div>

      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

export function DictionariesPage() {
  const [tab, setTab] = useState<'fabrics' | 'hardware' | 'branding' | 'products' | 'complexity' | 'settings'>(
    'fabrics',
  )
  const [data, setData] = useState<Dictionaries | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = () => api.dictionaries().then(setData).catch((err: Error) => setError(err.message))

  useEffect(() => {
    void reload()
  }, [])

  const fabricRows = useMemo<RowItem[]>(
    () =>
      (data?.fabrics ?? []).map((item) => ({
        id: item.id,
        values: {
          name: item.name,
          width_cm: String(item.width_cm),
          price_per_m: String(item.price_per_m),
          density: item.density ?? '',
          is_active: String(item.is_active),
        },
      })),
    [data],
  )

  const hardwareRows = useMemo<RowItem[]>(
    () =>
      (data?.hardware ?? []).map((item) => ({
        id: item.id,
        values: {
          name: item.name,
          unit: item.unit,
          price: String(item.price),
          is_active: String(item.is_active),
        },
      })),
    [data],
  )

  const brandingRows = useMemo<RowItem[]>(
    () =>
      (data?.branding ?? []).map((item) => ({
        id: item.id,
        values: { name: item.name, price: String(item.price), is_active: String(item.is_active) },
      })),
    [data],
  )

  const productRows = useMemo<RowItem[]>(
    () =>
      (data?.product_types ?? []).map((item) => ({
        id: item.id,
        values: {
          name: item.name,
          base_sewing_hours: String(item.base_sewing_hours),
          is_active: String(item.is_active),
        },
      })),
    [data],
  )

  const complexityRows = useMemo<RowItem[]>(
    () =>
      (data?.complexity_levels ?? []).map((item) => ({
        id: item.id,
        values: { code: item.code, name: item.name, factor: String(item.factor) },
      })),
    [data],
  )

  const [settingsDraft, setSettingsDraft] = useState<Record<string, string>>({})
  useEffect(() => {
    if (!data) return
    setSettingsDraft({
      sewing_normohour: String(data.settings.sewing_normohour),
      cutting_normohour: String(data.settings.cutting_normohour),
      waste_coefficient: String(Math.round(data.settings.waste_coefficient * 100)),
      cutting_rate_parts_per_hour: String(data.settings.cutting_rate_parts_per_hour),
      seam_allowance_cm: String(data.settings.seam_allowance_cm),
      lining_factor: String(data.settings.lining_factor),
      hood_factor: String(data.settings.hood_factor),
      pockets_factor: String(data.settings.pockets_factor),
      daily_capacity_units: String(data.settings.daily_capacity_units),
      lead_time_buffer_days: String(data.settings.lead_time_buffer_days),
      company_name: data.settings.company_name,
      company_requisites: data.settings.company_requisites,
    })
  }, [data])

  async function saveSettings() {
    setError(null)
    try {
      await api.saveSettings({
        sewing_normohour: Number(settingsDraft.sewing_normohour),
        cutting_normohour: Number(settingsDraft.cutting_normohour),
        waste_coefficient: Number(settingsDraft.waste_coefficient) / 100,
        cutting_rate_parts_per_hour: Number(settingsDraft.cutting_rate_parts_per_hour),
        seam_allowance_cm: Number(settingsDraft.seam_allowance_cm),
        lining_factor: Number(settingsDraft.lining_factor),
        hood_factor: Number(settingsDraft.hood_factor),
        pockets_factor: Number(settingsDraft.pockets_factor),
        daily_capacity_units: Number(settingsDraft.daily_capacity_units),
        lead_time_buffer_days: Number(settingsDraft.lead_time_buffer_days),
        company_name: settingsDraft.company_name,
        company_requisites: settingsDraft.company_requisites,
      })
      await reload()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const tabs = [
    { key: 'fabrics', label: 'Ткани' },
    { key: 'hardware', label: 'Фурнитура' },
    { key: 'branding', label: 'Брендирование' },
    { key: 'products', label: 'Изделия' },
    { key: 'complexity', label: 'Сложность' },
    { key: 'settings', label: 'Настройки' },
  ] as const

  return (
    <div className="page">
      <header className="page__header">
        <h1>Справочники</h1>
        <p className="page__subtitle">
          Базовые параметры цеха. Изменения сразу влияют на новые расчёты.
        </p>
      </header>

      <div className="tabs">
        {tabs.map((item) => (
          <button
            key={item.key}
            type="button"
            className={tab === item.key ? 'tab tab--active' : 'tab'}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error && <p className="alert" role="alert">{error}</p>}
      {!data && <p className="hint">Загружаем справочники…</p>}

      {data && (
        <section className="card">
          {tab === 'fabrics' && (
            <EntityTable
              fields={FABRIC_FIELDS}
              items={fabricRows}
              blank={FABRIC_BLANK}
              addLabel="Добавить ткань"
              onSave={async (values, id) => {
                await api.saveFabric({
                  id,
                  name: values.name,
                  width_cm: Number(values.width_cm),
                  price_per_m: Number(values.price_per_m),
                  density: values.density || null,
                  is_active: values.is_active === 'true',
                })
                await reload()
              }}
            />
          )}

          {tab === 'hardware' && (
            <EntityTable
              fields={HARDWARE_FIELDS}
              items={hardwareRows}
              blank={HARDWARE_BLANK}
              addLabel="Добавить фурнитуру"
              onSave={async (values, id) => {
                await api.saveHardware({
                  id,
                  name: values.name,
                  unit: values.unit as 'piece' | 'per_item',
                  price: Number(values.price),
                  is_active: values.is_active === 'true',
                })
                await reload()
              }}
            />
          )}

          {tab === 'branding' && (
            <EntityTable
              fields={BRANDING_FIELDS}
              items={brandingRows}
              blank={BRANDING_BLANK}
              addLabel="Добавить брендирование"
              onSave={async (values, id) => {
                await api.saveBranding({
                  id,
                  name: values.name,
                  price: Number(values.price),
                  is_active: values.is_active === 'true',
                })
                await reload()
              }}
            />
          )}

          {tab === 'products' && (
            <EntityTable
              fields={PRODUCT_FIELDS}
              items={productRows}
              blank={PRODUCT_BLANK}
              addLabel="Добавить изделие"
              onSave={async (values, id) => {
                await api.saveProductType({
                  id,
                  name: values.name,
                  base_sewing_hours: Number(values.base_sewing_hours),
                  is_active: values.is_active === 'true',
                })
                await reload()
              }}
            />
          )}

          {tab === 'complexity' && (
            <EntityTable
              fields={COMPLEXITY_FIELDS}
              items={complexityRows}
              blank={COMPLEXITY_BLANK}
              addLabel="Добавить уровень"
              onSave={async (values, id) => {
                await api.saveComplexity({
                  id,
                  code: values.code,
                  name: values.name,
                  factor: Number(values.factor),
                })
                await reload()
              }}
            />
          )}

          {tab === 'settings' && (
            <div className="stack">
              <LogoCard />

              <div className="grid grid--2">
                <label className="field">
                  <span>Нормо-час швеи, ₽</span>
                  <input
                    inputMode="decimal"
                    value={settingsDraft.sewing_normohour ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({ ...current, sewing_normohour: event.target.value }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Нормо-час раскройщика, ₽</span>
                  <input
                    inputMode="decimal"
                    value={settingsDraft.cutting_normohour ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({
                        ...current,
                        cutting_normohour: event.target.value,
                      }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Отходы раскроя, %</span>
                  <input
                    inputMode="decimal"
                    value={settingsDraft.waste_coefficient ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({
                        ...current,
                        waste_coefficient: event.target.value,
                      }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Выработка раскройщика, дет./ч</span>
                  <input
                    inputMode="numeric"
                    value={settingsDraft.cutting_rate_parts_per_hour ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({
                        ...current,
                        cutting_rate_parts_per_hour: event.target.value,
                      }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Припуск на шов, см</span>
                  <input
                    inputMode="decimal"
                    value={settingsDraft.seam_allowance_cm ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({ ...current, seam_allowance_cm: event.target.value }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Мощность цеха, шт./день</span>
                  <input
                    inputMode="numeric"
                    value={settingsDraft.daily_capacity_units ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({
                        ...current,
                        daily_capacity_units: event.target.value,
                      }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Буфер срока, дней</span>
                  <input
                    inputMode="numeric"
                    value={settingsDraft.lead_time_buffer_days ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({
                        ...current,
                        lead_time_buffer_days: event.target.value,
                      }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Коэффициент подкладки</span>
                  <input
                    inputMode="decimal"
                    value={settingsDraft.lining_factor ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({ ...current, lining_factor: event.target.value }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Коэффициент капюшона</span>
                  <input
                    inputMode="decimal"
                    value={settingsDraft.hood_factor ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({ ...current, hood_factor: event.target.value }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Коэффициент карманов</span>
                  <input
                    inputMode="decimal"
                    value={settingsDraft.pockets_factor ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({ ...current, pockets_factor: event.target.value }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Название цеха</span>
                  <input
                    value={settingsDraft.company_name ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({ ...current, company_name: event.target.value }))
                    }
                  />
                </label>
                <label className="field">
                  <span>Реквизиты в КП</span>
                  <input
                    value={settingsDraft.company_requisites ?? ''}
                    onChange={(event) =>
                      setSettingsDraft((current) => ({
                        ...current,
                        company_requisites: event.target.value,
                      }))
                    }
                  />
                </label>
              </div>

              <p className="hint">
                Текущая стоимость пошива: {number(data.settings.sewing_normohour, 2)} ₽/ч · раскроя:{' '}
                {number(data.settings.cutting_normohour, 2)} ₽/ч
              </p>

              <button type="button" className="button" onClick={() => void saveSettings()}>
                Сохранить настройки
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
