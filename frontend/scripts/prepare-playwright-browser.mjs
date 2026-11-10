import { existsSync, mkdirSync, rmSync, symlinkSync } from 'node:fs';
import { resolve } from 'node:path';
import { inflate } from '@sparticuz/chromium';

const chromiumArchive = resolve('node_modules/@sparticuz/chromium/bin/chromium.br');
const executablePath = await inflate(chromiumArchive);
rmSync(resolve('.next-playwright'), { force: true, recursive: true });

for (const revision of ['1009', '1010', '1011']) {
  const directory = `/tmp/.cache/ms-playwright/ffmpeg-${revision}`;
  const link = `${directory}/ffmpeg-linux`;
  mkdirSync(directory, { recursive: true });
  if (!existsSync(link)) symlinkSync('/usr/bin/ffmpeg', link);
}

process.stdout.write(`${executablePath}\n`);
