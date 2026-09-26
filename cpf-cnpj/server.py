import argparse
import json
import re
import socket
import threading
from typing import Dict, Tuple


PROTOCOL_VERSION = 1
MAX_MESSAGE_SIZE = 4096


def digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def validar_documento(value: str, document_type: str) -> Tuple[bool, str, str]:
    numero = digits(value)
    size = 11 if document_type == "CPF" else 14
    if len(numero) != size or len(set(numero)) == 1:
        return False, numero, f"Invalid {document_type}"

    if document_type == "CPF":
        digitos = (10, 9, 8, 7, 6, 5, 4, 3, 2)
        if not check_digit(numero, digitos, 9):
            return False, numero, "Invalid CPF"
        digitos = (11, 10, 9, 8, 7, 6, 5, 4, 3, 2)
        return check_digit(numero, digitos, 10), numero, "Valid CPF"

    digitos = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    if not check_digit(numero, digitos, 12):
        return False, numero, "Invalid CNPJ"
    digitos = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    return check_digit(numero, digitos, 13), numero, "Valid CNPJ"


def check_digit(numero: str, digitos: tuple, position: int) -> bool:
    total = sum(int(digit) * peso for digit, peso in zip(numero, digitos))
    expected = 0 if total % 11 < 2 else 11 - total % 11
    return expected == int(numero[position])


class ValidationServer:
    def __init__(self, host: str, port: int, max_connections: int):
        self.host = host
        self.port = port
        self.connection_slots = threading.BoundedSemaphore(max_connections)
        self.active_sockets: Dict[int, socket.socket] = {}
        self.socket_lock = threading.Lock()

    def start(self) -> None:
        with socket.socket() as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()
            print(f"Servidor iniciado em {self.host}:{self.port}")

            while True:
                client, address = server.accept()
                if not self.connection_slots.acquire(False):
                    self.send(client, {
                        "type": "error", "version": PROTOCOL_VERSION, "request_id": None,
                        "code": "SERVER_BUSY",
                        "message": "Limite de conexões ativas atingido",
                    })
                    client.close()
                    continue

                socket_id = id(client)
                with self.socket_lock:
                    self.active_sockets[socket_id] = client
                threading.Thread(
                    target=self.handle_client,
                    args=(socket_id, client, address),
                    daemon=True,
                ).start()

    def handle_client(
        self, socket_id: int, client: socket.socket, address
    ) -> None:
        client.settimeout(30)
        reader = client.makefile("rb")
        try:
            if not self.handle_hello(reader, client):
                return
            for line in reader:
                if len(line) > MAX_MESSAGE_SIZE:
                    self.send_error(client, None, "MESSAGE_TOO_LARGE", "mensagem muito grande")
                    return
                try:
                    message = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self.send_error(client, None, "INVALID_JSON", "mensagem JSON inválida")
                    continue
                if not isinstance(message, dict):
                    self.send_error(client, None, "INVALID_MESSAGE", "mensagem inválida")
                elif message.get("type") == "validate":
                    self.handle_validation(client, message)
                elif message.get("type") == "quit":
                    self.send(client, {
                        "type": "bye", "version": PROTOCOL_VERSION,
                        "request_id": message.get("request_id"),
                    })
                    return
                else:
                    self.send_error(
                        client, message.get("request_id"),
                        "UNKNOWN_MESSAGE_TYPE", "tipo de mensagem desconhecido",
                    )
        except (ConnectionError, OSError, socket.timeout):
            pass
        finally:
            reader.close()
            client.close()
            with self.socket_lock:
                self.active_sockets.pop(socket_id, None)
            self.connection_slots.release()
            print(f"Connection closed: {address}")

    def handle_hello(self, reader, client: socket.socket) -> bool:
        try:
            line = reader.readline(MAX_MESSAGE_SIZE + 1)
            message = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            self.send_error(client, None, "INVALID_HELLO", "invalid HELLO")
            return False
        if not isinstance(message, dict) or message.get("type") != "hello":
            self.send_error(client, None, "HELLO_REQUIRED", "HELLO is required")
            return False
        if message.get("version") != PROTOCOL_VERSION:
            self.send_error(
                client, message.get("request_id"),
                "UNSUPPORTED_VERSION", "versão do protocolo não suportada",
            )
            return False
        self.send(client, {
            "type": "hello_ack", "version": PROTOCOL_VERSION,
            "request_id": message.get("request_id"),
            "service": "cpf-cnpj-validator",
        })
        return True

    def handle_validation(self, client: socket.socket, message: dict) -> None:
        request_id = message.get("request_id")
        document_type = message.get("document_type")
        value = message.get("value")
        if not request_id or document_type not in ("CPF", "CNPJ") or not isinstance(value, str):
            self.send_error(client, request_id, "INVALID_VALIDATE", "dados de validação inválidos")
            return
        valid, normalized, text = validar_documento(value, document_type)
        self.send(client, {
            "type": "validation_result", "version": PROTOCOL_VERSION,
            "request_id": request_id, "document_type": document_type,
            "value": normalized, "valid": valid, "message": text,
        })

    def send(self, client: socket.socket, message: dict) -> None:
        data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        client.sendall(data)

    def send_error(self, client: socket.socket, request_id, code: str, text: str) -> None:
        self.send(client, {
            "type": "error", "version": PROTOCOL_VERSION,
            "request_id": request_id, "code": code, "message": text,
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
