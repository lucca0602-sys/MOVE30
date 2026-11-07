(function () {
  "use strict";
  const config = window.MOVE30_CONFIG || {};
  const API_BASE_URL = String(config.apiBaseUrl || "http://127.0.0.1:8002").replace(/\/$/, "");
  const header = document.querySelector(".header");
  const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 10);
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
  const integer = (value) => Number.parseInt(String(value), 10);
  const rules = {
    nome: (value) => value.trim().length >= 2 && value.trim().length <= 100 ? "" : "Informe o nome completo (2 a 100 caracteres).",
    email: (value) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim()) && value.trim().length <= 254 ? "" : "Informe um e-mail válido.",
    idade: (value) => Number.isInteger(integer(value)) && integer(value) >= 1 && integer(value) <= 120 ? "" : "Informe uma idade entre 1 e 120 anos.",
    fas: (value) => Number.isInteger(integer(value)) && integer(value) >= 1 && integer(value) <= 7 ? "" : "Informe um FAS entre 1 e 7.",
    peso: (value) => !value.trim() || (Number.isFinite(Number(value.trim().replace(",", "."))) && Number(value.trim().replace(",", ".")) >= 10 && Number(value.trim().replace(",", ".")) <= 200) ? "" : "Informe um peso entre 10 e 200 kg.",
    altura: (value) => Number.isFinite(Number(value.trim().replace(",", "."))) && Number(value.trim().replace(",", ".")) >= 1 && Number(value.trim().replace(",", ".")) <= 2.2 ? "" : "Informe uma altura entre 1,00 e 2,20 m.",
    fc_pre_teste: (value) => !value || (Number.isInteger(integer(value)) && integer(value) >= 30 && integer(value) <= 220) ? "" : "Informe uma frequência entre 30 e 220 bpm.",
    fc_pos_teste: (value) => !value || (Number.isInteger(integer(value)) && integer(value) >= 30 && integer(value) <= 220) ? "" : "Informe uma frequência entre 30 e 220 bpm.",
    tipo_teste: (value) => ["light", "moderate", "hard"].includes(value) ? "" : "Selecione o nível do teste.",
  };
  const validateField = (input) => {
    const error = rules[input.name](input.value);
    const field = input.closest(".field");
    field.classList.toggle("has-error", Boolean(error));
    field.querySelector(".field__error").textContent = error;
    input.setAttribute("aria-invalid", error ? "true" : "false");
    return !error;
  };
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
    const fields = [...form.querySelectorAll("input, select")];
    let fieldsValid = fields.map(validateField).every(Boolean);
    const manualFields = ["peso", "fc_pre_teste", "fc_pos_teste"].map((name) => form.elements.namedItem(name));
    const manualStarted = manualFields.some((input) => input.value.trim() !== "");
    if (manualStarted && manualFields.some((input) => input.value.trim() === "")) {
      manualFields.filter((input) => input.value.trim() === "").forEach((input) => {
        const field = input.closest(".field");
        field.classList.add("has-error");
        field.querySelector(".field__error").textContent = "Preencha todas as medições manuais ou deixe esta seção vazia.";
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
      email: String(values.get("email")).trim(),
      altura: decimal(values.get("altura")),
      idade: integer(values.get("idade")),
      fas: integer(values.get("fas")),
      tipo_teste: String(values.get("tipo_teste")),
    };
    if (String(values.get("peso")).trim()) participant.peso = decimal(values.get("peso"));
    if (String(values.get("fc_pre_teste")).trim()) participant.fc_pre_teste = integer(values.get("fc_pre_teste"));
    if (String(values.get("fc_pos_teste")).trim()) participant.fc_pos_teste = integer(values.get("fc_pos_teste"));
    submitButton.disabled = true;
    submitButton.textContent = "Salvando cadastro...";
    try {
      const response = await fetch(`${API_BASE_URL}/participantes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(participant),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(payload));
      const hasManualMeasurements = ["peso", "altura", "fc_pre_teste", "fc_pos_teste"].every((field) => participant[field] !== undefined);
      if (hasManualMeasurements) {
        fetch(`${API_BASE_URL}/participantes/${payload.id}/analisar`, { method: "POST" }).catch(() => {});
      }
      feedback.textContent = `Cadastro concluído. Seu número é #${payload.id}. Aguarde ser chamado para a estação; a análise ficará disponível no dashboard MOVE 30.`;
      form.reset();
      form.querySelectorAll(".field").forEach((field) => {
        field.classList.remove("has-error");
        field.querySelector(".field__error").textContent = "";
      });
    } catch (error) {
      feedback.textContent = error.message;
      feedback.classList.add("is-error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Concluir cadastro";
    }
  });
})();
