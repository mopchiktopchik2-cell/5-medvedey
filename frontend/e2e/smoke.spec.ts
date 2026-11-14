import { expect, test } from '@playwright/test'

// Проверяем не отдельные компоненты, а весь путь: nginx → API → cookie → React.
// Демо-учётки по умолчанию подставлены в форму входа.

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
