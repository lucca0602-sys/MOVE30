// Roda no build da Vercel: grava js/config.js com a URL do back-end vinda da variável de ambiente.
// Sem MOVE30_API_URL (uso local), mantém o config.js do repositório.
import { writeFileSync } from "node:fs";

const apiBaseUrl = (process.env.MOVE30_API_URL || "").trim().replace(/\/$/, "");
if (!apiBaseUrl) {
  console.warn("MOVE30_API_URL não definida: mantendo js/config.js local.");
  process.exit(0);
}
if (!/^https:\/\//.test(apiBaseUrl)) {
  console.error("MOVE30_API_URL precisa começar com https:// (ex.: https://pc.tail1234.ts.net).");
  process.exit(1);
}

writeFileSync(
  new URL("./js/config.js", import.meta.url),
  `window.MOVE30_CONFIG = {\n  apiBaseUrl: "http://127.0.0.1:8002",\n  publicApiBaseUrl: ${JSON.stringify(apiBaseUrl)},\n  dashboardBaseUrl: "http://127.0.0.1:8501"\n};\n`,
);
console.log(`config.js gerado: publicApiBaseUrl=${apiBaseUrl}`);
