// Entry for make.fun's news-image-20261122: "Sum up 22 November's world news in one image".
// entry.png is rendered ahead of time from src/front.html (tools/render.ps1). At grading time there is
// no network, so this program only copies those exact bytes to /output/entry.png; both runs match.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const png = readFileSync(new URL('./entry.png', import.meta.url));

// The contest takes a whole PNG or JPEG of at most 1 MiB and 1024 x 1024 pixels: refuse anything else
// rather than hand the gate a file it will mark invalid.
const signature = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
if (!signature.every((b, i) => png[i] === b)) throw new Error('entry.png is not a PNG');
if (png.length > 1048576) throw new Error(`entry.png is ${png.length} bytes, over 1 MiB`);
const width = png.readUInt32BE(16);
const height = png.readUInt32BE(20);
if (width > 1024 || height > 1024) throw new Error(`entry.png is ${width}x${height}, over 1024x1024`);
const iend = png.subarray(png.length - 8, png.length - 4).toString('latin1');
if (iend !== 'IEND') throw new Error('entry.png does not end with its IEND chunk');

const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
mkdirSync(outDir, { recursive: true });
writeFileSync(join(outDir, 'entry.png'), png);
