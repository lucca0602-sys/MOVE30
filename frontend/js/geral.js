(function () {
  "use strict";
  const config = window.MOVE30_CONFIG || {};
  const API = String(config.publicApiBaseUrl ?? "http://127.0.0.1:8003").replace(/\/$/, "");
  const INTERVALO_MS = 5000; // igual ao Streamlit
  const G = window.MOVE30_GRAFICOS;
  const $ = (id) => document.getElementById(id);
  const fmt = (v, casas, sufixo) => v === null || v === undefined ? "—" : `${Number(v).toFixed(casas).replace(".", ",")}${sufixo}`;

  const CARDS = { peso: [1, " kg"], altura: [2, " m"], fc_pos_teste: [0, " bpm"], variacao_fc: [0, " bpm"] };
  const NOMES_TIPO = { simples: "Teste rápido", bike: "Bike", agachamento: "Agachamento", abdominal: "Abdominal", flexao: "Flexão", corrida: "Esteira (antigo)", nao_informado: "Não informado" };
  const CORES_FC = [G.COR.pre, G.COR.post, G.COR.alert];
  const CORES_IMC = [G.COR.pre, G.COR.post, G.COR.score, G.COR.laranja, G.COR.alert, G.COR.purple];
  const CORES_TIPOS = [G.COR.post, G.COR.pre, G.COR.purple, G.COR.score, G.COR.laranja, G.COR.alert, G.COR.muted];

  const graficos = {
    imc: G.velocimetro($("g-imc"), { min: 14, max: 40, zonas: G.ZONAS_IMC, casas: 1 }),
    fc: G.velocimetro($("g-fc"), { min: 40, max: 130, zonas: G.ZONAS_FC, sufixo: " bpm" }),
    indice: G.velocimetro($("g-indice"), { min: 0, max: 100, zonas: G.ZONAS_INDICE, casas: 1 }),
    distFc: G.rosca($("g-dist-fc"), { cores: CORES_FC }),
    distImc: G.rosca($("g-dist-imc"), { cores: CORES_IMC }),
    tipos: G.rosca($("g-tipos"), { cores: CORES_TIPOS, legenda: "avaliações" }),
    hora: G.porHora($("g-hora")),
  };

  // Legenda embaixo no celular e na TV; à direita no notebook.
  // Na TV os 4 gráficos dividem uma linha: colunas estreitas, legenda embaixo também.
  const estreita = window.matchMedia("(max-width: 640px), (min-width: 1600px)");
  const ajustarLegendas = () => [graficos.distFc, graficos.distImc, graficos.tipos].forEach((g) => g.legendaEmbaixo(estreita.matches));
  estreita.addEventListener?.("change", ajustarLegendas);
  ajustarLegendas();

  function nota(m, minimo) {
    if (m.valor !== null) return `${m.n} pessoa(s)`;
    return m.n ? `${m.n} de ${minimo} necessárias` : "sem dados ainda";
  }

  function distribuicao(grafico, wrapperId, itens, minimo) {
    const w = $(wrapperId);
    let aviso = w.querySelector(".aviso");
    if (!itens) {
      if (!aviso) { aviso = document.createElement("p"); aviso.className = "aviso"; w.append(aviso); }
      aviso.textContent = `Aparece a partir de ${minimo} participantes.`;
      w.querySelector("canvas").hidden = true;
      return;
    }
    aviso?.remove();
    w.querySelector("canvas").hidden = false;
    grafico.atualizar(itens);
  }

  // Só redesenha quando os números mudam: na TV, animar a cada 5 s cansa.
  let ultimo = "";
  function render(d) {
    const assinatura = JSON.stringify(d);
    if (assinatura === ultimo) return;
    ultimo = assinatura;
    $("m-participantes").textContent = d.participantes;
    Object.entries(CARDS).forEach(([campo, [casas, sufixo]]) => {
      const m = d.medias[campo];
      $(`m-${campo}`).textContent = fmt(m.valor, casas, sufixo);
      $(`n-${campo}`).textContent = nota(m, d.minimo_para_media);
      // Evento só com teste rápido: card de esforço sem nenhum dado some em vez de ficar "—".
      $(`m-${campo}`).closest(".card").hidden = m.n === 0;
    });
    graficos.imc.atualizar(d.medias.imc.valor);
    $("n-imc").textContent = nota(d.medias.imc, d.minimo_para_media);
    graficos.fc.atualizar(d.medias.fc_repouso.valor);
    $("n-fc_repouso").textContent = nota(d.medias.fc_repouso, d.minimo_para_media);
    graficos.indice.atualizar(d.indice_move.valor);
    $("n-indice").textContent = d.indice_move.valor === null ? "só avaliações de bike" : `${d.indice_move.n} pessoa(s) na bike`;
    distribuicao(graficos.distFc, "w-fc", d.distribuicao_fc_repouso, d.minimo_para_media);
    distribuicao(graficos.distImc, "w-imc", d.distribuicao_imc, d.minimo_para_media);
    distribuicao(
      graficos.tipos, "w-tipos",
      d.tipos_avaliacao && Object.entries(d.tipos_avaliacao).map(([k, total]) => ({ faixa: NOMES_TIPO[k] || k, total })),
      d.minimo_para_media,
    );
    graficos.hora.atualizar(d.avaliacoes_por_hora || []);
  }

  async function atualizar() {
    const pill = $("pill");
    try {
      const r = await fetch(`${API}/public/coletivo`, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!r.ok) throw new Error(String(r.status));
      render(await r.json());
      pill.classList.remove("pill--off");
      pill.textContent = `Tempo real · ${new Date().toLocaleTimeString("pt-BR")}`;
    } catch {
      // Mantém os últimos números na tela e avisa; tenta de novo no próximo ciclo.
      pill.classList.add("pill--off");
      pill.textContent = "Sem conexão · tentando de novo";
    } finally {
      setTimeout(atualizar, INTERVALO_MS);
    }
  }
  atualizar();
})();
