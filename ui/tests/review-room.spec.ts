import { expect, test } from "@playwright/test";

import { demoProjectState } from "../src/test/fixtures";
import type { ProjectState } from "../src/lib/types";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/launch-context", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ project_id: null, project_dir: null })
    });
  });
});

async function startDemo(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  await page.getByRole("button", { name: /Explore companion demo/ }).click();
}

const animationContracts = [
  { id: "idle", label: "Idle", row: 0, durations: [280, 110, 110, 140, 140, 320] },
  { id: "running-right", label: "Run Right", row: 1, durations: [120, 120, 120, 120, 120, 120, 120, 220] },
  { id: "running-left", label: "Run Left", row: 2, durations: [120, 120, 120, 120, 120, 120, 120, 220] },
  { id: "waving", label: "Waving", row: 3, durations: [140, 140, 140, 280] },
  { id: "jumping", label: "Jumping", row: 4, durations: [140, 140, 140, 140, 280] },
  { id: "failed", label: "Failed", row: 5, durations: [140, 140, 140, 140, 140, 140, 140, 240] },
  { id: "waiting", label: "Waiting", row: 6, durations: [150, 150, 150, 150, 150, 260] },
  { id: "running", label: "Running", row: 7, durations: [120, 120, 120, 120, 120, 220] },
  { id: "review", label: "Review", row: 8, durations: [150, 150, 150, 150, 150, 280] }
];

test("onboarding explains the paths into review room", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Create with Codex/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Open a project/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Explore companion demo/ })).toBeVisible();
  await page.getByRole("button", { name: /Create with Codex/ }).click();
  await expect(page.getByRole("button", { name: "Copy agent prompt" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create v2 project" })).toBeDisabled();

  await page.getByRole("button", { name: /Open a project/ }).click();
  await expect(page.getByLabel("Project directory")).toBeVisible();
});

test("onboarding fits and scrolls at a narrow mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  const documentMetrics = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  expect(documentMetrics.scrollWidth).toBeLessThanOrEqual(documentMetrics.clientWidth);

  const shellMetrics = await page.getByLabel("Goodboy onboarding").evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    overflowY: getComputedStyle(element).overflowY
  }));
  expect(shellMetrics.scrollWidth).toBeLessThanOrEqual(shellMetrics.clientWidth);
  expect(shellMetrics.scrollHeight).toBeGreaterThan(shellMetrics.clientHeight);
  expect(shellMetrics.overflowY).toBe("auto");

  await page.getByRole("button", { name: /Create with Codex/ }).click();
  await expect(page.getByRole("button", { name: "Copy agent prompt" })).toBeVisible();
  await page.getByRole("button", { name: "Copy agent prompt" }).scrollIntoViewIfNeeded();
  await expect(page.getByRole("button", { name: "Copy agent prompt" })).toBeInViewport();
});

test("launch context opens the project supplied to goodboy ui", async ({ page }) => {
  const state = JSON.parse(JSON.stringify(demoProjectState)) as ProjectState;
  state.project_id = "launch-project";
  state.project_dir = "/private/launch-project";
  state.active_run_id = "active-run";
  state.manifest = { ...state.manifest, display_name: "Launch Project" };
  const activeSpritesheet = {
    ...state.artifacts.find((artifact) => artifact.kind === "package")!,
    id: "runs-active-run-package-spritesheet-webp",
    relative_path: "runs/active-run/package/spritesheet.webp",
    url: "/demo/active-run-spritesheet.webp"
  };
  state.artifacts = [
    {
      ...activeSpritesheet,
      id: "runs-stale-run-package-spritesheet-webp",
      relative_path: "runs/stale-run/package/spritesheet.webp",
      url: "/demo/stale-run-spritesheet.webp"
    },
    ...state.artifacts,
    activeSpritesheet
  ];
  await page.unroute("**/api/launch-context");
  await page.route("**/api/launch-context", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ project_id: state.project_id, project_dir: state.project_dir })
    });
  });
  await page.route("**/api/projects/launch-project/state", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Launch Project" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).not.toBeVisible();
  await expect(page.getByTestId("sprite-state-viewer").locator(".sprite-state-frame").first()).toHaveAttribute(
    "style",
    /active-run-spritesheet\.webp/
  );
});

test("saved v2 review evidence and blind validation survive reopening", async ({ page }) => {
  const state = JSON.parse(JSON.stringify(demoProjectState)) as ProjectState;
  state.project_id = "saved-review-project";
  state.project_dir = "/private/saved-review-project";
  state.active_run_id = "saved-run";
  state.manifest = {
    ...state.manifest,
    id: "saved-review-project",
    display_name: "Saved Review Project",
    sprite_version_number: 2,
    output_contract: {
      contract_id: "codex-pet-v2",
      rows: 11,
      columns: 8,
      cell_width: 192,
      cell_height: 208
    }
  };
  state.direction_review = {
    status: "reviewed",
    directions: [
      "000", "022.5", "045", "067.5", "090", "112.5", "135", "157.5",
      "180", "202.5", "225", "247.5", "270", "292.5", "315", "337.5"
    ].map((direction) => ({
      direction,
      verdict: "pass",
      observed: direction === "000" ? "up" : "visible",
      reason: `Saved direction evidence for ${direction}`
    }))
  };
  state.direction_blind = { ok: true, errors: [], warnings: [] };
  state.animation_review = {
    status: "approved",
    verdicts: animationContracts.map(({ id }) => ({
      state: id,
      verdict: "pass",
      state_semantics: `Saved semantics evidence for ${id}`,
      motion_continuity: `Saved continuity evidence for ${id}`,
      identity_consistency: `Saved identity evidence for ${id}`
    }))
  };

  await page.unroute("**/api/launch-context");
  await page.route("**/api/launch-context", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ project_id: state.project_id, project_dir: state.project_dir })
    });
  });
  await page.route("**/api/projects/saved-review-project/state", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Saved Review Project" })).toBeVisible();
  await expect(page.locator(".blind-review-card")).toContainText("Validated");
  await expect(page.getByLabel("Three independent blind review JSON files")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Blind review validated" })).toBeDisabled();

  const idleReview = page.locator(".animation-verdict").first();
  await expect(idleReview.getByLabel("Verdict")).toHaveValue("pass");
  await expect(idleReview.getByLabel("State meaning evidence")).toHaveValue("Saved semantics evidence for idle");

  const northReview = page.locator(".direction-verdict").filter({ hasText: "000°" });
  await expect(northReview.getByLabel("Verdict")).toHaveValue("pass");
  await expect(northReview.getByLabel("Visible evidence")).toHaveValue("Saved direction evidence for 000");

  const faceReview = page.locator(".likeness-trait").filter({ hasText: "tiny rounded white face" });
  await expect(faceReview.locator("select")).toHaveValue("pass");
  await expect(faceReview.locator("input")).toHaveValue("The compact white face matches the source.");
});

test("review room defaults to a focused decision surface", async ({ page }) => {
  await startDemo(page);
  await page.getByRole("button", { name: /Identity/ }).click();
  await page.getByRole("button", { name: /Baselines/ }).click();
  await page.getByRole("button", { name: /Style/ }).click();
  await page.getByRole("button", { name: /Generate/ }).click();
  await page.getByRole("button", { name: /QA Review/ }).click();

  await expect(page.getByRole("heading", { name: "Companion Demo" })).toBeVisible();
  await expect(page.getByRole("main").getByRole("heading", { name: "QA Review" })).toBeVisible();
  await expect(page.getByRole("banner").getByText("Decision needed: visual QA")).toBeVisible();
  await expect(page.getByLabel("Project progress")).toContainText("Current step");
  await expect(page.getByLabel("Project progress")).toContainText("QA Review");

  await expect(page.getByTestId("sprite-state-viewer")).toBeVisible();
  await expect(page.getByTestId("sprite-state-viewer")).toContainText("Idle");
  await expect(page.getByTestId("sprite-state-viewer")).toContainText("6 frames");
  await expect(page.getByLabel("Generated files")).not.toBeVisible();
  await expect(page.getByLabel("Review Room walkthrough guide")).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Toggle compare mode" })).not.toBeVisible();
  await expect(page.getByLabel("Zoom level")).not.toBeVisible();

  await page.getByRole("button", { name: "Run Right Row 1, 8 frames" }).click();
  await expect(page.getByTestId("sprite-state-viewer")).toContainText("Run Right");
  await expect(page.getByTestId("sprite-state-animation")).toHaveAttribute("data-state", "running-right");
  await expect(page.getByTestId("sprite-state-animation")).toHaveAttribute("data-row", "1");
  await expect(page.getByTestId("sprite-state-animation")).toHaveAttribute("data-frame-count", "8");
  await expect(page.getByTestId("sprite-state-animation")).toHaveAttribute(
    "data-frame-durations",
    "120,120,120,120,120,120,120,220"
  );
  await expect(page.getByTestId("sprite-state-animation")).toHaveAttribute("data-loop-duration", "1060");
  await expect.poll(async () => Number(await page.getByTestId("sprite-state-animation").getAttribute("data-frame-index"))).toBeGreaterThan(0);

  await page.getByRole("button", { name: "Open large preview" }).click();
  await expect(page.getByRole("dialog", { name: "Large artifact preview" })).toBeVisible();
  await page.getByRole("button", { name: "Toggle compare mode" }).click();
  await expect(page.getByText("Reference overlay")).toBeVisible();

  await page.getByLabel("Zoom level").fill("1.25");
  await expect(page.getByText("125%")).toBeVisible();
  await page.getByRole("button", { name: "Close preview" }).click();

  await page.keyboard.press("Meta+K");
  await page.getByText("Open Style Studio").click();
  await expect(page.getByRole("heading", { name: "Style Studio" })).toBeVisible();
  await page.getByRole("button", { name: "anime" }).click();
  await expect(page.getByRole("button", { name: "anime" })).toHaveClass(/active/);

  await page.getByRole("button", { name: "Open details" }).click();
  await expect(page.getByLabel("Generated files")).toBeVisible();
  await expect(page.getByLabel("Generated files")).toContainText("contact-sheet.png");
  await page.getByRole("button", { name: "Close details" }).click();
  await expect(page.getByLabel("Generated files")).not.toBeVisible();

  await page.getByRole("button", { name: "Back to start" }).first().click();
  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  await page.getByRole("button", { name: /Explore companion demo/ }).click();

  await page.keyboard.press("Meta+K");
  await expect(page.getByPlaceholder("Search Goodboy actions...")).toBeVisible();
  await page.getByText("Open QA Review").click();
  await expect(page.getByRole("heading", { name: "QA Review" })).toBeVisible();
});

test("state player honors every frame duration and loops in canonical order", async ({ page }) => {
  const pausedAt = new Date("2026-07-16T12:00:00Z");
  await page.clock.install({ time: pausedAt });
  await page.clock.pauseAt(pausedAt);
  await startDemo(page);
  await page.getByRole("button", { name: /Identity/ }).click();
  await page.getByRole("button", { name: /Baselines/ }).click();
  await page.getByRole("button", { name: /Style/ }).click();
  await page.getByRole("button", { name: /Generate/ }).click();
  await page.getByRole("button", { name: /QA Review/ }).click();

  const player = page.getByTestId("sprite-state-animation");
  for (const contract of animationContracts) {
    await page.getByRole("button", {
      name: `${contract.label} Row ${contract.row}, ${contract.durations.length} frames`
    }).click();
    await expect(player).toHaveAttribute("data-state", contract.id);
    expect(await player.getAttribute("data-frame-index")).toBe("0");
    await expect(player).toHaveAttribute("data-frame-durations", contract.durations.join(","));
    await expect(player).toHaveAttribute(
      "data-loop-duration",
      String(contract.durations.reduce((total, duration) => total + duration, 0))
    );

    for (let index = 0; index < contract.durations.length; index += 1) {
      await page.clock.fastForward(contract.durations[index] - 1);
      expect(await player.getAttribute("data-frame-index")).toBe(String(index));
      await page.clock.fastForward(1);
      expect(await player.getAttribute("data-frame-index")).toBe(
        String((index + 1) % contract.durations.length)
      );
    }
  }
});

test("reduced-motion preference freezes the animated player", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const pausedAt = new Date("2026-07-16T12:00:00Z");
  await page.clock.install({ time: pausedAt });
  await page.clock.pauseAt(pausedAt);
  await startDemo(page);
  await page.getByRole("button", { name: /Identity/ }).click();
  await page.getByRole("button", { name: /Baselines/ }).click();
  await page.getByRole("button", { name: /Style/ }).click();
  await page.getByRole("button", { name: /Generate/ }).click();
  await page.getByRole("button", { name: /QA Review/ }).click();
  await page.getByRole("button", { name: "Run Right Row 1, 8 frames" }).click();

  const player = page.getByTestId("sprite-state-animation");
  await expect(player).toHaveAttribute("data-frame-index", "0");
  await page.clock.fastForward(10_000);
  await expect(player).toHaveAttribute("data-frame-index", "0");
});

test("demo refresh is safe and recorded without a backend", async ({ page }) => {
  await startDemo(page);

  await page.getByRole("button", { name: "Refresh project state" }).click();
  await page.getByRole("button", { name: "Toggle activity drawer" }).click();

  await expect(page.getByRole("complementary", { name: "Activity drawer" })).toContainText("Demo refreshed");
});

test("approval interaction updates gate and activity", async ({ page }) => {
  await startDemo(page);
  await page.keyboard.press("6");

  await page.getByRole("button", { name: "Approve visual review" }).click();
  await expect(page.getByRole("banner").getByText("Ready to export")).toBeVisible();
  await page.getByRole("button", { name: "Open details" }).click();
  await expect(page.getByLabel("Details drawer").getByText("Ready", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Close details" }).click();

  await page.getByRole("button", { name: "Toggle activity drawer" }).click();
  await expect(page.getByRole("complementary", { name: "Activity drawer" })).toContainText("Approval recorded");
});

test("operational controls call the shared v2 project actions", async ({ page }) => {
  const state = JSON.parse(JSON.stringify(demoProjectState)) as ProjectState;
  state.project_id = "v2-operations-project";
  state.project_dir = "/private/v2-operations-project";
  state.manifest = {
    ...state.manifest,
    display_name: "V2 Operations",
    sprite_version_number: 2,
    output_contract: {
      contract_id: "codex-pet-v2",
      rows: 11,
      columns: 8,
      cell_width: 192,
      cell_height: 208
    }
  };
  state.gate = { ...state.gate, stage: "generation_planned", install_ready: false };
  state.direction_review = null;
  state.likeness = { status: "pending", verdicts: [] };

  const actionPayloads = new Map<string, Record<string, unknown>>();
  await page.route("**/api/projects/open", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ project_id: state.project_id, project_dir: state.project_dir })
    });
  });
  await page.route("**/api/projects/v2-operations-project/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/state")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
      return;
    }
    actionPayloads.set(path, route.request().postDataJSON() as Record<string, unknown>);
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /Open a project/ }).click();
  await page.getByLabel("Project directory").fill(state.project_dir);
  await page.getByRole("button", { name: "Open project", exact: true }).click();

  await page.getByRole("button", { name: "Generate ready handoffs" }).click();
  expect(actionPayloads.get("/api/projects/v2-operations-project/generation/handoff")?.all_jobs).toBe(true);

  await page.getByLabel("Generated output JSON").fill('{"idle":"/private/generated/idle.png"}');
  await page.getByRole("button", { name: "Import ready outputs" }).click();
  expect(
    (actionPayloads.get("/api/projects/v2-operations-project/generation/import")?.mapping as Record<string, string>).idle
  ).toBe("/private/generated/idle.png");

  await page.getByLabel("Visible problem and intended correction").fill("Preserve the left ear marking.");
  await page.getByRole("button", { name: "Archive and repair selected scope" }).click();
  expect(actionPayloads.get("/api/projects/v2-operations-project/repair")?.job_ids).toEqual(["row-idle"]);

  await page.getByRole("button", { name: "Recover interrupted run" }).click();
  expect(actionPayloads.has("/api/projects/v2-operations-project/recover")).toBe(true);

  await page.getByRole("button", { name: "Build final review" }).click();
  expect(actionPayloads.get("/api/projects/v2-operations-project/review/build")?.row_provenance).toBe("provider_generated");

  await page.keyboard.press("1");
  const sourcePolicy = page.locator(".source-role-editor").first();
  await sourcePolicy.getByLabel("Reference roles").fill("identity_front, marking_detail");
  await sourcePolicy.getByLabel("openai_images").check();
  await sourcePolicy.getByRole("button", { name: "Save source policy" }).click();
  expect(actionPayloads.get("/api/projects/v2-operations-project/sources/source-001/roles")?.roles).toEqual([
    "identity_front",
    "marking_detail"
  ]);

  await page.keyboard.press("3");
  const candidate = page.locator(".decision-card.candidate").filter({ hasText: "baseline-002" });
  await candidate.getByLabel("Holistic gestalt (1–5)").fill("4.5");
  await candidate.getByLabel("Signature traits (1–5)").fill("4");
  await candidate.getByLabel("Small-size readability (1–5)").fill("4");
  await candidate.getByLabel("Source-linked review notes").fill("Head, body, coat, and marking evidence match the source.");
  await candidate.getByRole("button", { name: "Record likeness evidence" }).click();
  expect(
    actionPayloads.get("/api/projects/v2-operations-project/candidates/baseline-002/review")?.holistic_gestalt_score
  ).toBe(4.5);

  await page.keyboard.press("4");
  await page.getByRole("button", { name: "anime" }).click();
  await page.getByRole("button", { name: "Save style contract" }).click();
  expect(actionPayloads.get("/api/projects/v2-operations-project/style/default")?.preset).toBe("anime");
});

test("v2 review requires explicit animation, direction, and likeness evidence before approval", async ({ page }) => {
  let state = JSON.parse(JSON.stringify(demoProjectState)) as ProjectState;
  state = {
    ...state,
    project_id: "v2-review-project",
    project_dir: "/private/v2-review-project",
    manifest: {
      ...state.manifest,
      id: "v2-review-project",
      display_name: "V2 Review Project",
      sprite_version_number: 2,
      output_contract: {
        contract_id: "codex-pet-v2",
        rows: 11,
        columns: 8,
        cell_width: 192,
        cell_height: 208
      }
    },
    gate: {
      ...state.gate,
      stage: "built_for_review",
      install_ready: false
    },
    qa: {
      run_id: "demo",
      stage: "built_for_review",
      install_policy: { ok_to_install: false, hard_failures: [], warnings: [] },
      review_gates: {
        animation_ok: false,
        direction_semantics_complete: false,
        likeness_complete: false,
        all_reviews_complete: false
      }
    },
    likeness: { status: "pending", verdicts: [] },
    animation_review: null,
    direction_review: null
  };
  state.artifacts = state.artifacts.map((artifact) =>
    artifact.relative_path.endsWith("spritesheet.webp")
      ? { ...artifact, width: 1536, height: 2288 }
      : artifact
  );

  let animationCount = 0;
  let directionCount = 0;
  let likenessCount = 0;
  let approvalDecision = "";
  let exportedKind = "";
  let installedRoot = "";
  await page.route("**/api/projects/open", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ project_id: state.project_id, project_dir: state.project_dir })
    });
  });
  await page.route("**/api/projects/v2-review-project/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/state")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
      return;
    }
    if (path.endsWith("/animation/review")) {
      const animationPayload = route.request().postDataJSON() as Record<string, unknown>;
      animationCount = (animationPayload.verdicts as unknown[]).length;
      state = {
        ...state,
        animation_review: { status: "approved", verdicts: animationPayload.verdicts },
        qa: {
          ...state.qa,
          review_gates: {
            animation_ok: true,
            direction_semantics_complete: false,
            likeness_complete: false,
            all_reviews_complete: false
          }
        }
      };
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
      return;
    }
    if (path.endsWith("/review/directions")) {
      const directionPayload = route.request().postDataJSON() as Record<string, unknown>;
      directionCount = (directionPayload.directions as unknown[]).length;
      state = {
        ...state,
        direction_review: { status: "reviewed", directions: directionPayload.directions },
        qa: {
          ...state.qa,
          review_gates: {
            animation_ok: true,
            direction_semantics_complete: true,
            likeness_complete: false,
            all_reviews_complete: false
          }
        }
      };
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
      return;
    }
    if (path.endsWith("/review/likeness")) {
      const likenessPayload = route.request().postDataJSON() as Record<string, unknown>;
      likenessCount = (likenessPayload.verdicts as unknown[]).length;
      state = {
        ...state,
        likeness: { status: "approved", verdicts: likenessPayload.verdicts },
        qa: {
          ...state.qa,
          review_gates: {
            animation_ok: true,
            direction_semantics_complete: true,
            likeness_complete: true,
            all_reviews_complete: true
          }
        }
      };
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
      return;
    }
    if (path.endsWith("/approval")) {
      const approvalPayload = route.request().postDataJSON() as Record<string, unknown>;
      approvalDecision = String(approvalPayload.decision);
      state = {
        ...state,
        gate: { ...state.gate, stage: "visually_approved", install_ready: true }
      };
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
      return;
    }
    if (path.endsWith("/export")) {
      const exportPayload = route.request().postDataJSON() as Record<string, unknown>;
      exportedKind = String(exportPayload.kind);
      state = {
        ...state,
        exports: [
          {
            id: "exports-petdex-zip",
            kind: "export",
            label: "v2-review-project-petdex.zip",
            relative_path: "exports/v2-review-project-petdex.zip",
            url: "/api/projects/v2-review-project/artifacts/exports-petdex-zip",
            exists: true,
            width: null,
            height: null,
            bytes: 1024,
            modified_at: "now",
            stage: "approval",
            state: null,
            severity: "success"
          }
        ]
      };
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
      return;
    }
    if (path.endsWith("/finish")) {
      const finishPayload = route.request().postDataJSON() as Record<string, unknown>;
      installedRoot = String(finishPayload.install_root);
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(state) });
      return;
    }
    await route.abort();
  });

  await page.goto("/");
  await page.getByRole("button", { name: /Open a project/ }).click();
  await page.getByLabel("Project directory").fill("/private/v2-review-project");
  await page.getByRole("button", { name: "Open project", exact: true }).click();

  const approval = page.getByRole("button", { name: "Approve visual review" });
  await expect(page.getByRole("heading", { name: "V2 Review Project" })).toBeVisible();
  await expect(page.getByText("Nine-state animation correctness")).toBeVisible();
  await expect(page.getByText("16-direction semantics")).toBeVisible();
  await expect(page.getByText(/pass all/)).toBeVisible();
  await expect(approval).toBeDisabled();

  const animationLabels = [
    "Idle", "Run right", "Run left", "Waving", "Jumping", "Failed", "Waiting", "Active task", "Review"
  ];
  for (const [index, label] of animationLabels.entries()) {
    const fieldset = page.locator(".animation-verdict").nth(index);
    await fieldset.getByLabel("Verdict").selectOption("pass");
    await fieldset.getByLabel("State meaning evidence").fill(`${label} has the intended state-specific gesture`);
    await fieldset.getByLabel("Motion continuity evidence").fill(`${label} advances coherently and closes its loop`);
    await fieldset.getByLabel("Identity consistency evidence").fill(`${label} preserves the same face and proportions`);
  }
  await page.getByRole("button", { name: "Record nine animation verdicts" }).click();
  expect(animationCount).toBe(9);
  await expect(approval).toBeDisabled();

  const directionLabels = [
    "000", "022.5", "045", "067.5", "090", "112.5", "135", "157.5",
    "180", "202.5", "225", "247.5", "270", "292.5", "315", "337.5"
  ];
  for (const direction of directionLabels) {
    const fieldset = page.locator(".direction-verdict").filter({ hasText: `${direction}°` });
    await fieldset.getByLabel("Verdict").selectOption("pass");
    await fieldset.getByLabel("Visible evidence").fill(`Visible pose evidence for ${direction} degrees`);
  }
  await page.getByRole("button", { name: "Record 16 semantic verdicts" }).click();
  await expect(page.getByText("Reviewed", { exact: true })).toBeVisible();
  expect(directionCount).toBe(16);
  await expect(approval).toBeDisabled();

  const likenessTraits = state.identity_profile?.traits as Array<Record<string, unknown>>;
  for (const [index, trait] of likenessTraits.entries()) {
    const traitId = String(trait.id);
    const row = page.locator(".likeness-trait").nth(index);
    await row.locator("select").selectOption("pass");
    await row.getByPlaceholder(/What in the source and final pet/).fill(`Source-linked evidence for ${traitId}`);
  }
  await page.getByRole("button", { name: "Record per-trait review" }).click();
  expect(likenessCount).toBe(2);
  await expect(approval).toBeEnabled();

  await approval.click();
  expect(approvalDecision).toBe("approved");
  await expect(page.getByRole("banner").getByText("Ready to export")).toBeVisible();

  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByLabel("Output directory (optional)").fill("/private/exports");
  await page.getByRole("button", { name: "Export approved package" }).click();
  expect(exportedKind).toBe("petdex");
  await expect(page.getByLabel("Created exports")).toContainText("v2-review-project-petdex.zip");

  await page.getByLabel("Codex package root").fill("/private/codex/pets");
  await page.getByRole("button", { name: "Finish and install" }).click();
  expect(installedRoot).toBe("/private/codex/pets");
});
