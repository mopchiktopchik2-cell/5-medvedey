import { expect, test, type APIRequestContext } from '@playwright/test'

// Проверяем не отдельные компоненты, а весь путь: nginx → API → cookie → React.
// Демо-учётки по умолчанию подставлены в форму входа.

// В CI база чистая: перед проверкой истории создаём один расчёт через API.
async function ensureEstimate(request: APIRequestContext) {
  const list = await request.get('/api/estimates')
  expect(list.ok()).toBeTruthy()
  if ((await list.json()).total > 0) return

  const dictionaries = await (await request.get('/api/dictionaries')).json()
  const fabric = dictionaries.fabrics[0]
  const created = await request.post('/api/estimates', {
    data: {
      product_type_id: dictionaries.product_types[0].id,
      complexity_id: dictionaries.complexity_levels[0].id,
      quantity: 10,
      fabric_id: fabric.id,
      fabric_width_cm: fabric.width_cm,
      fabric_price_per_m: fabric.price_per_m,
      parts: [{ name: 'Перед', length_cm: 60, width_cm: 50, count_per_unit: 1 }],
    },
  })
  expect(created.status(), await created.text()).toBe(201)
}

test.describe('менеджер', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: 'Войти' }).click()
    await expect(page.getByRole('heading', { name: /Расчёт/ })).toBeVisible()
  })

  test('калькулятор сразу показывает смету', async ({ page }) => {
    const total = page.locator('.summary__total strong')
    await expect(total).toBeVisible()
    await expect(total).toContainText('₽')
    const digits = (await total.innerText()).replace(/\D/g, '')
    expect(Number(digits)).toBeGreaterThan(1000)
  })

  test('история открывает КП и отдаёт PDF', async ({ page }) => {
    await ensureEstimate(page.request)
    await page.goto('/estimates')
    await expect(page.getByRole('heading', { name: /История/ })).toBeVisible()

    const firstNumber = page.locator('tbody tr').first().getByRole('link').first()
    await expect(firstNumber).toContainText('КП-')
    await firstNumber.click()

    await expect(page.getByRole('heading', { name: /Коммерческое/ })).toBeVisible()
    const id = page.url().split('/').pop()

    const pdf = await page.request.get(`/api/estimates/${id}/pdf`)
    expect(pdf.status()).toBe(200)
    expect(pdf.headers()['content-type']).toContain('application/pdf')
    const body = await pdf.body()
    expect(body.subarray(0, 5).toString()).toBe('%PDF-')
  })
})

test('технолог видит импорт справочников из CSV', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('button', { name: /Технолог/ }).click()
  await page.getByRole('button', { name: 'Войти' }).click()
  await expect(page.getByRole('heading', { name: /Расчёт/ })).toBeVisible()

  await page.goto('/dictionaries')
  await expect(page.getByRole('heading', { name: /Базовые/ })).toBeVisible()
  await expect(page.getByText('Импорт из CSV', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Скачать шаблон' })).toBeVisible()
})
