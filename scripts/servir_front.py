"""Serve o front com as mesmas rotas da Vercel e repassa /public para o app público (8003).

Uso local (testes) e PLANO B sem internet:
    .\\.venv\\Scripts\\python.exe -m scripts.servir_front            -> http://127.0.0.1:8080
    .\\.venv\\Scripts\\python.exe -m scripts.servir_front --rede     -> http://IP-DO-PC:8080 (celulares no mesmo Wi-Fi)

O /js/config.js é gerado com publicApiBaseUrl "" (mesma origem): o navegador fala só com este
servidor, e o app público continua escutando apenas em 127.0.0.1.
"""
import argparse
import re
import urllib.error
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FRONT = Path(__file__).resolve().parent.parent / "frontend"
APP_PUBLICO = "http://127.0.0.1:8003"
CONFIG_JS = b'window.MOVE30_CONFIG = { apiBaseUrl: "http://127.0.0.1:8002", publicApiBaseUrl: "", dashboardBaseUrl: "http://127.0.0.1:8501" };\n'
REESCRITAS = ((re.compile(r"^/$"), "/teste.html"), (re.compile(r"^/dash/[^/]+/?$"), "/dash.html"), (re.compile(r"^/geral/?$"), "/geral.html"))


class Handler(SimpleHTTPRequestHandler):
    def _caminho(self) -> str:
        return self.path.split("?", 1)[0]

    def _proxy(self, metodo: str) -> None:
        tamanho = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(tamanho) if tamanho else None
        pedido = urllib.request.Request(
            APP_PUBLICO + self.path, data=corpo, method=metodo,
            headers={"Content-Type": self.headers.get("Content-Type", "application/json"), "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=30) as resposta:
                status, dados = resposta.status, resposta.read()
        except urllib.error.HTTPError as erro:
            status, dados = erro.code, erro.read()
        except (urllib.error.URLError, TimeoutError):
            status, dados = 502, b'{"detail":"App publico (porta 8003) fora do ar."}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        caminho = self._caminho()
        if caminho.startswith("/public/"):
            return self._proxy("GET")
        if caminho == "/js/config.js":
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(CONFIG_JS)
            return
        for padrao, destino in REESCRITAS:
            if padrao.match(caminho):
                self.path = destino
                break
        return super().do_GET()

    def do_POST(self):
        if self._caminho().startswith("/public/"):
            return self._proxy("POST")
        self.send_error(405)


def main() -> None:
    global APP_PUBLICO
    parser = argparse.ArgumentParser()
    parser.add_argument("--rede", action="store_true", help="aceita celulares da rede local (0.0.0.0)")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument("--api", default=APP_PUBLICO, help="app público para onde /public é repassado")
    args = parser.parse_args()
    APP_PUBLICO = args.api.rstrip("/")
    host = "0.0.0.0" if args.rede else "127.0.0.1"
    servidor = ThreadingHTTPServer((host, args.porta), partial(Handler, directory=str(FRONT)))
    print(f"Front em http://{'IP-DO-PC' if args.rede else '127.0.0.1'}:{args.porta}  (Ctrl+C para parar)")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
