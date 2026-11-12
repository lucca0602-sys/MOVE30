// De onde vêm os dados públicos: primeiro o backend ao vivo do evento (Funnel); se ele não
// responder (PC desligado depois da feira), o arquivo publicado na Vercel (/api/...).
(function () {
  "use strict";
  const config = window.MOVE30_CONFIG || {};
  // "" = mesma origem (servidor local do plano B repassa /public para o app público).
  const PUBLIC_API = String(config.publicApiBaseUrl ?? "http://127.0.0.1:8003").replace(/\/$/, "");

  async function tentar(url, limiteMs) {
    const controle = new AbortController();
    const timer = setTimeout(() => controle.abort(), limiteMs);
    try {
      return await fetch(url, { cache: "no-store", headers: { Accept: "application/json" }, signal: controle.signal });
    } catch {
      return null; // rede, Funnel fora do ar, tempo esgotado
    } finally {
      clearTimeout(timer);
    }
  }

  // caminho: "resultado/<token>" ou "coletivo". Devolve { dados, origem: "vivo" | "arquivo" }.
  // naoEncontrado=true quando o backend ao vivo diz que o token não existe, ou quando o arquivo
  // (já publicado) não tem o token. Antes de publicar o arquivo responde 503: durante a feira
  // um tropeço do Funnel não vira "link inválido", só nova tentativa.
  async function buscar(caminho) {
    const vivo = await tentar(`${PUBLIC_API}/public/${caminho}`, 5000);
    if (vivo?.ok) return { dados: await vivo.json(), origem: "vivo" };
    const arquivo = await tentar(`/api/${caminho}`, 10000);
    if (arquivo?.ok) return { dados: await arquivo.json(), origem: "arquivo" };
    const erro = new Error("O servidor do MOVE 30 não respondeu. Tente de novo em instantes.");
    erro.naoEncontrado = vivo?.status === 404 || vivo?.status === 422 || arquivo?.status === 404;
    throw erro;
  }

  window.MOVE30_FONTE = { PUBLIC_API, buscar };
})();
