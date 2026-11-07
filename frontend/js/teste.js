(function () {
  "use strict";
  const M = window.MOVE30;
  const form = document.getElementById("teste-form");
  const feedback = form.querySelector(".teste__feedback");
  const submit = form.querySelector(".teste__submit");
  const etapaForm = document.getElementById("etapa-form");
  const etapaResultado = document.getElementById("etapa-resultado");
  const analisando = document.getElementById("analisando");
  const analisePronTa = document.getElementById("analise-pronta");
  const msgEspera = document.getElementById("analisando-msg");
  let execucao = 0; // invalida a espera anterior ao clicar em "Novo participante"

  const decimal = (v) => Number.parseFloat(String(v).trim().replace(",", "."));
  const inteiro = (v) => Number.parseInt(String(v).trim(), 10);
  // Aceita altura em metros (1,70) ou centímetros (170).
  const altura = (v) => { const n = decimal(v); return n > 3 ? n / 100 : n; };

  const regras = {
    nome: (v) => v.trim().length >= 2 && v.trim().length <= 100 ? "" : "Informe seu nome (mínimo 2 letras).",
    idade: (v) => inteiro(v) >= 5 && inteiro(v) <= 120 ? "" : "Idade entre 5 e 120 anos.",
    peso: (v) => decimal(v) >= 10 && decimal(v) <= 250 ? "" : "Peso entre 10 e 250 kg.",
    altura: (v) => altura(v) >= 0.8 && altura(v) <= 2.3 ? "" : "Altura entre 0,80 e 2,30 m (ex.: 1,70).",
    fc_repouso: (v) => inteiro(v) >= 30 && inteiro(v) <= 220 ? "" : "Batimentos entre 30 e 220 bpm.",
  };

  const validar = (input) => {
    const erro = regras[input.name](input.value);
    const campo = input.closest(".field");
    campo.classList.toggle("has-error", Boolean(erro));
    campo.querySelector(".field__error").textContent = erro;
    input.setAttribute("aria-invalid", erro ? "true" : "false");
    return !erro;
  };
  form.querySelectorAll("input").forEach((input) => {
    input.addEventListener("blur", () => validar(input));
    input.addEventListener("input", () => { if (input.closest(".field").classList.contains("has-error")) validar(input); });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";
    feedback.classList.remove("is-error");
    const inputs = [...form.querySelectorAll("input")];
    if (!inputs.map(validar).every(Boolean)) {
      form.querySelector(".has-error input")?.focus();
      return;
    }
    const dados = new FormData(form);
    const corpo = {
      nome: String(dados.get("nome")).trim(),
      idade: inteiro(dados.get("idade")),
      peso: decimal(dados.get("peso")),
      altura: Math.round(altura(dados.get("altura")) * 100) / 100,
      fc_repouso: inteiro(dados.get("fc_repouso")),
    };
    submit.disabled = true;
    submit.textContent = "Enviando...";
    try {
      const response = await fetch(`${M.PUBLIC_API}/public/teste`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(corpo),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(response.status === 422
          ? "Algum valor parece fora do normal. Confira os campos."
          : "Não conseguimos salvar agora. Confira a internet e tente de novo.");
      }
      mostrarResultado(payload.token, corpo.nome.split(" ")[0]);
    } catch (erro) {
      feedback.textContent = erro instanceof TypeError
        ? "Sem conexão com o servidor do MOVE 30. Chame alguém da equipe."
        : erro.message;
      feedback.classList.add("is-error");
    } finally {
      submit.disabled = false;
      submit.textContent = "Ver minha análise";
    }
  });

  async function mostrarResultado(token, primeiroNome) {
    const minhaExecucao = ++execucao;
    etapaForm.hidden = true;
    etapaResultado.hidden = false;
    document.getElementById("resultado-titulo").textContent = `Pronto, ${primeiroNome}!`;
    const link = M.linkDash(token);
    M.desenharQr(document.getElementById("qr"), link);
    document.getElementById("link-dash").href = link;
    analisando.hidden = false;
    analisePronTa.hidden = true;
    window.scrollTo({ top: 0, behavior: "smooth" });

    const timer = M.iniciarMensagensEspera(msgEspera);
    try {
      const resultado = await M.aguardarAnalise(token);
      if (minhaExecucao !== execucao) return;
      if (resultado?.status === "pronto") {
        M.renderAnalise(analisePronTa, resultado.analise);
        analisando.hidden = true;
        analisePronTa.hidden = false;
      } else {
        msgEspera.textContent = "A IA está com fila. Sua análise vai aparecer no link do QR Code assim que ficar pronta.";
      }
    } catch (erro) {
      if (minhaExecucao === execucao) msgEspera.textContent = erro.message;
    } finally {
      clearInterval(timer);
    }
  }

  document.getElementById("novo-teste").addEventListener("click", () => {
    execucao++;
    form.reset();
    form.querySelectorAll(".field").forEach((f) => { f.classList.remove("has-error"); f.querySelector(".field__error").textContent = ""; });
    document.getElementById("qr").replaceChildren();
    etapaResultado.hidden = true;
    etapaForm.hidden = false;
    form.querySelector("input").focus();
  });
})();
