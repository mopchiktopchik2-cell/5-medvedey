export function money(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${value.toLocaleString('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ₽`
}

export function number(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toLocaleString('ru-RU', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

/**
 * Разбирает дату из API. SQLite/SQLAlchemy отдают время в UTC без зоны —
 * без суффикса «Z» браузер принял бы его за локальное и сдвинул бы
 * на величину часового пояса.
 */
export function parseDate(value: string): Date {
  if (!value) return new Date(Number.NaN)
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(hasZone ? value : `${value}Z`)
}

/**
 * Разбирает число из поля ввода: принимает запятую как десятичный
 * разделитель и пробелы между разрядами. Пустая строка — NaN.
 */
export function parseDecimal(value: string): number {
  const normalized = value.replace(/[\s\u00a0]/g, '').replace(',', '.')
  return normalized === '' ? Number.NaN : Number(normalized)
}

export function dateTime(value: string): string {
  const parsed = parseDate(value)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function dateOnly(value: string): string {
  const parsed = parseDate(value)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleDateString('ru-RU')
}

export function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toLocaleString('ru-RU', { maximumFractionDigits: 1 })}%`
}

export function plural(count: number, one: string, few: string, many: string): string {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few
  return many
}
