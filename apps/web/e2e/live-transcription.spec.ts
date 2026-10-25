import { expect, test } from "@playwright/test";

const SESSION_ID = "SESSION-DEMO";

test("fake microphone streams through SpecLive and persists an identified speaker", async ({
  page,
  request,
}) => {
  await page.goto("/");

  const autoDetect = page.getByRole("checkbox", { name: "Auto-detect voices" });
  await expect(autoDetect).toBeChecked();

  const start = page.getByRole("button", { name: "Start recording" });
  await expect(start).toBeEnabled();
  await start.click();

  await expect(page.getByRole("button", { name: "Stop recording" })).toBeEnabled();
  await expect(page.getByTestId("live-partial")).toContainText("Live microphone test", {
    timeout: 15_000,
  });

  await page.getByRole("button", { name: "Stop recording" }).click();
  const persistedSegment = page
    .locator("[data-segment-id]")
    .filter({ hasText: "Live microphone test complete" })
    .last();
  await expect(persistedSegment).toBeVisible({ timeout: 15_000 });
  await expect(
    persistedSegment.getByRole("button", { name: "Correct speaker Voice 1" }),
  ).toBeVisible();

  await expect
    .poll(async () => {
      const response = await request.get(
        `http://127.0.0.1:8000/api/v1/sessions/${SESSION_ID}/transcript`,
      );
      const segments = (await response.json()) as Array<{
        text: string;
        speaker_id: string | null;
        speaker_name: string | null;
        speaker_source: string;
      }>;
      return segments.find((segment) => segment.text === "Live microphone test complete");
    })
    .toEqual(
      expect.objectContaining({
        speaker_id: "voice-1",
        speaker_name: "Voice 1",
        speaker_source: "detected",
      }),
    );

  await persistedSegment.getByRole("button", { name: "Correct speaker Voice 1" }).click();
  await persistedSegment.getByLabel("Speaker role").selectOption("customer");
  await persistedSegment.getByLabel("Speaker name").fill("Maya");
  await persistedSegment.getByRole("button", { name: "Save" }).click();
  await expect(
    persistedSegment.getByRole("button", { name: "Correct speaker Maya" }),
  ).toBeVisible();

  await expect
    .poll(async () => {
      const response = await request.get(
        `http://127.0.0.1:8000/api/v1/sessions/${SESSION_ID}/transcript`,
      );
      const segments = (await response.json()) as Array<{
        text: string;
        speaker: string;
        speaker_name: string | null;
        speaker_source: string;
      }>;
      return segments.find((segment) => segment.text === "Live microphone test complete");
    })
    .toEqual(
      expect.objectContaining({
        speaker: "customer",
        speaker_name: "Maya",
        speaker_source: "corrected",
      }),
    );
});
