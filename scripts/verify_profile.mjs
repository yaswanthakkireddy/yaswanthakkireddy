import { chromium } from 'playwright';
import { mkdir, writeFile, appendFile } from 'node:fs/promises';
import { setTimeout as delay } from 'node:timers/promises';

// This is a read-only check of the public, live GitHub profile.
const profileUrl = 'https://github.com/yaswanthakkireddy';
const outputDirectory = 'profile-verification';
const headings = [
  'Yaswanth Kumar Akkireddy',
  'Engineering Profile',
  'Flagship Systems',
  'Reliability-first AI Engineering',
  'Supporting Systems',
  'Engineering Telemetry',
  'More Work',
];
const configurations = [
  { name: 'desktop-light', viewport: { width: 1280, height: 1000 }, colorScheme: 'light' },
  { name: 'desktop-dark', viewport: { width: 1280, height: 1000 }, colorScheme: 'dark' },
  { name: 'mobile-light', viewport: { width: 390, height: 844 }, colorScheme: 'light', isMobile: true, hasTouch: true },
];
const report = {
  url: profileUrl,
  checkedAt: new Date().toISOString(),
  commit: process.env.GITHUB_SHA ?? null,
  viewports: [],
};
const errors = [];
await mkdir(outputDirectory, { recursive: true });
const browser = await chromium.launch();

function headingLocator(readme, name) {
  return readme.getByRole('heading', { name, exact: true });
}

async function capture(page, name, target) {
  if (target && await target.count()) {
    await target.evaluate(element => {
      window.scrollTo({ top: Math.max(0, element.getBoundingClientRect().top + window.scrollY - 60), behavior: 'instant' });
    });
  }
  await page.evaluate(() => document.fonts.ready);
  let screenshot;
  // Keep the public JPEG previews small enough to inspect through job logs.
  for (const quality of [62, 48, 36]) {
    screenshot = await page.screenshot({ type: 'jpeg', quality, animations: 'disabled', scale: 'css', fullPage: false });
    if (screenshot.length <= 120_000) break;
  }
  await writeFile(outputDirectory + '/' + name + '.jpg', screenshot);
  console.log('CODEX_SCREENSHOT:' + name + ':' + screenshot.toString('base64'));
  return { name, bytes: screenshot.length, scrollY: await page.evaluate(() => window.scrollY) };
}

async function loadProfile(page, retryForPublication) {
  const deadline = Date.now() + (retryForPublication ? 90_000 : 35_000);
  let lastError;
  do {
    try {
      const response = await page.goto(profileUrl, { waitUntil: 'domcontentloaded', timeout: Math.max(1, Math.min(30_000, deadline - Date.now())) });
      if (!response?.ok()) throw new Error('Profile returned HTTP ' + response?.status());
      const readme = page.locator('article.markdown-body').filter({
        has: page.getByRole('heading', { name: headings[0], exact: true }),
      }).first();
      await headingLocator(readme, 'Engineering Telemetry').waitFor({ state: 'visible', timeout: Math.max(1, Math.min(5_000, deadline - Date.now())) });
      return readme;
    } catch (error) {
      lastError = error;
      if (Date.now() + 10_000 >= deadline) break;
      console.log('Waiting for the published profile README to appear.');
      await delay(10_000);
    }
  } while (Date.now() < deadline);
  throw lastError;
}

try {
  for (const [index, configuration] of configurations.entries()) {
    const context = await browser.newContext({
      viewport: configuration.viewport,
      colorScheme: configuration.colorScheme,
      isMobile: configuration.isMobile ?? false,
      hasTouch: configuration.hasTouch ?? false,
      deviceScaleFactor: 1,
      locale: 'en-US',
      reducedMotion: 'reduce',
    });
    const page = await context.newPage();
    page.setDefaultTimeout(12_000);
    const result = { name: configuration.name, viewport: configuration.viewport, screenshots: [], failures: [] };
    report.viewports.push(result);
    try {
      const readme = await loadProfile(page, index === 0);
      result.headings = await readme.locator('h1, h2, h3').allTextContents();
      for (const name of headings) {
        if (!await headingLocator(readme, name).count()) result.failures.push('Missing heading: ' + name);
      }

      await readme.locator('details').evaluateAll(elements => elements.forEach(element => { element.open = true; }));
      // Scroll every README image into view so lazy images are genuinely loaded.
      const images = readme.locator('img');
      for (let imageIndex = 0; imageIndex < await images.count(); imageIndex++) {
        const image = images.nth(imageIndex);
        await image.scrollIntoViewIfNeeded();
        await image.evaluate(element => new Promise(resolve => {
          if (element.complete) return resolve();
          const timeout = setTimeout(resolve, 12_000);
          const finish = () => { clearTimeout(timeout); resolve(); };
          element.addEventListener('load', finish, { once: true });
          element.addEventListener('error', finish, { once: true });
        }));
      }
      result.images = await images.evaluateAll(elements => elements.map(element => ({
        alt: element.alt,
        source: element.currentSrc || element.src,
        complete: element.complete,
        naturalWidth: element.naturalWidth,
        renderedWidth: Math.round(element.getBoundingClientRect().width),
      })));
      if (result.images.length === 0) result.failures.push('No README images were rendered.');
      for (const image of result.images) {
        if (!image.complete || image.naturalWidth <= 0) result.failures.push('Unloaded image: ' + image.alt);
      }

      const toscoLink = readme.locator('a[href="https://github.com/yaswanthakkireddy/TOSCO"]').first();
      if (!await toscoLink.count()) result.failures.push('Missing featured TOSCO project.');
      if (configuration.isMobile && !result.images.some(image => image.source.includes('hero-mobile.svg'))) {
        result.failures.push('Mobile hero asset was not selected.');
      }
      if (configuration.isMobile && !result.images.some(image => image.source.includes('tosco-mobile.svg'))) {
        result.failures.push('Mobile TOSCO asset was not selected.');
      }
      const heroSource = result.images.find(image => image.alt.startsWith('Call me Yaswanth'))?.source;
      if (!heroSource) result.failures.push('Portrait header was not rendered.');
      else {
        const heroResponse = await page.request.get(heroSource);
        const svg = await heroResponse.text();
        result.portrait = { embeddedAvatar: /<image[^>]+href="data:image\//.test(svg), motionElements: (svg.match(/<animate(?:Motion|Transform)?\b/g) || []).length };
        if (!result.portrait.embeddedAvatar || result.portrait.motionElements < 3) result.failures.push('Portrait or self-contained motion is missing.');
      }
      result.layout = await readme.evaluate(element => {
        const rect = element.getBoundingClientRect();
        return {
          viewportWidth: window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          readmeWidth: Math.round(rect.width),
          readmeScrollWidth: element.scrollWidth,
          readmeClientWidth: element.clientWidth,
          rightEdge: Math.round(rect.right),
          colorMode: document.documentElement.getAttribute('data-color-mode'),
          bodyBackground: getComputedStyle(document.body).backgroundColor,
        };
      });
      if (result.layout.documentWidth > result.layout.viewportWidth + 2) {
        result.failures.push('Page has horizontal overflow.');
      }
      if (result.layout.readmeScrollWidth > result.layout.readmeClientWidth + 2 ||
          result.layout.rightEdge > result.layout.viewportWidth + 2) {
        result.failures.push('Profile README has horizontal overflow.');
      }
      const background = result.layout.bodyBackground.match(/[\d.]+/g)?.slice(0, 3).map(Number);
      if (background?.length === 3) {
        const brightness = (background[0] * 299 + background[1] * 587 + background[2] * 114) / 1000;
        if ((configuration.colorScheme === 'dark' && brightness > 128) ||
            (configuration.colorScheme === 'light' && brightness < 128)) {
          result.failures.push('GitHub did not render the requested ' + configuration.colorScheme + ' theme.');
        }
      }

      const sections = configuration.isMobile
        ? [['top', headings[0]], ['engineering', 'Engineering Profile'], ['flagship', 'Flagship Systems'], ['supporting', 'Supporting Systems'], ['telemetry', 'Engineering Telemetry']]
        : [
          ['top', headings[0]],
          ['engineering', 'Engineering Profile'],
          ['flagship', 'Flagship Systems'],
          ['reliability', 'Reliability-first AI Engineering'],
          ['supporting', 'Supporting Systems'],
          ['telemetry', 'Engineering Telemetry'],
        ];
      for (const [section, heading] of sections) {
        try {
          result.screenshots.push(await capture(page, configuration.name + '-' + section, headingLocator(readme, heading)));
        } catch (error) {
          result.failures.push('Screenshot ' + section + ': ' + error.message);
        }
      }
    } catch (error) {
      result.failures.push(error.message);
      try {
        result.screenshots.push(await capture(page, configuration.name + '-failure'));
      } catch (captureError) {
        result.failures.push('Failure screenshot: ' + captureError.message);
      }
    } finally {
      await context.close();
    }
    errors.push(...result.failures.map(message => configuration.name + ': ' + message));
    console.log('CODEX_CHECK:' + JSON.stringify(result));
  }
} finally {
  await browser.close();
  report.passed = errors.length === 0;
  await writeFile(outputDirectory + '/report.json', JSON.stringify(report, null, 2) + '\n');
  const summary = [
    '## Live GitHub profile verification',
    '',
    '[Public profile](' + profileUrl + ')',
    '',
    'Result: **' + (report.passed ? 'passed' : 'needs review') + '**',
    '',
    'Checked desktop light, desktop dark, and mobile light. Screenshots and the image/layout report are in the profile-verification artifact.',
    'These screenshots come from the live GitHub profile, not a local rendering.',
    '',
    ...errors.map(error => '- ' + error.replace(/\n/g, ' ')),
    '',
  ].join('\n');
  if (process.env.GITHUB_STEP_SUMMARY) await appendFile(process.env.GITHUB_STEP_SUMMARY, summary);
  console.log('CODEX_RESULT:' + JSON.stringify({ passed: report.passed, errors }));
}
if (errors.length) process.exitCode = 1;
