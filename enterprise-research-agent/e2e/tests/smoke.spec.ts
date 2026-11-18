import { expect, test } from "@playwright/test";

test("home page loads and shows navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Enterprise Research Agent")).toBeVisible();
  await expect(page.getByRole("link", { name: "Collections" })).toBeVisible();
});

// TODO(Sprint 3): the golden path —
// register → sign in → create collection → upload a PDF → wait until "ready" →
// ask a question → wait for "succeeded" → report contains a citation → clicking it shows the source.
test.skip("golden path: upload, research, open citation", async () => {});
