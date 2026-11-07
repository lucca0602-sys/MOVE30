# MOVE 30

Estação de avaliação física da feira de ciências: cadastro no totem, peso e batimentos pelo hardware (ESP32-S3), análise por IA (n8n + Ollama) e dashboards.

## Como rodar

Pré-requisitos: PostgreSQL, Docker com n8n e Ollama, e `.env` preenchido (modelo em `.env.example`).

1. **Banco:** aplique uma vez, em ordem, os arquivos de `backend/migrations/` que ainda não foram aplicados.
2. **API:** `.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8002`
3. **Dashboards:** `.\.venv\Scripts\python.exe -m streamlit run Dashboard\app.py`
4. **Totem:** abra `frontend/index.html` com o Live Server na porta 5500.
5. **Firmware:** abra `linha_medicao/linha_medicao/linha_medicao.ino` no Arduino IDE, confira `secrets.h` e `API_URL` em `config.h` (o IP do computador pode mudar) e grave. Deixe a balança vazia ao ligar.

## Fluxo na estação

A estação atende uma pessoa por vez, na ordem do cadastro. A página **Estação de medição** do dashboard mostra quem deve estar na balança; confira antes de cada pessoa subir.

1. Peso: a pessoa sobe e fica parada por cerca de 1 s.
2. FC de repouso: dedo no sensor por cerca de 15 s.
3. Corrida: a pessoa tira o dedo e corre.
4. FC depois: dedo no sensor de novo, no mínimo 60 s depois da FC de repouso.

O botão de emergência cancela a pessoa atual, sem apagar o que já foi medido. Para refazer a tara, envie `t` no Monitor Serial com a balança vazia.

## Proteção dos dados

- Cada leitura é gravada no banco assim que chega, ligada ao ID do cadastro.
- Se o envio falhar, a ESP32 guarda a leitura na memória e reenvia sem duplicar.
- O banco recusa sobrescrever medição ou análise e recusa apagar participante. Uma correção deliberada exige um administrador desligar o gatilho `proteger_participante`.
- Se a IA falhar, as medidas continuam salvas e a análise é tentada de novo a cada 10 minutos.
- A API grava em `backups/` um arquivo novo sempre que os dados mudam, verificando a cada minuto. Essa pasta contém dados pessoais e fica fora do Git.
- Para restaurar: `.\.venv\Scripts\python.exe -m scripts.restaurar_backup backups\arquivo.json`. Só insere o que falta.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests
```

Os testes criam e apagam um banco separado, `move30_test`, e não tocam nos dados reais. Eles usam uma IA simulada.

Mais detalhes em [docs/hardware-api.md](docs/hardware-api.md) e [docs/registration-flow.md](docs/registration-flow.md).
