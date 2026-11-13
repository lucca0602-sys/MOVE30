(function () {
  "use strict";
  const config = window.MOVE30_CONFIG || {};
  const API_BASE_URL = String(config.apiBaseUrl || "http://127.0.0.1:8002").replace(/\/$/, "");
  const header = document.querySelector(".header");
  // Guarda a altura real do cabeçalho fixo para o CSS (scroll-padding das âncoras).
  const medirCabecalho = () => document.documentElement.style.setProperty("--altura-cabecalho", `${header.offsetHeight}px`);
  const onScroll = () => { header.classList.toggle("is-scrolled", window.scrollY > 10); medirCabecalho(); };
  window.addEventListener("resize", medirCabecalho, { passive: true });
  header.addEventListener("transitionend", medirCabecalho);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.getElementById("menu");
  const setMenu = (open) => {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
  };
  toggle.addEventListener("click", () => setMenu(!nav.classList.contains("is-open")));
  nav.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => setMenu(false)));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") setMenu(false); });
  const links = [...document.querySelectorAll(".nav__link")];
  const sections = links.map((link) => document.querySelector(link.getAttribute("href"))).filter(Boolean);
  if ("IntersectionObserver" in window) {
    const spy = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) links.forEach((link) => link.classList.toggle("is-active", link.getAttribute("href") === `#${entry.target.id}`));
    }), { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach((section) => spy.observe(section));
    const reveal = new IntersectionObserver((entries, observer) => entries.forEach((entry) => {
      if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); }
    }), { threshold: 0.15 });
    document.querySelectorAll(".reveal").forEach((element) => reveal.observe(element));
  } else document.querySelectorAll(".reveal").forEach((element) => element.classList.add("is-visible"));
  const form = document.getElementById("cadastro");
  const feedback = form.querySelector(".form__feedback");
  const submitButton = form.querySelector(".form__submit");
  const tipoAvaliacao = form.elements.namedItem("tipo_avaliacao");
  const campoNivel = document.getElementById("campo-nivel");
  const campoFcPos = document.getElementById("campo-fc-pos");
  // O select escolhe a atividade; "simples" vira tipo_avaliacao simples, o resto é "completa" + modalidade.
  const simples = () => tipoAvaliacao.value === "simples";
  const bike = () => tipoAvaliacao.value === "bike";
  const integer = (value) => Number.parseInt(String(value), 10);
  const rules = {
    nome: (value) => value.trim().length >= 2 && value.trim().length <= 100 ? "" : "Informe o nome completo (2 a 100 caracteres).",
    idade: (value) => Number.isInteger(integer(value)) && integer(value) >= 1 && integer(value) <= 120 ? "" : "Informe uma idade entre 1 e 120 anos.",
    fas: (value) => Number.isInteger(integer(value)) && integer(value) >= 1 && integer(value) <= 7 ? "" : "Selecione a frequência semanal.",
    peso: (value) => !value.trim() || (Number.isFinite(Number(value.trim().replace(",", "."))) && Number(value.trim().replace(",", ".")) >= 10 && Number(value.trim().replace(",", ".")) <= 200) ? "" : "Informe um peso entre 10 e 200 kg.",
    altura: (value) => !value.trim() || Number.isFinite(Number(value.trim().replace(",", "."))) && Number(value.trim().replace(",", ".")) >= 1 && Number(value.trim().replace(",", ".")) <= 2.2 ? "" : "Informe uma altura entre 1,00 e 2,20 m.",
    fc_pre_teste: (value) => !value || (Number.isInteger(integer(value)) && integer(value) >= 30 && integer(value) <= 220) ? "" : "Informe uma frequência entre 30 e 220 bpm.",
    fc_pos_teste: (value) => simples() || !value || (Number.isInteger(integer(value)) && integer(value) >= 30 && integer(value) <= 220) ? "" : "Informe uma frequência entre 30 e 220 bpm.",
    tipo_avaliacao: (value) => ["bike", "agachamento", "abdominal", "flexao", "simples"].includes(value) ? "" : "Escolha o tipo de teste.",
    // O nível (leve/médio/pesado = 1/2/3 min) só existe na bike.
    tipo_teste: (value) => !bike() || ["light", "moderate", "hard"].includes(value) ? "" : "Selecione o nível da bike.",
  };
  const validateField = (input) => {
    const error = rules[input.name](input.value);
    const field = input.closest(".field");
    field.classList.toggle("has-error", Boolean(error));
    field.querySelector(".field__error").textContent = error;
    input.setAttribute("aria-invalid", error ? "true" : "false");
    return !error;
  };
  const limparErro = (input) => {
    const field = input.closest(".field");
    field.classList.remove("has-error");
    field.querySelector(".field__error").textContent = "";
    input.setAttribute("aria-invalid", "false");
  };
  // Nível só na bike; FC depois do esforço some no simples.
  const aplicarTipo = () => {
    campoNivel.hidden = !bike();
    campoFcPos.hidden = simples();
    if (!bike()) {
      form.elements.namedItem("tipo_teste").value = "";
      limparErro(form.elements.namedItem("tipo_teste"));
    }
    if (simples()) {
      form.elements.namedItem("fc_pos_teste").value = "";
      limparErro(form.elements.namedItem("fc_pos_teste"));
    }
  };
  tipoAvaliacao.addEventListener("change", aplicarTipo);
  aplicarTipo();

  form.querySelectorAll("input, select").forEach((input) => {
    input.addEventListener("blur", () => validateField(input));
    input.addEventListener("input", () => { if (input.closest(".field").classList.contains("has-error")) validateField(input); });
    input.addEventListener("change", () => validateField(input));
  });
  const apiError = (payload) => typeof payload?.detail === "string" ? payload.detail : "Não foi possível concluir o cadastro. Confira a conexão e tente novamente.";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";
    feedback.classList.remove("is-error");
    const fields = [...form.querySelectorAll("input, select")].filter((input) => !input.closest("[hidden]"));
    let fieldsValid = fields.map(validateField).every(Boolean);
    // Medição manual: peso e batimentos vão juntos, com a altura (no simples, 1 batimento).
    // A altura sozinha pode ser digitada se o sensor falhar; o resto a estação mede.
    const nomesGrupo = simples() ? ["peso", "fc_pre_teste"] : ["peso", "fc_pre_teste", "fc_pos_teste"];
    const manualStarted = nomesGrupo.some((name) => form.elements.namedItem(name).value.trim() !== "");
    const manualFields = ["altura", ...nomesGrupo].map((name) => form.elements.namedItem(name));
    if (manualStarted && manualFields.some((input) => input.value.trim() === "")) {
      manualFields.filter((input) => input.value.trim() === "").forEach((input) => {
        const field = input.closest(".field");
        field.classList.add("has-error");
        field.querySelector(".field__error").textContent = "Preencha todas as medições manuais (ou só a altura) ou deixe esta seção vazia.";
        input.setAttribute("aria-invalid", "true");
      });
      fieldsValid = false;
    }
    if (!fieldsValid) {
      const faltando = [...form.querySelectorAll(".has-error label")].map((label) => label.textContent.trim());
      feedback.textContent = `Verifique: ${faltando.join(", ")}.`;
      feedback.classList.add("is-error");
      form.querySelector(".has-error input, .has-error select")?.focus();
      return;
    }
    const values = new FormData(form);
    const decimal = (value) => Number.parseFloat(String(value).trim().replace(",", "."));
    const participant = {
      nome: String(values.get("nome")).trim(),
      idade: integer(values.get("idade")),
      fas: integer(values.get("fas")),
      tipo_avaliacao: simples() ? "simples" : "completa",
    };
    if (!simples()) participant.modalidade = String(values.get("tipo_avaliacao"));
    if (bike()) participant.tipo_teste = String(values.get("tipo_teste"));
    if (String(values.get("altura")).trim()) participant.altura = decimal(values.get("altura"));
    if (String(values.get("peso")).trim()) participant.peso = decimal(values.get("peso"));
    if (String(values.get("fc_pre_teste")).trim()) participant.fc_pre_teste = integer(values.get("fc_pre_teste"));
    if (!simples() && String(values.get("fc_pos_teste")).trim()) participant.fc_pos_teste = integer(values.get("fc_pos_teste"));
    submitButton.disabled = true;
    submitButton.textContent = "Salvando cadastro...";
    try {
      // Rota pública: funciona igual pela Vercel (via Funnel) e no plano B local.
      const response = await fetch(`${window.MOVE30.PUBLIC_API}/public/cadastro`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(participant),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(payload));
      mostrarResultado(payload, participant.nome.split(" ")[0], participant);
    } catch (error) {
      feedback.textContent = error instanceof TypeError
        ? "Sem conexão com o servidor do MOVE 30. Chame alguém da equipe."
        : error.message;
      feedback.classList.add("is-error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Concluir cadastro";
    }
  });

  // ---------- Depois do cadastro: QR Code + acompanhamento ----------
  const resultado = document.getElementById("resultado");
  const analisando = document.getElementById("analisando");
  const analisePronta = document.getElementById("analise-pronta");
  const tituloStatus = document.getElementById("analisando-titulo");
  const msgStatus = document.getElementById("analisando-msg");
  let execucao = 0; // invalida o acompanhamento anterior ao clicar em "Novo participante"

  // Ordem da estação: balança, sensor de altura, batimentos. Etapa já digitada sai da lista.
  function passosEstacao(participant) {
    const passos = [];
    if (participant.peso === undefined) passos.push("suba na balança");
    if (participant.altura === undefined) passos.push("fique embaixo do sensor de altura");
    if (participant.fc_pre_teste === undefined) passos.push("coloque o dedo no sensor de batimentos");
    if (!passos.length) return "Suas medições já foram informadas. A análise começa em instantes.";
    const lista = passos.length > 1 ? `${passos.slice(0, -1).join(", ")} e ${passos.at(-1)}` : passos[0];
    return `Quando chamarem sua senha: ${lista}.`;
  }

  async function mostrarResultado({ token, numero }, primeiroNome, participant = {}) {
    const minhaExecucao = ++execucao;
    const M = window.MOVE30;
    form.hidden = true;
    resultado.hidden = false;
    document.getElementById("resultado-titulo").textContent = `Pronto, ${primeiroNome}!`;
    document.getElementById("resultado-senha").textContent = `#${numero}`;
    const link = M.linkDash(token);
    M.desenharQr(document.getElementById("qr"), link);
    document.getElementById("link-dash").href = link;
    analisando.hidden = false;
    analisePronta.hidden = true;
    tituloStatus.textContent = "Siga para a estação de medição";
    msgStatus.textContent = passosEstacao(participant);
    resultado.scrollIntoView({ behavior: "smooth", block: "start" });

    let timer = null;
    const final = await M.aguardarAnalise(token, {
      intervaloMs: 5000,
      limiteMs: 30 * 60 * 1000, // fila da estação + IA
      aoAtualizar: (r) => {
        if (minhaExecucao !== execucao || r.status !== "analisando" || timer) return;
        tituloStatus.textContent = "Medições concluídas! Analisando seus dados...";
        timer = M.iniciarMensagensEspera(msgStatus);
      },
    }).catch((erro) => ({ erro }));
    clearInterval(timer);
    if (minhaExecucao !== execucao) return;
    if (final?.status === "pronto") {
      M.renderAnalise(analisePronta, final.analise);
      analisando.hidden = true;
      analisePronta.hidden = false;
    } else {
      tituloStatus.textContent = "Seu resultado vai aparecer no link do QR Code";
      msgStatus.textContent = final?.erro ? final.erro.message : "Pode fechar esta tela: a análise chega no seu celular assim que ficar pronta.";
    }
  }

  document.getElementById("novo-cadastro").addEventListener("click", () => {
    execucao++;
    form.reset();
    aplicarTipo();
    form.querySelectorAll(".field").forEach((field) => {
      field.classList.remove("has-error");
      field.querySelector(".field__error").textContent = "";
    });
    document.getElementById("qr").replaceChildren();
    resultado.hidden = true;
    form.hidden = false;
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    form.querySelector("input").focus({ preventScroll: true });
  });
})();
