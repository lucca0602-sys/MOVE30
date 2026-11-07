(function () {
  "use strict";
  const M = window.MOVE30;
  const $ = (id) => document.getElementById(id);
  const fmt = (v, casas, sufixo) => v === null || v === undefined ? "—" : `${Number(v).toFixed(casas).replace(".", ",")}${sufixo}`;
  const pct = (v, min, max) => `${Math.min(100, Math.max(0, ((v - min) / (max - min)) * 100))}%`;

  // /dash/<token> (Vercel e servidor local) ou dash.html?t=<token>
  const token = decodeURIComponent(window.location.pathname.split("/dash/")[1] || "").replace(/\/$/, "")
    || new URLSearchParams(window.location.search).get("t") || "";

  function erro(mensagem) {
    $("estado").hidden = false;
    $("estado").querySelector(".carregando").hidden = true;
    $("estado-msg").textContent = mensagem;
    $("conteudo").hidden = true;
    $("status-pill").textContent = "Indisponível";
    $("status-pill").classList.add("pill--off");
  }

  // Gráficos só nascem com o conteúdo visível (canvas escondido fica com tamanho zero).
  const G = window.MOVE30_GRAFICOS;
  let graficos = null;
  let ultimaComparacao = 0;
  function desenharGraficos(r) {
    if (!graficos) {
      graficos = {
        imc: G.velocimetro($("g-imc"), { min: 14, max: 40, zonas: G.ZONAS_IMC, casas: 1 }),
        fc: G.velocimetro($("g-fc"), { min: 40, max: 130, zonas: G.ZONAS_FC, sufixo: " bpm" }),
        comparacao: null,
      };
    }
    graficos.imc.atualizar(r.imc);
    graficos.fc.atualizar(r.fc_repouso);
    // Média do grupo: só agregados do /public/coletivo; atualiza no máximo a cada 30 s.
    if (Date.now() - ultimaComparacao > 30000) {
      ultimaComparacao = Date.now();
      fetch(`${M.PUBLIC_API}/public/coletivo`, { cache: "no-store" })
        .then((resp) => (resp.ok ? resp.json() : null))
        .then((g) => {
          const imcGrupo = g?.medias?.imc?.valor, fcGrupo = g?.medias?.fc_repouso?.valor;
          if (imcGrupo == null || fcGrupo == null || r.imc == null || r.fc_repouso == null) return;
          $("bloco-comparacao").hidden = false;
          if (!graficos.comparacao) {
            graficos.comparacao = {
              imc: G.comparacao($("g-comp-imc"), { titulo: "IMC", casas: 1 }),
              fc: G.comparacao($("g-comp-fc"), { titulo: "Batimentos em repouso", sufixo: " bpm" }),
            };
          }
          graficos.comparacao.imc.atualizar(r.imc, imcGrupo);
          graficos.comparacao.fc.atualizar(r.fc_repouso, fcGrupo);
          $("comparacao-nota").textContent = `Média de ${g.medias.imc.n} pessoas avaliadas no MOVE 30 até agora (IMC ${fmt(imcGrupo, 1, "")} · ${fmt(fcGrupo, 0, " bpm")}).`;
        })
        .catch(() => {});
    }
  }

  let analiseMostrada = false;
  function render(r) {
    $("estado").hidden = true;
    $("conteudo").hidden = false;
    $("ola").textContent = `Olá, ${r.primeiro_nome}!`;
    $("sub").textContent = r.criado_em
      ? `Avaliação de ${new Date(r.criado_em).toLocaleDateString("pt-BR")} às ${new Date(r.criado_em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`
      : "Seu resultado do MOVE 30.";
    $("v-peso").textContent = fmt(r.peso, 1, " kg");
    $("v-altura").textContent = fmt(r.altura, 2, " m");
    $("v-imc").textContent = fmt(r.imc, 1, "");
    $("v-imc-classe").textContent = r.classificacao_imc || "";
    $("v-fc").textContent = fmt(r.fc_repouso, 0, " bpm");
    $("v-fc-faixa").textContent = r.fc_repouso == null ? "" : r.fc_repouso < 60 ? "Abaixo de 60" : r.fc_repouso <= 100 ? "Faixa normal" : "Acima de 100";
    if (r.fc_pos_teste != null) { $("card-fc-pos").hidden = false; $("v-fc-pos").textContent = fmt(r.fc_pos_teste, 0, " bpm"); }
    if (r.fc_score != null) { $("card-fc-score").hidden = false; $("v-fc-score").textContent = fmt(r.fc_score, 1, " bpm"); }

    desenharGraficos(r);

    const pill = $("status-pill");
    pill.classList.remove("pill--off");
    if (r.status === "pronto" && r.analise && !analiseMostrada) {
      analiseMostrada = true;
      pill.textContent = "Análise pronta";
      // Texto principal à esquerda; ponto forte e dica à direita (como no dashboard pessoal).
      M.renderAnalise($("analise-texto"), { perfil: r.analise.perfil, mensagem: r.analise.mensagem });
      M.renderAnalise($("analise-pontos"), { destaque: r.analise.destaque, oportunidade: r.analise.oportunidade });
      $("analisando").hidden = true;
      $("analise-texto").hidden = false;
    } else if (r.status === "analisando") {
      pill.textContent = "Analisando...";
    } else if (r.status === "aguardando_medicoes") {
      pill.textContent = "Aguardando medições";
      $("analisando-msg").textContent = "Assim que as medições terminarem, a análise começa.";
    }
  }

  async function iniciar() {
    if (!/^[0-9a-f-]{36}$/i.test(token)) {
      erro("Link inválido. Escaneie o QR Code de novo ou peça ajuda à equipe.");
      return;
    }
    const timer = M.iniciarMensagensEspera($("analisando-msg"));
    try {
      const final = await M.aguardarAnalise(token, { aoAtualizar: render, intervaloMs: 5000, limiteMs: 15 * 60 * 1000 });
      if (!final) erro("Não conseguimos falar com o servidor do MOVE 30. Tente de novo daqui a pouco.");
      else if (final.status !== "pronto") $("analisando-msg").textContent = "A análise está demorando mais que o normal. Recarregue a página daqui a alguns minutos.";
    } catch (e) {
      erro(e.message);
    } finally {
      clearInterval(timer);
    }
  }
  iniciar();
})();
