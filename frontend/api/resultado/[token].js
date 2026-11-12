// GET /api/resultado/<token>: mesmo JSON do /public/resultado/<token> do backend do evento.
import { consultar, responder } from "../_arquivo.js";

const TOKEN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function handler(req, res) {
  if (req.method !== "GET") return responder(res, 405, { detail: "Método não permitido." });
  const token = String(req.query.token || "");
  if (!TOKEN.test(token)) return responder(res, 404, { detail: "Resultado não encontrado." });
  // 404 só depois de publicado: antes disso o token pode simplesmente ser novo, ainda no backend do evento.
  return consultar(
    res,
    "SELECT (SELECT dados FROM resultados_publicos WHERE token_publico = $1) AS dados FROM painel_publico WHERE id = 1;",
    [token],
    (r) => r.dados,
  );
}
