// Gráficos dos dashboards (Chart.js vendorizado em js/vendor: funciona sem internet).
// Paleta igual à do Streamlit (Dashboard/visuals.py).
(function () {
  "use strict";
  const C = window.Chart;
  const COR = { pre: "#22b8ff", post: "#13d6a0", score: "#ffc83d", alert: "#ff5b70", purple: "#b28bff", laranja: "#ff8a5b", texto: "#f4f8ff", muted: "#a9c0d9", grade: "rgba(169,192,217,.14)" };
  const reduzMovimento = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  C.defaults.color = COR.muted;
  C.defaults.font.family = '"Poppins", system-ui, sans-serif';
  C.defaults.borderColor = COR.grade;
  // Ajusta campos em vez de trocar o objeto: substituir defaults.animation apaga os
  // interpoladores internos e quebra a troca de cores ("this._fn is not a function").
  if (reduzMovimento) C.defaults.animation = false;
  else { C.defaults.animation.duration = 900; C.defaults.animation.easing = "easeOutQuart"; }
  C.defaults.plugins.legend.labels.boxWidth = 12;
  C.defaults.plugins.legend.labels.usePointStyle = true;
  C.defaults.plugins.tooltip.backgroundColor = "#0a2340";
  C.defaults.plugins.tooltip.borderColor = "rgba(34,184,255,.4)";
  C.defaults.plugins.tooltip.borderWidth = 1;

  const fmt = (v, casas) => Number(v).toFixed(casas).replace(".", ",");

  // ---------- Velocímetro (meia rosca com faixas + ponteiro) ----------
  const ponteiro = {
    id: "ponteiro",
    afterDatasetsDraw(chart) {
      const cfg = chart.config.options.plugins.ponteiro;
      if (!cfg) return;
      const meta = chart.getDatasetMeta(0);
      if (!meta.data.length) return;
      const { x, y, outerRadius, innerRadius } = meta.data[0];
      if (cfg.valor === null || cfg.valor === undefined) {
        // Sem dados: só o traço no centro (as faixas ficam cinza em atualizar()).
        const c = chart.ctx;
        c.save();
        c.textAlign = "center";
        c.fillStyle = COR.muted;
        c.font = `700 ${Math.round(innerRadius * 0.42)}px Poppins, system-ui, sans-serif`;
        c.fillText("—", x, y - innerRadius * 0.12);
        c.restore();
        return;
      }
      const frac = Math.min(1, Math.max(0, (cfg.valor - cfg.min) / (cfg.max - cfg.min)));
      const ang = Math.PI + frac * Math.PI;
      const ctx = chart.ctx;
      // Marcador sobre o arco (não cruza o número no centro).
      const cos = Math.cos(ang), sin = Math.sin(ang);
      const r1 = innerRadius - 6, r2 = outerRadius + 6;
      ctx.save();
      ctx.lineCap = "round";
      ctx.strokeStyle = "#061426";
      ctx.lineWidth = 9;
      ctx.beginPath(); ctx.moveTo(x + cos * r1, y + sin * r1); ctx.lineTo(x + cos * r2, y + sin * r2); ctx.stroke();
      ctx.strokeStyle = COR.texto;
      ctx.lineWidth = 5;
      ctx.shadowColor = "rgba(255,255,255,.7)";
      ctx.shadowBlur = 10;
      ctx.beginPath(); ctx.moveTo(x + cos * r1, y + sin * r1); ctx.lineTo(x + cos * r2, y + sin * r2); ctx.stroke();
      ctx.restore();
      ctx.save();
      ctx.textAlign = "center";
      ctx.fillStyle = cfg.cor || COR.texto;
      // Fonte encolhe até o texto caber dentro do arco ("79 bpm" é mais largo que "24,4").
      let tamanho = Math.round(innerRadius * 0.42);
      do {
        ctx.font = `700 ${tamanho}px Poppins, system-ui, sans-serif`;
        tamanho -= 1;
      } while (ctx.measureText(cfg.texto).width > innerRadius * 1.45 && tamanho > 10);
      ctx.fillText(cfg.texto, x, y - innerRadius * 0.12);
      ctx.restore();
    },
  };

  function corDaFaixa(zonas, valor) {
    for (const z of zonas) if (valor < z.ate) return z.cor;
    return zonas[zonas.length - 1].cor;
  }

  // zonas: [{ate, cor, rotulo}] em ordem; min/max: limites da escala.
  function velocimetro(canvas, { min, max, zonas, casas = 0, sufixo = "" }) {
    let anterior = min;
    const larguras = zonas.map((z) => { const w = Math.min(z.ate, max) - anterior; anterior = Math.min(z.ate, max); return Math.max(w, 0); });
    const chart = new C(canvas, {
      type: "doughnut",
      data: { labels: zonas.map((z) => z.rotulo), datasets: [{ data: larguras, backgroundColor: zonas.map((z) => z.cor), borderWidth: 0, hoverOffset: 0 }] },
      options: {
        rotation: -90, circumference: 180, cutout: "68%", aspectRatio: 1.7, responsive: true, maintainAspectRatio: true,
        layout: { padding: { top: 10, bottom: 2, left: 8, right: 8 } },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (item) => ` ${item.label}` } },
          ponteiro: { valor: null, min, max, texto: "—" },
        },
      },
      plugins: [ponteiro],
    });
    return {
      atualizar(valor) {
        const cfg = chart.options.plugins.ponteiro;
        const vazio = valor === null || valor === undefined;
        chart.data.datasets[0].backgroundColor = zonas.map((z) => (vazio ? "rgba(169,192,217,.16)" : z.cor));
        cfg.valor = valor;
        cfg.texto = valor === null || valor === undefined ? "—" : `${fmt(valor, casas)}${sufixo}`;
        cfg.cor = valor === null || valor === undefined ? COR.muted : corDaFaixa(zonas, valor);
        chart.update();
      },
    };
  }

  const ZONAS_IMC = [
    { ate: 18.5, cor: COR.pre, rotulo: "Abaixo de 18,5" },
    { ate: 25, cor: COR.post, rotulo: "18,5 a 24,9 (saudável)" },
    { ate: 30, cor: COR.score, rotulo: "25 a 29,9" },
    { ate: 35, cor: COR.laranja, rotulo: "30 a 34,9" },
    { ate: 99, cor: COR.alert, rotulo: "35 ou mais" },
  ];
  const ZONAS_FC = [
    { ate: 60, cor: COR.pre, rotulo: "Abaixo de 60 bpm" },
    { ate: 100.01, cor: COR.post, rotulo: "60 a 100 bpm (normal)" },
    { ate: 999, cor: COR.alert, rotulo: "Acima de 100 bpm" },
  ];
  const ZONAS_INDICE = [
    { ate: 40, cor: COR.alert, rotulo: "0 a 39" },
    { ate: 70, cor: COR.score, rotulo: "40 a 69" },
    { ate: 101, cor: COR.post, rotulo: "70 a 100" },
  ];

  // ---------- Rosca com total no centro ----------
  const centro = {
    id: "centro",
    afterDatasetsDraw(chart) {
      const cfg = chart.config.options.plugins.centro;
      if (!cfg) return;
      const meta = chart.getDatasetMeta(0);
      if (!meta.data.length) return;
      const { x, y, innerRadius } = meta.data[0];
      const ctx = chart.ctx;
      ctx.save();
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = COR.texto;
      ctx.font = `700 ${Math.round(innerRadius * 0.5)}px Poppins, system-ui, sans-serif`;
      ctx.fillText(cfg.texto, x, y - innerRadius * 0.08);
      ctx.fillStyle = COR.muted;
      ctx.font = `500 ${Math.max(10, Math.round(innerRadius * 0.17))}px Poppins, system-ui, sans-serif`;
      ctx.fillText(cfg.legenda, x, y + innerRadius * 0.32);
      ctx.restore();
    },
  };

  function rosca(canvas, { cores, legenda = "pessoas" }) {
    const chart = new C(canvas, {
      type: "doughnut",
      data: { labels: [], datasets: [{ data: [], backgroundColor: cores, borderColor: "#061426", borderWidth: 3, hoverOffset: 6 }] },
      options: {
        cutout: "66%", responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { color: COR.texto, padding: 12, font: { size: 12 } } },
          tooltip: { callbacks: { label: (i) => { const t = i.dataset.data.reduce((a, b) => a + b, 0) || 1; return ` ${i.raw} (${Math.round((i.raw / t) * 100)}%)`; } } },
          centro: { texto: "0", legenda },
        },
      },
      plugins: [centro],
    });
    return {
      atualizar(itens) {
        // Esconde fatias zeradas para a legenda não poluir a TV.
        const visiveis = itens.map((it, i) => ({ ...it, cor: cores[i % cores.length] })).filter((it) => it.total > 0);
        chart.data.labels = visiveis.map((it) => it.faixa);
        chart.data.datasets[0].data = visiveis.map((it) => it.total);
        chart.data.datasets[0].backgroundColor = visiveis.map((it) => it.cor);
        chart.options.plugins.centro.texto = String(itens.reduce((s, it) => s + it.total, 0));
        chart.update();
      },
      legendaEmbaixo(sim) { chart.options.plugins.legend.position = sim ? "bottom" : "right"; chart.update("none"); },
    };
  }

  // ---------- Você vs. média do grupo (um mini gráfico por medida, cada um com sua escala) ----------
  function comparacao(canvas, { titulo, casas = 0, sufixo = "" }) {
    const chart = new C(canvas, {
      type: "bar",
      data: { labels: ["Você", "Grupo"], datasets: [{ data: [], backgroundColor: [COR.pre, "rgba(178,139,255,.8)"], borderRadius: 8, maxBarThickness: 64 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        layout: { padding: { top: 22 } },
        scales: { y: { beginAtZero: true, grid: { color: COR.grade }, ticks: { maxTicksLimit: 4 } }, x: { grid: { display: false }, ticks: { color: COR.texto, font: { size: 12 } } } },
        plugins: {
          legend: { display: false },
          title: { display: true, text: titulo, color: "#c6d8ef", font: { size: 13, weight: "600" }, padding: { bottom: 4 } },
          tooltip: { callbacks: { label: (i) => ` ${fmt(i.raw, casas)}${sufixo}` } },
        },
      },
      plugins: [{
        id: "valores",
        afterDatasetsDraw(c) {
          const ctx = c.ctx;
          ctx.save();
          ctx.fillStyle = COR.texto;
          ctx.textAlign = "center";
          ctx.font = `700 ${c.width < 220 ? 12 : 14}px Poppins, system-ui, sans-serif`;
          c.getDatasetMeta(0).data.forEach((barra, i) => {
            const v = c.data.datasets[0].data[i];
            if (v != null) ctx.fillText(`${fmt(v, casas)}${sufixo}`, barra.x, barra.y - 8);
          });
          ctx.restore();
        },
      }],
    });
    return { atualizar(voce, grupo) { chart.data.datasets[0].data = [voce, grupo]; chart.update(); } };
  }

  // ---------- Avaliações por hora ----------
  function porHora(canvas) {
    const ctx = canvas.getContext("2d");
    const grad = ctx.createLinearGradient(0, 0, 0, 260);
    grad.addColorStop(0, "rgba(34,184,255,.45)");
    grad.addColorStop(1, "rgba(34,184,255,0)");
    const chart = new C(canvas, {
      type: "line",
      data: { labels: [], datasets: [{ label: "Avaliações", data: [], borderColor: COR.pre, backgroundColor: grad, fill: true, tension: 0.35, pointRadius: 4, pointBackgroundColor: COR.pre, borderWidth: 3 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: { y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: COR.grade } }, x: { grid: { display: false } } },
        plugins: { legend: { display: false } },
      },
    });
    return { atualizar(serie) { chart.data.labels = serie.map((s) => s.hora); chart.data.datasets[0].data = serie.map((s) => s.total); chart.update(); } };
  }

  window.MOVE30_GRAFICOS = { COR, ZONAS_IMC, ZONAS_FC, ZONAS_INDICE, velocimetro, rosca, comparacao, porHora };
})();
