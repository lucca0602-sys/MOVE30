from backend.services.coerencia_ia import ajustar_resposta, problemas_de_coerencia


def _resp(**campos):
    base = {"perfil": "Seu IMC é 22,1.", "destaque": "Ótimo.", "oportunidade": "Caminhe 30 min.", "mensagem": "Bora!"}
    return {**base, **campos}


def test_reprova_contradicao_de_imc_e_fc():
    # Casos reais vistos no llama3.2: IMC normal chamado de "abaixo do peso"; FC normal chamada de alta.
    assert "contradiz o IMC (abaixo do peso)" in problemas_de_coerencia(
        _resp(perfil="Você está abaixo do peso ideal"), {"imc": 22.1, "fc_pre_teste": 70})
    assert any("contradiz a FC" in p for p in problemas_de_coerencia(
        _resp(perfil="seus batimentos estão acima de 100 bpm"), {"imc": 30.9, "fc_pre_teste": 82}))


def test_fc_elevada_ignorada_ganha_aviso_e_termos_de_doenca_reprovam():
    assert problemas_de_coerencia(_resp(), {"imc": 22.1, "fc_pre_teste": 108}) == []
    assert ajustar_resposta(_resp(), {"imc": 22.1, "fc_pre_teste": 108})["perfil"].startswith(
        "Seus batimentos em repouso, 108 bpm, ficaram acima de 100")
    assert "termo proibido (risco)" in problemas_de_coerencia(
        _resp(mensagem="faixa de risco para problemas"), {"imc": 30.9, "fc_pre_teste": 82})
    # Repetir a orientação da leitura não é termo proibido.
    assert problemas_de_coerencia(
        _resp(oportunidade="Coma bem, sem dieta restritiva."), {"imc": 22.1, "fc_pre_teste": 70}) == []
    assert "termo proibido (dieta restritiva)" in problemas_de_coerencia(
        _resp(oportunidade="Faça uma dieta restritiva."), {"imc": 22.1, "fc_pre_teste": 70})


def test_resposta_coerente_passa():
    assert problemas_de_coerencia(_resp(), {"imc": 22.1, "fc_pre_teste": 70}) == []
    assert problemas_de_coerencia(_resp(perfil="FC de 108 bpm, um pouco elevada"), {"imc": 22.1, "fc_pre_teste": 108}) == []


def test_ajuste_acrescenta_profissional_quando_falta():
    ajustada = ajustar_resposta(_resp(), {"imc": 15.9, "fc_pre_teste": 74})
    assert "profissional de saúde" in ajustada["oportunidade"]
    assert ajustar_resposta(_resp(), {"imc": 22.1, "fc_pre_teste": 70}) == _resp()


def test_reprova_fc_normal_chamada_de_baixa():
    # Visto no n8n real: 68 bpm descrito como "um pouco baixo".
    assert any("contradiz a FC normal" in p for p in problemas_de_coerencia(
        _resp(perfil="batimentos de 68 bpm, um pouco baixo"), {"imc": 24.1, "fc_pre_teste": 68}))
    assert problemas_de_coerencia(_resp(perfil="52 bpm, baixo e eficiente"), {"imc": 21.1, "fc_pre_teste": 52}) == []


def test_reprova_imc_fora_da_faixa_chamado_de_normal():
    # Visto no n8n real: IMC 26,3 (sobrepeso) descrito como "na faixa de referência".
    caio = {"imc": 26.3, "fc_pre_teste": 108}
    problemas = problemas_de_coerencia(_resp(perfil="IMC de 26,3, você está na faixa de referência. FC de 108, elevada."), caio)
    assert problemas == ["contradiz o IMC (na faixa de referência)"]
    assert problemas_de_coerencia(
        _resp(perfil="IMC de 26,3, um pouco acima da faixa de referência. FC de 108, elevada."), caio) == []


def test_ajuste_avisa_imc_fora_da_faixa_quando_o_texto_nao_diz():
    # Não reprova (outra chamada custa 1-2 min na CPU): o back-end põe a frase verdadeira.
    ajustada = ajustar_resposta(_resp(perfil="Você mandou bem."), {"imc": 26.3, "fc_pre_teste": 70})
    assert ajustada["perfil"] == "Seu IMC de 26,3 está um pouco acima da faixa de referência (18,5 a 24,9). Você mandou bem."
    assert ajustar_resposta(_resp(), {"imc": 15.9, "fc_pre_teste": 70})["perfil"].startswith(
        "Seu IMC de 15,9 está abaixo da faixa")
    ja_disse = _resp(perfil="IMC 31,0, acima da faixa.")
    assert ajustar_resposta(ja_disse, {"imc": 31.0, "fc_pre_teste": 70})["perfil"] == ja_disse["perfil"]


def test_reprova_terceira_pessoa():
    assert "fala da pessoa em terceira pessoa" in problemas_de_coerencia(
        _resp(perfil="O participante tem IMC 22,1."), {"imc": 22.1, "fc_pre_teste": 70})


def test_leitura_aponta_ponto_positivo_verdadeiro():
    from backend.services.n8n_service import montar_leitura

    base = {"idade": 16, "fc_pos_teste": 139, "modalidade": "bike", "tipo_teste": "moderate"}
    caio = montar_leitura({**base, "imc": 26.3, "fc_pre_teste": 108})
    assert "um pouco ACIMA da faixa" in caio and "NÃO diga que está dentro da faixa" in caio
    assert "NÃO diga que isso prova bom condicionamento" in caio
    assert "Ponto positivo para o destaque: ter encarado a atividade" in caio
    assert "Ponto positivo para o destaque: o IMC 22,0" in montar_leitura({**base, "imc": 22.0, "fc_pre_teste": 108})
    assert "Ponto positivo para o destaque: os batimentos em repouso de 70 bpm" in montar_leitura(
        {**base, "imc": 31.0, "fc_pre_teste": 70})


def test_imc_elevado_nao_conta_como_fc_elevada():
    # Visto no teste do prompt: "IMC elevado" com FC 82 reprovava como se fosse a FC.
    carla = {"imc": 30.9, "fc_pre_teste": 82}
    assert problemas_de_coerencia(_resp(perfil="Seu IMC de 30,9 está elevado. FC de 82 bpm, normal."), carla) == []
    assert "contradiz a FC normal (elevad)" in problemas_de_coerencia(
        _resp(perfil="Seus batimentos de 82 bpm estão elevados."), carla)


def test_reprova_meta_de_peso_e_suplemento():
    # Vistos no llama3.2: "perda de peso de 0,5 a 1 kg por semana" (16 anos) e "tome suplementos".
    for frase in ("perda de peso de 1 kg por semana", "tome suplementos de vitamina D", "para emagrecer"):
        assert any(p.startswith("termo proibido") for p in problemas_de_coerencia(
            _resp(oportunidade=frase), {"imc": 26.3, "fc_pre_teste": 70}))


def test_fc_alta_dita_com_acima_nao_ganha_aviso_repetido():
    resp = _resp(perfil="Batimentos de 108 bpm, um pouco acima do normal.")
    assert ajustar_resposta(resp, {"imc": 22.1, "fc_pre_teste": 108})["perfil"] == resp["perfil"]


def test_reprova_calorias_e_imc_fora_chamado_de_saudavel():
    # Vistos no teste final do prompt: 1.200 calorias para IMC 15,9 e IMC 28,6 "considerado saudável".
    assert "termo proibido (caloria)" in problemas_de_coerencia(
        _resp(oportunidade="consuma 1.200 calorias por dia"), {"imc": 15.9, "fc_pre_teste": 74})
    paula = {"imc": 28.6, "fc_pre_teste": 78}
    assert "contradiz o IMC (saudável)" in problemas_de_coerencia(
        _resp(mensagem="você está dentro de um range de IMC que pode ser considerado saudável"), paula)
    assert problemas_de_coerencia(_resp(perfil="IMC 28,6, um pouco acima da faixa. Comida saudável ajuda."), paula) == []
    assert problemas_de_coerencia(_resp(perfil="IMC 22,1, peso saudável."), {"imc": 22.1, "fc_pre_teste": 70}) == []
