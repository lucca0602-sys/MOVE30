// Arquivo pós-feira (PC do evento desligado): lê do Postgres da nuvem (Neon) o que
// scripts/publicar_resultados.py publicou. Arquivos com "_" na pasta api/ não viram rota.
// ARQUIVO_DATABASE_URL fica só nas variáveis de ambiente da Vercel (de preferência um
// usuário só-leitura); nunca no repositório.
import pg from "pg";

let pool = null;

export function banco() {
  const url = (process.env.ARQUIVO_DATABASE_URL || "").trim();
  if (!url) return null;
  // Uma conexão por instância: a função é curta e o Neon free tem poucas conexões.
  pool ??= new pg.Pool({ connectionString: url, max: 1, idleTimeoutMillis: 10_000 });
  return pool;
}

export function responder(res, status, corpo, cacheS = 0) {
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  // Dado só muda quando o script publica de novo: CDN segura 5 min, serve velho por 1 dia se o banco cair.
  res.setHeader("Cache-Control", cacheS ? `public, max-age=60, s-maxage=${cacheS}, stale-while-revalidate=86400` : "no-store");
  res.status(status).send(JSON.stringify(corpo));
}

// montar(linha) devolve o JSON da resposta, ou null para 404.
export async function consultar(res, sql, params, montar) {
  const db = banco();
  if (!db) return responder(res, 503, { detail: "Arquivo não configurado." });
  try {
    const { rows } = await db.query(sql, params);
    // Nada publicado ainda (tabela vazia): 503, para o front seguir tentando o backend ao vivo.
    if (!rows.length) return responder(res, 503, { detail: "Arquivo ainda não publicado." });
    const corpo = montar(rows[0]);
    if (corpo === null) return responder(res, 404, { detail: "Resultado não encontrado." }, 300);
    return responder(res, 200, corpo, 300);
  } catch (erro) {
    console.error("arquivo:", erro.message);
    return responder(res, 503, { detail: "Arquivo indisponível." });
  }
}
