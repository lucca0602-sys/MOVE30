"""Simulates the whole system over real HTTP: uvicorn, background workers and a fake n8n."""
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import pytest
import requests
import uvicorn

CHAVE = "chave-de-teste"
RESPOSTA_IA = {"perfil": "P", "destaque": "D", "oportunidade": "O", "mensagem": "M"}


def porta_livre() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Api:
    def __init__(self):
        self.porta = porta_livre()
        self.url = f"http://127.0.0.1:{self.porta}"
        self.ligar()

    def ligar(self):
        from backend.main import app

        self.servidor = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=self.porta, log_level="warning")
        )
        self.thread = threading.Thread(target=self.servidor.run, daemon=True)
        self.thread.start()
        while not self.servidor.started:
            time.sleep(0.05)

    def desligar(self):
        self.servidor.should_exit = True
        self.thread.join(timeout=15)


@pytest.fixture
def ia_falsa(monkeypatch):
    """Local n8n: the first `falhas` calls answer 503; every payload is recorded."""
    estado = {"falhas": 0, "payloads": [], "lock": threading.Lock()}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with estado["lock"]:
                falhar = estado["falhas"] > 0
                estado["falhas"] -= 1
                if not falhar:
                    estado["payloads"].append(corpo)
            self.send_response(503 if falhar else 200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}" if falhar else json.dumps(RESPOSTA_IA).encode())

        def log_message(self, *args):
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    monkeypatch.setenv("N8N_WEBHOOK_URL", f"http://127.0.0.1:{servidor.server_address[1]}/webhook")
    yield estado
    servidor.shutdown()


@pytest.fixture
def api(db, ia_falsa, tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    monkeypatch.setenv("WORKER_INTERVALO_S", "0.5")
    # Longer than one failed AI call (two attempts with 2 s pauses), as in production.
    monkeypatch.setenv("IA_INTERVALO_S", "6")
    servidor = Api()
    yield servidor
    servidor.desligar()


def cadastrar(api, nome, email, altura):
    response = requests.post(f"{api.url}/participantes", timeout=10, json={
        "nome": nome, "email": email, "altura": altura,
        "idade": 25, "fas": 4, "tipo_teste": "moderate",
    })
    assert response.status_code == 200, response.text
    return response.json()["id"]


def proxima(api, device):
    response = requests.get(
        f"{api.url}/api/v1/hardware/assessments/next", timeout=10,
        headers={"X-Device-Key": CHAVE, "X-Device-ID": device},
    )
    assert response.status_code == 200, response.text
    return response.json()


def enviar(api, device, assessment_id, nome, valor, unidade, message_id=None):
    return requests.post(
        f"{api.url}/api/v1/hardware/measurements", timeout=10,
        headers={"X-Device-Key": CHAVE, "X-Device-ID": device},
        json={
            "device_id": device, "assessment_id": assessment_id,
            "message_id": message_id or str(uuid4()),
            "measured_at": "2026-11-03T12:00:00Z",
            "measurements": [{"name": nome, "value": valor, "unit": unidade}],
        },
    )


def sessao(api, assessment_id):
    return requests.get(f"{api.url}/participantes/{assessment_id}", timeout=10).json()["participante"]


def esperar(condicao, segundos=40):
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicao():
            return True
        time.sleep(0.25)
    return False


def test_tres_participantes_em_sequencia_com_falhas(api, ia_falsa, db, tmp_path):
    # Two people share a name on purpose. The AI fails for the first attempts.
    ia_falsa["falhas"] = 2
    pessoas = [
        {"nome": "Ana Souza", "email": "ana1@example.com", "altura": 1.60, "peso": 55.5, "antes": 62, "depois": 141},
        {"nome": "Ana Souza", "email": "ana2@example.com", "altura": 1.72, "peso": 68.0, "antes": 75, "depois": 163},
        {"nome": "Bruno Lima", "email": "bruno@example.com", "altura": 1.88, "peso": 91.5, "antes": 58, "depois": 172},
    ]
    for pessoa in pessoas:
        pessoa["id"] = cadastrar(api, pessoa["nome"], pessoa["email"], pessoa["altura"])

    device = "estacao-01"
    for indice, pessoa in enumerate(pessoas):
        reserva = proxima(api, device)
        assert reserva["assessment_id"] == pessoa["id"]
        assert reserva["next_measurement"] == "weight"

        # Lost response: the firmware repeats the same message_id.
        message_id = str(uuid4())
        assert enviar(api, device, pessoa["id"], "weight", pessoa["peso"], "kg", message_id).status_code == 202
        repetido = enviar(api, device, pessoa["id"], "weight", pessoa["peso"], "kg", message_id)
        assert repetido.status_code == 202 and repetido.json()["duplicate"] is True

        # Server restarts between steps: the reservation and the data survive.
        if indice == 1:
            api.desligar()
            with pytest.raises(requests.ConnectionError):
                enviar(api, device, pessoa["id"], "heart_rate_rest", pessoa["antes"], "bpm")
            api.ligar()
            assert proxima(api, device)["next_measurement"] == "heart_rate_rest"

        assert enviar(api, device, pessoa["id"], "heart_rate_rest", pessoa["antes"], "bpm").status_code == 202
        assert enviar(api, device, pessoa["id"], "heart_rate_post", pessoa["depois"], "bpm").json()["complete"] is True

    # Saved even with the AI failing; the worker retries by itself.
    assert esperar(lambda: all(sessao(api, p["id"])["perfil"] == "P" for p in pessoas))

    for pessoa in pessoas:
        salvo = sessao(api, pessoa["id"])
        assert salvo["nome"] == pessoa["nome"]
        assert float(salvo["altura"]) == pessoa["altura"]
        assert float(salvo["peso"]) == pessoa["peso"]
        assert salvo["fc_pre_teste"] == pessoa["antes"]
        assert salvo["fc_pos_teste"] == pessoa["depois"]

    # The AI received each person's own numbers, once, without name or e-mail.
    assert len(ia_falsa["payloads"]) == 3
    por_id = {payload["id"]: payload for payload in ia_falsa["payloads"]}
    for pessoa in pessoas:
        assert por_id[pessoa["id"]]["indicadores"]["peso"] == pessoa["peso"]
        assert por_id[pessoa["id"]]["indicadores"]["fc_pos_teste"] == pessoa["depois"]
    enviado = json.dumps(ia_falsa["payloads"]).lower()
    assert "ana" not in enviado and "bruno" not in enviado and "example.com" not in enviado

    # Raw readings stay linked to the right assessment.
    with db.get_connection() as connection:
        for pessoa in pessoas:
            linhas = connection.execute(
                "SELECT measurements->0->>'name', (measurements->0->>'value')::float FROM hardware_measurement_batches WHERE assessment_id = %s;",
                (pessoa["id"],),
            ).fetchall()
            assert dict(linhas) == {
                "weight": pessoa["peso"],
                "heart_rate_rest": pessoa["antes"],
                "heart_rate_post": pessoa["depois"],
            }

    # Averages use all three, and same-name people stay separate.
    medias = requests.get(f"{api.url}/indicadores/coletivos", timeout=10).json()["medias"]
    assert medias["participantes_validos"] == 3
    assert medias["peso"] == pytest.approx(sum(p["peso"] for p in pessoas) / 3, abs=0.01)
    assert medias["altura"] == pytest.approx(sum(p["altura"] for p in pessoas) / 3, abs=0.01)
    assert medias["variacao_fc"] == pytest.approx(sum(p["depois"] - p["antes"] for p in pessoas) / 3, abs=0.01)

    linhas = requests.get(f"{api.url}/participantes", timeout=10).json()["participantes"]
    assert len({linha["pessoa_id"] for linha in linhas}) == 3

    # The automatic backup holds everyone.
    def backup_completo():
        arquivos = sorted(tmp_path.glob("move30_*.json"))
        if not arquivos:
            return False
        dados = json.loads(arquivos[-1].read_text(encoding="utf-8"))
        return sum(1 for p in dados["participantes"] if p["perfil"] == "P") == 3
    assert esperar(backup_completo, 10)


def test_varias_estacoes_ao_mesmo_tempo_nao_trocam_leituras(api, ia_falsa):
    # Every value derives from the ID, so any mix-up shows in the assertion.
    ids = [cadastrar(api, f"Pessoa {i}", f"p{i}@example.com", 1.70) for i in range(9)]
    concluidos = {}
    lock = threading.Lock()

    def estacao(device):
        while True:
            reserva = proxima(api, device)
            if reserva["status"] != "active":
                return
            assessment_id = reserva["assessment_id"]
            for nome, valor, unidade in (
                ("weight", 50 + assessment_id, "kg"),
                ("heart_rate_rest", 60 + assessment_id, "bpm"),
                ("heart_rate_post", 120 + assessment_id, "bpm"),
            ):
                response = enviar(api, device, assessment_id, nome, valor, unidade)
                assert response.status_code == 202, response.text
            with lock:
                concluidos.setdefault(assessment_id, []).append(device)

    with ThreadPoolExecutor(max_workers=3) as executor:
        for resultado in [executor.submit(estacao, f"estacao-{n}") for n in range(3)]:
            resultado.result()

    assert sorted(concluidos) == sorted(ids)
    assert all(len(devices) == 1 for devices in concluidos.values())
    for assessment_id in ids:
        salvo = sessao(api, assessment_id)
        assert float(salvo["peso"]) == 50 + assessment_id
        assert salvo["fc_pre_teste"] == 60 + assessment_id
        assert salvo["fc_pos_teste"] == 120 + assessment_id

    assert esperar(lambda: len(ia_falsa["payloads"]) == 9)
    assert len({payload["id"] for payload in ia_falsa["payloads"]}) == 9
