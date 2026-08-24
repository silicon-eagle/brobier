import { expect, test } from '@playwright/test'

test('home page shows the placeholder heading', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Brobier' })).toBeVisible()
})
