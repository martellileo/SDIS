import argparse
import json
import re
import socket
import threading
from typing import Set, Tuple


MAX_MESSAGE_SIZE = 4096


def digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def validar_documento(value: str, document_type: str):
    numero = digits(value)
    regras = {
        "CPF": (
            11,
            (10, 9, 8, 7, 6, 5, 4, 3, 2),
            (11, 10, 9, 8, 7, 6, 5, 4, 3, 2),
        ),
        "CNPJ": (
            14,
            (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
            (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
        ),
    }
    regra = regras.get(document_type)
    if regra is None or len(numero) != regra[0] or len(set(numero)) == 1:
        return False, numero, f"{document_type} invalido"

    for position, pesos in enumerate(regra[1:], start=regra[0] - 2):
        if not check_digit(numero, pesos, position):
            return False, numero, f"{document_type} invalido"
    return True, numero, f"{document_type} valido"


def check_digit(numero: str, digitos: tuple, position: int) -> bool:
    total = sum(int(digit) * peso for digit, peso in zip(numero, digitos))
    expected = 0 if total % 11 < 2 else 11 - total % 11
    return expected == int(numero[position])


class ValidationServer:
    def __init__(self, host: str, port: int, max_connections: int):
        self.host = host
        self.port = port
        self.connection_slots = threading.BoundedSemaphore(max_connections)
        self.active_sockets: Set[socket.socket] = set()
        self.socket_lock = threading.Lock()

    def start(self) -> None:
        with socket.socket() as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()
            print(f"Servidor iniciado em {self.host}:{self.port}")

            while True:
                client, _ = server.accept()
                if not self.connection_slots.acquire(False):
                    self.send(client, {
                        "type": "error",
                        "code": "SERVER_BUSY",
                        "message": "Limite de conexões ativas atingido",
                    })
                    client.close()
                    continue

                with self.socket_lock:
                    self.active_sockets.add(client)
                threading.Thread(
                    target=self.handle_client,
                    args=(client,),
                    daemon=True,
                ).start()

    def handle_client(self, client: socket.socket) -> None:
        client.settimeout(30)
        try:
            with client, client.makefile("rb") as reader:
                for line in reader:
                    if len(line) > MAX_MESSAGE_SIZE:
                        self.send_error(client, "MESSAGE_TOO_LARGE", "mensagem muito grande")
                        return
                    try:
                        message = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        self.send_error(client, "INVALID_JSON", "mensagem JSON inválida")
                        continue
                    if not isinstance(message, dict):
                        self.send_error(client, "INVALID_MESSAGE", "mensagem inválida")
                    elif message.get("type") == "validate":
                        self.handle_validation(client, message)
                    else:
                        self.send_error(
                            client, "UNKNOWN_MESSAGE_TYPE", "tipo de mensagem desconhecido",
                        )
        except (ConnectionError, OSError, socket.timeout):
            pass
        finally:
            with self.socket_lock:
                self.active_sockets.discard(client)
            self.connection_slots.release()

    def handle_validation(self, client: socket.socket, message: dict) -> None:
        document_type = message.get("document_type")
        value = message.get("value")
        if document_type not in ("CPF", "CNPJ") or not isinstance(value, str):
            self.send_error(client, "INVALID_VALIDATE", "dados de validação inválidos")
            return
        valid, normalized, text = validar_documento(value, document_type)
        self.send(client, {
            "cpf_cnpj": normalized, "valid": valid, "message": text,
        })

    def send(self, client: socket.socket, message: dict) -> None:
        data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        client.sendall(data)

    def send_error(self, client: socket.socket, code: str, text: str) -> None:
        self.send(client, {
            "type": "error",
            "code": code, "message": text,
        })


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor de validação de CPF e CNPJ")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--max-connections", type=int, default=32)
    args = parser.parse_args()
    if args.max_connections < 1:
        parser.error("--max-connections tem de ser pelo menos 1")
    try:
        ValidationServer(args.host, args.port, args.max_connections).start()
    except KeyboardInterrupt:
        print("\nServer fechado")


if __name__ == "__main__":
    main()
