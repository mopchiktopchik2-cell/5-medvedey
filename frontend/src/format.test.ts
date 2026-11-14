import { describe, expect, it } from 'vitest'
import {
  dateOnly,
  dateTime,
  money,
  number,
  parseDate,
  parseDecimal,
  percent,
  plural,
} from './format'

describe('money', () => {
  it('форматирует сумму с копейками и знаком рубля', () => {
    expect(money(1234.5)).toMatch(/^1\s?234,50\s?₽$/)
  })

  it('возвращает прочерк вместо пустого значения', () => {
    expect(money(null)).toBe('—')
    expect(money(undefined)).toBe('—')
    expect(money(Number.NaN)).toBe('—')
  })
})

describe('number', () => {
  it('округляет до заданного числа знаков', () => {
    expect(number(1234.567, 1)).toMatch(/^1\s?234,6$/)
    expect(number(2, 3)).toMatch(/^2,000$/)
  })

  it('возвращает прочерк вместо пустого значения', () => {
    expect(number(null)).toBe('—')
  })
})

describe('percent', () => {
  it('переводит долю в проценты', () => {
    expect(percent(0.12)).toBe('12%')
    expect(percent(0.085)).toBe('8,5%')
  })
})

describe('plural', () => {
  const forms: [number, string][] = [
    [1, 'товар'],
    [2, 'товара'],
    [5, 'товаров'],
    [11, 'товаров'],
    [21, 'товар'],
    [104, 'товара'],
  ]

  it.each(forms)('%i → %s', (count, expected) => {
    expect(plural(count, 'товар', 'товара', 'товаров')).toBe(expected)
  })
})

describe('parseDecimal', () => {
  it('принимает запятую как разделитель и пробелы между разрядами', () => {
    expect(parseDecimal('1,5')).toBe(1.5)
    expect(parseDecimal('1 234,50')).toBe(1234.5)
    expect(parseDecimal('180')).toBe(180)
  })

  it('возвращает NaN для пустого поля', () => {
    expect(Number.isNaN(parseDecimal(''))).toBe(true)
    expect(Number.isNaN(parseDecimal('  '))).toBe(true)
  })
})

describe('parseDate', () => {
  it('считает время без зоны как UTC', () => {
    expect(parseDate('2026-03-04T10:00:00').getTime()).toBe(Date.UTC(2026, 2, 4, 10))
  })

  it('уважает явно указанную зону', () => {
    expect(parseDate('2026-03-04T13:00:00+03:00').getTime()).toBe(Date.UTC(2026, 2, 4, 10))
    expect(parseDate('2026-03-04T10:00:00.123Z').getTime()).toBe(
      Date.UTC(2026, 2, 4, 10, 0, 0, 123),
    )
  })
})

describe('даты', () => {
  it('форматирует корректную дату', () => {
    const local = new Date(2026, 2, 4, 10, 0)
    expect(dateOnly(local.toISOString())).toMatch(/^0?4\.0?3\.2026$/)
    expect(dateTime(local.toISOString())).toMatch(/^\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2}$/)
  })

  it('возвращает прочерк для некорректной даты', () => {
    expect(dateOnly('не дата')).toBe('—')
    expect(dateTime('')).toBe('—')
  })
})
