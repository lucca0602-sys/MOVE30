// Peças compartilhadas entre o cadastro (index.html) e o dash pessoal (dash.html).
// Todo texto vindo da API/IA entra via textContent (nunca innerHTML).
(function () {
  "use strict";
  const { PUBLIC_API, buscar } = window.MOVE30_FONTE;

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  };

  async function buscarResultado(token) {
    try {
      return (await buscar(`resultado/${encodeURIComponent(token)}`)).dados;
    } catch (erro) {
      if (erro.naoEncontrado) erro.message = "Resultado não encontrado. Confira se o link está completo.";
      throw erro;
    }
  }

  // Bloco da análise da IA: perfil, mensagem, destaque e recomendação.
  function renderAnalise(container, analise) {
    container.replaceChildren();
    const bloco = el("div", "analise");
    bloco.append(el("h2", "analise__titulo", "Sua análise"));
    if (analise.perfil) bloco.append(el("p", "analise__perfil", analise.perfil));
    if (analise.mensagem) {
      analise.mensagem.split(/\n{2,}/).forEach((paragrafo) => {
        if (paragrafo.trim()) bloco.append(el("p", "analise__texto", paragrafo.trim()));
      });
    }
    const pontos = el("div", "analise__pontos");
    [["destaque", "Ponto forte", "analise__ponto--forte"], ["oportunidade", "Dica prática", "analise__ponto--dica"]].forEach(([campo, rotulo, classe]) => {
      if (!analise[campo]) return;
      const item = el("div", `analise__ponto ${classe}`);
      item.append(el("h3", "analise__ponto-titulo", rotulo), el("p", "", analise[campo]));
      pontos.append(item);
    });
    if (pontos.childElementCount) bloco.append(pontos);
    container.append(bloco);
  }

  // Mensagens que giram enquanto a IA trabalha (CPU: ~1-2 min).
  const MENSAGENS_ESPERA = [
    "A IA está olhando seu IMC e seus batimentos.",
    "Comparando com as faixas de referência...",
    "Separando dicas práticas para a sua rotina...",
    "Escrevendo uma mensagem só para você...",
    "Quase lá! Análise caprichada leva um tempinho.",
  ];
  function iniciarMensagensEspera(node) {
    let i = 0;
    node.textContent = MENSAGENS_ESPERA[0];
    return setInterval(() => {
      i = (i + 1) % MENSAGENS_ESPERA.length;
      node.textContent = MENSAGENS_ESPERA[i];
    }, 6000);
  }

  // Consulta até a análise ficar pronta (ou desistir com mensagem amigável).
  async function aguardarAnalise(token, { aoAtualizar, intervaloMs = 4000, limiteMs = 8 * 60 * 1000 } = {}) {
    const inicio = Date.now();
    for (;;) {
      let resultado = null;
      try {
        resultado = await buscarResultado(token);
        aoAtualizar?.(resultado);
        if (resultado.status === "pronto") return resultado;
      } catch (erro) {
        if (erro.naoEncontrado) throw erro;
        // Falha de rede momentânea: tenta de novo.
      }
      if (Date.now() - inicio > limiteMs) return resultado;
      await new Promise((resolve) => setTimeout(resolve, intervaloMs));
    }
  }

  function linkDash(token) {
    return `${window.location.origin}/dash/${encodeURIComponent(token)}`;
  }

  function desenharQr(container, texto) {
    const qr = window.qrcode(0, "M");
    qr.addData(texto);
    qr.make();
    // SVG gerado pela própria lib a partir do texto do link (sem conteúdo do usuário).
    container.innerHTML = qr.createSvgTag({ cellSize: 6, margin: 2, scalable: true });
  }

  window.MOVE30 = { PUBLIC_API, el, buscarResultado, renderAnalise, iniciarMensagensEspera, aguardarAnalise, linkDash, desenharQr };
})();
