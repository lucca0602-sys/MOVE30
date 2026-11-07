(function () {
  "use strict";
  const config = window.MOVE30_CONFIG || {};
  const API = String(config.publicApiBaseUrl ?? "http://127.0.0.1:8003").replace(/\/$/, "");
  const INTERVALO_MS = 5000; // igual ao Streamlit
  const $ = (id) => document.getElementById(id);
  const fmt = (v, casas, sufixo) => v === null || v === undefined ? "—" : `${Number(v).toFixed(casas).replace(".", ",")}${sufixo}`;

  const MEDIAS = { peso: [1, " kg"], altura: [2, " m"], imc: [1, ""], fc_repouso: [0, " bpm"], fc_pos_teste: [0, " bpm"], variacao_fc: [0, " bpm"], fc_score: [1, " bpm"] };
  const CORES_FC = ["#22b8ff", "#13d6a0", "#ff5b70"];
  const CORES_IMC = ["#22b8ff", "#13d6a0", "#ffc83d", "#ff8a5b", "#ff5b70", "#b28bff"];
  const NOMES_TIPO = { simples: "Teste rápido", light: "Leve", moderate: "Moderado", hard: "Intenso", nao_informado: "Não informado" };

  function barras(container, itens, cores, minimo) {
    container.replaceChildren();
    if (!itens) {
      const p = document.createElement("p");
      p.className = "aviso";
      p.textContent = `Aparece a partir de ${minimo} participantes.`;
      container.append(p);
      return;
    }
    const total = itens.reduce((s, i) => s + i.total, 0) || 1;
    itens.forEach((item, i) => {
      const linha = document.createElement("div");
      linha.className = "barra__linha";
      const rotulo = document.createElement("span");
      rotulo.textContent = item.faixa;
      const trilho = document.createElement("div");
      trilho.className = "barra__trilho";
      const fill = document.createElement("div");
      fill.className = "barra__fill";
      fill.style.width = `${(item.total / total) * 100}%`;
      fill.style.background = cores[i % cores.length];
      trilho.append(fill);
      const valor = document.createElement("span");
      valor.className = "barra__valor";
      valor.textContent = `${item.total} · ${Math.round((item.total / total) * 100)}%`;
      linha.append(rotulo, trilho, valor);
      container.append(linha);
    });
  }

  function render(d) {
    $("m-participantes").textContent = d.participantes;
    Object.entries(MEDIAS).forEach(([campo, [casas, sufixo]]) => {
      const m = d.medias[campo];
      $(`m-${campo}`).textContent = fmt(m.valor, casas, sufixo);
      $(`n-${campo}`).textContent = m.valor === null
        ? (m.n ? `${m.n} de ${d.minimo_para_media} necessárias` : "sem dados ainda")
        : `${m.n} pessoa(s)`;
    });
    $("m-indice").textContent = d.indice_move.valor === null ? "—" : `${fmt(d.indice_move.valor, 1, "")} / 100`;
    barras($("d-fc"), d.distribuicao_fc_repouso, CORES_FC, d.minimo_para_media);
    barras($("d-imc"), d.distribuicao_imc, CORES_IMC, d.minimo_para_media);
    barras(
      $("d-tipos"),
      d.tipos_avaliacao && Object.entries(d.tipos_avaliacao).map(([k, total]) => ({ faixa: NOMES_TIPO[k] || k, total })),
      ["#13d6a0", "#22b8ff", "#b28bff", "#ffc83d", "#ff5b70"],
      d.minimo_para_media,
    );
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
