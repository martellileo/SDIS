from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import re
from xml.sax.saxutils import escape
from lxml import etree

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TNS = "http://sdis.ifsp.edu.br/validador"
BASE_DIR = Path(__file__).parent
SCHEMA = etree.XMLSchema(etree.parse(str(BASE_DIR / "validador.xsd")))


def digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def check_digit(numero: str, digitos: tuple, position: int) -> bool:
    total = sum(int(d) * p for d, p in zip(numero, digitos))
    expected = 0 if total % 11 < 2 else 11 - total % 11
    return expected == int(numero[position])


def validar_documento(value: str, document_type: str):
    doc_type = document_type.upper()
    numero = digits(value)
    regras = {
        "CPF": (11, (10, 9, 8, 7, 6, 5, 4, 3, 2), (11, 10, 9, 8, 7, 6, 5, 4, 3, 2)),
        "CNPJ": (14, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
    }
    regra = regras.get(doc_type)
    if regra is None or len(numero) != regra[0] or len(set(numero)) == 1:
        return False, numero, f"{doc_type} invalido"
    for pos, pesos in enumerate(regra[1:], start=regra[0] - 2):
        if not check_digit(numero, pesos, pos):
            return False, numero, f"{doc_type} invalido"
    return True, numero, f"{doc_type} validado"


def soap_envelope(body_xml: str) -> bytes:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<soap:Envelope xmlns:soap="{SOAP_NS}" xmlns:tns="{TNS}">'
        f"<soap:Body>{body_xml}</soap:Body>"
        f"</soap:Envelope>"
    ).encode("utf-8")


def soap_fault(code: str, message: str) -> bytes:
    return soap_envelope(
        f"<soap:Fault><faultcode>{code}</faultcode><faultstring>{escape(message)}</faultstring></soap:Fault>"
    )


class SoapHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith("?wsdl"):
            self._send(200, (BASE_DIR / "validador.wsdl").read_bytes())
        elif self.path.endswith(".xsd"):
            self._send(200, (BASE_DIR / "validador.xsd").read_bytes())
        else:
            self._send(404, b"Not Found")

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            env = etree.fromstring(raw)
            body = env.find(f"{{{SOAP_NS}}}Body")
            if body is None or len(body) == 0:
                raise ValueError("SOAP Body ausente ou vazio")
            payload = body[0]
            SCHEMA.assertValid(payload)

            doc_type = payload.findtext(f"{{{TNS}}}document_type", "")
            val = payload.findtext(f"{{{TNS}}}value", "")
            valid, norm, msg = validar_documento(val, doc_type)

            resp_str = (
                f'<tns:ValidarDocumentoResponse xmlns:tns="{TNS}">'
                f"<tns:cpf_cnpj>{norm}</tns:cpf_cnpj>"
                f"<tns:valid>{str(valid).lower()}</tns:valid>"
                f"<tns:message>{msg}</tns:message>"
                f"</tns:ValidarDocumentoResponse>"
            )
            SCHEMA.assertValid(etree.fromstring(resp_str))
            self._send(200, soap_envelope(resp_str))
        except (etree.XMLSyntaxError, etree.DocumentInvalid, ValueError) as e:
            self._send(500, soap_fault("soap:Client", str(e)))

    def _send(self, status: int, data: bytes):
        self.send_response(status)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print("Servidor SOAP iniciado em http://localhost:8000/soap (WSDL: ?wsdl)")
    HTTPServer(("0.0.0.0", 8000), SoapHandler).serve_forever()
