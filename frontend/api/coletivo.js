// GET /api/coletivo: agregados do /geral congelados na última publicação (mesmo formato do /public/coletivo).
import { consultar, responder } from "./_arquivo.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return responder(res, 405, { detail: "Método não permitido." });
  return consultar(res, "SELECT dados, publicado_em FROM painel_publico WHERE id = 1;", [],
    (r) => ({ ...r.dados, arquivo: true, publicado_em: r.publicado_em }));
}
