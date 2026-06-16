// scripts/build-icons.mjs — regenera os PNGs do ícone a partir dos SVGs em public/.
// Node 22. Requer: npm i -D sharp   →   roda com: yarn icons
import sharp from "sharp";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const pub = resolve(root, "public");

const full = readFileSync(resolve(pub, "icon.svg"));
const mask = readFileSync(resolve(pub, "icon-maskable.svg"));

const jobs = [
  { svg: full, out: "icon-1024.png", size: 1024 },
  { svg: full, out: "icon-512.png", size: 512 },
  { svg: full, out: "icon-192.png", size: 192 },
  { svg: full, out: "apple-touch-icon.png", size: 180 },
  { svg: full, out: "favicon-32.png", size: 32 },
  { svg: full, out: "favicon-16.png", size: 16 },
  { svg: mask, out: "icon-512-maskable.png", size: 512 },
  { svg: mask, out: "icon-192-maskable.png", size: 192 },
];

try {
  for (const { svg, out, size } of jobs) {
    await sharp(svg, { density: 384 })
      .resize(size, size, { fit: "cover" })
      .png({ compressionLevel: 9 })
      .toFile(resolve(pub, out));
    console.log(`✓ ${out} (${size}px)`);
  }
  console.log("Icones regenerados em public/.");
} catch (err) {
  console.error("Falha ao gerar icones:", err);
  process.exit(1);
}
