from concurrent import futures
import re
import grpc
import validador_pb2
import validador_pb2_grpc


def digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def check_digit(numero: str, digitos: tuple, position: int) -> bool:
    total = sum(int(digit) * peso for digit, peso in zip(numero, digitos))
    expected = 0 if total % 11 < 2 else 11 - total % 11
    return expected == int(numero[position])


def validar_documento(value: str, document_type: str):
    doc_type = document_type.upper()
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
    regra = regras.get(doc_type)
    if regra is None or len(numero) != regra[0] or len(set(numero)) == 1:
        return False, numero, f"{doc_type} invalido"

    for position, pesos in enumerate(regra[1:], start=regra[0] - 2):
        if not check_digit(numero, pesos, position):
            return False, numero, f"{doc_type} invalido"
    return True, numero, f"{doc_type} validado"


class ValidadorServicer(validador_pb2_grpc.ValidadorServicer):
    def ValidarDocumento(self, request, context):
        valid, normalized, text = validar_documento(request.value, request.document_type)
        return validador_pb2.DocumentoResponse(
            cpf_cnpj=normalized,
            valid=valid,
            message=text,
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    validador_pb2_grpc.add_ValidadorServicer_to_server(ValidadorServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("Servidor gRPC iniciado na porta 50051...")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
