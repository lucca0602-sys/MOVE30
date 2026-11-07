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


def test_reprova_fc_elevada_ignorada_e_termos_de_doenca():
    assert "não comenta a FC elevada" in problemas_de_coerencia(_resp(), {"imc": 22.1, "fc_pre_teste": 108})
    assert "termo proibido (risco)" in problemas_de_coerencia(
        _resp(mensagem="faixa de risco para problemas"), {"imc": 30.9, "fc_pre_teste": 82})


def test_resposta_coerente_passa():
    assert problemas_de_coerencia(_resp(), {"imc": 22.1, "fc_pre_teste": 70}) == []
    assert problemas_de_coerencia(_resp(perfil="FC de 108 bpm, um pouco elevada"), {"imc": 22.1, "fc_pre_teste": 108}) == []


def test_ajuste_acrescenta_profissional_quando_falta():
    ajustada = ajustar_resposta(_resp(), {"imc": 15.9, "fc_pre_teste": 74})
    assert "profissional de saúde" in ajustada["oportunidade"]
    assert ajustar_resposta(_resp(), {"imc": 22.1, "fc_pre_teste": 70}) == _resp()
