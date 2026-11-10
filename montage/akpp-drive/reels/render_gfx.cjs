// Render gfx.html frame by frame into a transparent PNG sequence: node render_gfx.js <build_dir> [frames...]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const B = process.argv[2], out = path.join(B, 'gfx');
  fs.mkdirSync(out, { recursive: true });
  const tl = JSON.parse(fs.readFileSync(path.join(B, 'gfx.json')));
  const only = process.argv.slice(3).map(Number);
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'gfx.html'));
  await page.evaluate(tl => window.setup(tl), tl);
  const n = Math.round(tl.total * tl.fps);
  const frames = only.length ? only : [...Array(n).keys()];
  for (const i of frames) {
    const url = await page.evaluate(i => window.frame(i), i);
    fs.writeFileSync(path.join(out, String(i).padStart(5, '0') + '.png'), Buffer.from(url.split(',')[1], 'base64'));
  }
  await browser.close();
  console.log('gfx frames', frames.length);
})();
