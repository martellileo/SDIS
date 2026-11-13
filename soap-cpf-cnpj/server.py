import collections.abc
import http.cookies
import io
import re
import sys
import types
import urllib.parse
from wsgiref.simple_server import make_server

# ?????
_moves = types.ModuleType("spyne.util.six.moves")
_moves.collections_abc = collections.abc
_moves.http_cookies = http.cookies
_moves.urllib = types.ModuleType("spyne.util.six.moves.urllib")
_moves.urllib.parse = urllib.parse
_moves.cStringIO = io.StringIO

sys.modules["spyne.util.six.moves"] = _moves
sys.modules["spyne.util.six.moves.collections_abc"] = collections.abc
sys.modules["spyne.util.six.moves.http_cookies"] = http.cookies
sys.modules["spyne.util.six.moves.urllib"] = _moves.urllib
sys.modules["spyne.util.six.moves.urllib.parse"] = urllib.parse

from spyne import Application, Boolean, ServiceBase, Unicode, rpc
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

REGRAS = {
    "CPF": (11, (10, 9, 8, 7, 6, 5, 4, 3, 2), (11, 10, 9, 8, 7, 6, 5, 4, 3, 2)),
    "CNPJ": (14, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
}


def check_digit(numero: str, pesos: tuple) -> bool:
    total = sum(int(d) * p for d, p in zip(numero, pesos))
    return (0 if total % 11 < 2 else 11 - total % 11) == int(numero[len(pesos)])


def validar_documento(value: str, doc_type: str):
    numero = re.sub(r"\D", "", value or "")
    tam, *pesos = REGRAS.get(doc_type, (0,))
    valido = bool(tam) and len(numero) == tam and len(set(numero)) > 1 and all(check_digit(numero, p) for p in pesos)
    return valido, numero, f"{doc_type} {'validado' if valido else 'invalido'}"


class ValidadorService(ServiceBase):
    @rpc(
        Unicode,
        Unicode,
        _returns=(Unicode, Boolean, Unicode),
        _in_variable_names={"document_type": "document_type", "value": "value"},
        _out_variable_names={"cpf_cnpj": "cpf_cnpj", "valid": "valid", "message": "message"},
        _operation_name="ValidarDocumento",
        _in_message_name="ValidarDocumentoRequest",
        _out_message_name="ValidarDocumentoResponse",
    )
    def ValidarDocumento(ctx, document_type, value):
        valid, norm, msg = validar_documento(value, document_type)
        return norm, valid, msg


app = Application(
    [ValidadorService],
    tns="http://sdis.ifsp.edu.br/validador",
    name="ValidadorService",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11(),
)

wsgi_app = WsgiApplication(app)

if __name__ == "__main__":
    print("Servidor SOAP iniciado em http://localhost:8000/soap")
    server = make_server("0.0.0.0", 8000, wsgi_app)
    server.serve_forever()
