# Manual Completo de Estudo e Apresentação — Validador CPF/CNPJ com SOAP e XML Schema (XSD)

Este manual foi preparado para você estudar e apresentar o trabalho ao professor. Ele cobre:
1. **Visão Geral e Arquitetura (Sockets vs. gRPC vs. SOAP/XML)**
2. **O que é SOAP, WSDL e XSD?**
3. **Explicação linha por linha do XML Schema (`validador.xsd`)**
4. **Explicação linha por linha do contrato WSDL (`validador.wsdl`)**
5. **Explicação linha por linha do Servidor Python (`server.py`)**
6. **Explicação linha por linha do Cliente Java (`Client.java`)**
7. **Exemplos dos Envelopes XML (Requisição, Resposta e Fault)**
8. **Possíveis Perguntas do Professor (e como responder)**

---

## 1. Visão Geral: Sockets vs. gRPC vs. SOAP

Ao longo da disciplina, implementamos o mesmo domínio (validação de CPF e CNPJ) em três arquiteturas diferentes:

| Característica | 1. Sockets TCP Puros | 2. gRPC | 3. Web Service SOAP |
| :--- | :--- | :--- | :--- |
| **Transporte** | TCP direto (`socket`) | HTTP/2 | HTTP/1.1 (`POST /soap`) |
| **Formato dos Dados** | Texto JSON separado por `\n` | Binário (Protocol Buffers) | Texto **XML** (Envelope SOAP) |
| **Definição de Contrato** | Informal (combinado no código) | Arquivo `.proto` | Arquivos **`.wsdl`** e **`.xsd`** |
| **Validação de Estrutura** | `if` manual no dicionário Python | Tipagem binária do Protobuf | **XML Schema (XSD)** no cliente e no servidor |
| **Linguagens usadas** | Python + Java | Python + Node.js | **Python** (Servidor) + **Java** (Cliente) |

---

## 2. Conceitos Fundamentais: SOAP, WSDL e XSD

- **SOAP (*Simple Object Access Protocol*):** É um protocolo baseado em **XML** para troca de mensagens em serviços Web. Toda mensagem SOAP viaja dentro de um `<soap:Envelope>`, que contém um cabeçalho opcional (`<soap:Header>`) e um corpo obrigatório (`<soap:Body>`). Caso ocorra algum erro, o servidor responde com um elemento padronizado `<soap:Fault>` dentro do `Body`.
- **XSD (*XML Schema Definition*):** Define as regras estruturais e de tipos de dados do XML (quais tags existem, em qual ordem devem aparecer, qual o tipo de cada campo — `xs:string`, `xs:boolean` — e quais valores são permitidos, como a restrição `CPF` ou `CNPJ`). No nosso projeto, **tanto o cliente Java quanto o servidor Python validam a requisição e a resposta contra o arquivo [`validador.xsd`](file:///c:/Users/marce/Documents/Faculdade/SDIS/soap-cpf-cnpj/validador.xsd)**.
- **WSDL (*Web Services Description Language*):** É um documento XML que descreve o serviço Web como um todo: quais operações existem (`ValidarDocumento`), quais mensagens entram e saem (importando o `validador.xsd`), qual protocolo é usado (SOAP sobre HTTP) e em qual endereço (`http://localhost:8000/soap`) o serviço está disponível.

---

## 3. Explicação Linha por Linha: `validador.xsd`

Arquivo: [`validador.xsd`](file:///c:/Users/marce/Documents/Faculdade/SDIS/soap-cpf-cnpj/validador.xsd)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://sdis.ifsp.edu.br/validador"
           xmlns:tns="http://sdis.ifsp.edu.br/validador"
           elementFormDefault="qualified">
```
- **`xmlns:xs="http://www.w3.org/2001/XMLSchema"`**: Declara o namespace oficial do XML Schema da W3C.
- **`targetNamespace="http://sdis.ifsp.edu.br/validador"`**: Define o namespace exclusivo do nosso serviço de validação, evitando conflito de nomes de tags com o próprio envelope SOAP.
- **`elementFormDefault="qualified"`**: Exige que os elementos XML validados por este schema pertençam explicitamente ao namespace `http://sdis.ifsp.edu.br/validador` (usando o prefixo `tns:`).

### Elemento de Requisição (`ValidarDocumentoRequest`)
```xml
  <xs:element name="ValidarDocumentoRequest">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="document_type">
          <xs:simpleType>
            <xs:restriction base="xs:string">
              <xs:enumeration value="CPF"/>
              <xs:enumeration value="CNPJ"/>
            </xs:restriction>
          </xs:simpleType>
        </xs:element>
        <xs:element name="value" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
```
- **`<xs:sequence>`**: Garante que os elementos filhos apareçam **exatamente nessa ordem**: primeiro `document_type` e depois `value`.
- **`<xs:restriction base="xs:string">` com `<xs:enumeration>`**: Regra de validação no próprio XML Schema! O campo `document_type` **só aceita** os valores `"CPF"` ou `"CNPJ"`. Se alguém enviar `"RG"` ou `"CNH"`, o validador XSD rejeita o XML antes mesmo de chamar a função Python de cálculo de dígito.
- **`<xs:element name="value" type="xs:string"/>`**: O número do documento em texto (com ou sem máscara).

### Elemento de Resposta (`ValidarDocumentoResponse`)
```xml
  <xs:element name="ValidarDocumentoResponse">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="cpf_cnpj" type="xs:string"/>
        <xs:element name="valid" type="xs:boolean"/>
        <xs:element name="message" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
```
- Exige que a resposta contenha, em sequência:
  1. `cpf_cnpj` (`xs:string`): apenas os números higienizados;
  2. `valid` (`xs:boolean`): obrigatoriamente `"true"` ou `"false"`;
  3. `message` (`xs:string`): texto informando se foi validado ou inválido.

---

## 4. Explicação Linha por Linha: `validador.wsdl`

Arquivo: [`validador.wsdl`](file:///c:/Users/marce/Documents/Faculdade/SDIS/soap-cpf-cnpj/validador.wsdl)

O WSDL 1.1 é dividido em 5 seções clássicas:
1. **`<types>`**: Inclui o nosso [`validador.xsd`](file:///c:/Users/marce/Documents/Faculdade/SDIS/soap-cpf-cnpj/validador.xsd) (`<xs:include schemaLocation="validador.xsd"/>`) para definir os tipos de dados trocados.
2. **`<message>`**: Define as mensagens de entrada (`ValidarDocumentoInput` apontando para `tns:ValidarDocumentoRequest`) e de saída (`ValidarDocumentoOutput` apontando para `tns:ValidarDocumentoResponse`).
3. **`<portType name="ValidadorPortType">`**: Define a interface abstrata do serviço e a operação `<operation name="ValidarDocumento">` com seu `<input>` e `<output>`.
4. **`<binding name="ValidadorSoapBinding">`**: Amarração concreta do serviço ao protocolo **SOAP 1.1 sobre HTTP** (`style="document"`, `use="literal"`), definindo o cabeçalho `soapAction="http://sdis.ifsp.edu.br/validador/ValidarDocumento"`.
5. **`<service name="ValidadorService">`**: Declara o endereço real (*endpoint*) onde o servidor atende: `<soap:address location="http://localhost:8000/soap"/>`.

---

## 5. Explicação Linha por Linha: Servidor Python (`server.py`)

Arquivo: [`server.py`](file:///c:/Users/marce/Documents/Faculdade/SDIS/soap-cpf-cnpj/server.py)

### Bloco 1: Importações e Carregamento do XSD (Linhas 1 a 10)
```python
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import re
from xml.sax.saxutils import escape
from lxml import etree

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TNS = "http://sdis.ifsp.edu.br/validador"
BASE_DIR = Path(__file__).parent
SCHEMA = etree.XMLSchema(etree.parse(str(BASE_DIR / "validador.xsd")))
```
- **`http.server`**: Servidor HTTP da biblioteca padrão do Python (pois o SOAP trafega via requisições HTTP POST).
- **`from lxml import etree`**: Biblioteca padrão de mercado em Python para processamento de XML com suporte completo a **XML Schema (`XMLSchema`)**.
- **`SCHEMA = etree.XMLSchema(...)`**: Ao iniciar o servidor, lê e compila o arquivo `validador.xsd` em memória para validar todas as requisições e respostas.

### Bloco 2: Regra de Negócio — Cálculo Módulo 11 de CPF e CNPJ (Linhas 13 a 35)
- As funções `digits`, `check_digit` e `validar_documento` implementam exatamente o mesmo algoritmo oficial da Receita Federal usado nas versões anteriores (remove pontuação via regex `\D`, rejeita sequências de dígitos repetidos como `11111111111` e valida os dois dígitos verificadores por Módulo 11).

### Bloco 3: Montagem do Envelope SOAP e SOAP Fault (Linhas 38 a 50)
```python
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
```
- **`soap_envelope`**: Envolve qualquer conteúdo XML dentro da estrutura oficial do SOAP 1.1 (`<soap:Envelope>` $\rightarrow$ `<soap:Body>`) e codifica em UTF-8.
- **`soap_fault`**: Caso o XML enviado pelo cliente seja inválido ou viole o XSD, monta uma resposta padrão de erro SOAP (`<soap:Fault>`) escapando caracteres especiais com `escape(message)`.

### Bloco 4: Tratamento HTTP (`do_GET` e `do_POST`) e Validação XSD (Linhas 53 a 95)
```python
class SoapHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith("?wsdl"):
            self._send(200, (BASE_DIR / "validador.wsdl").read_bytes())
        elif self.path.endswith(".xsd"):
            self._send(200, (BASE_DIR / "validador.xsd").read_bytes())
        else:
            self._send(404, b"Not Found")
```
- **`do_GET`**: Permite que qualquer cliente ou ferramenta (como SoapUI ou navegador) consulte o contrato em `http://localhost:8000/soap?wsdl` e o schema em `/validador.xsd`.

```python
    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            env = etree.fromstring(raw)
            body = env.find(f"{{{SOAP_NS}}}Body")
            if body is None or len(body) == 0:
                raise ValueError("SOAP Body ausente ou vazio")
            payload = body[0]
            SCHEMA.assertValid(payload)
```
- **`env = etree.fromstring(raw)`**: Faz o parse do XML recebido no corpo do HTTP POST.
- **`body = env.find(f"{{{SOAP_NS}}}Body")`**: Localiza a tag `<soap:Body>` respeitando o namespace oficial do SOAP.
- **`payload = body[0]`**: Pega o elemento dentro do Body (`<tns:ValidarDocumentoRequest>`).
- **`SCHEMA.assertValid(payload)`**: **Valida a requisição contra o `validador.xsd`!** Se faltar algum campo, se a ordem estiver errada ou se `document_type` não for `CPF` nem `CNPJ`, lança `etree.DocumentInvalid`, que cai no `except` e devolve HTTP 500 com `<soap:Fault>`.

```python
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
```
- Extrai `document_type` e `value`, executa `validar_documento(val, doc_type)` e monta o XML `<tns:ValidarDocumentoResponse>`.
- **`SCHEMA.assertValid(etree.fromstring(resp_str))`**: **Valida também a resposta contra o `validador.xsd`** antes de enviá-la ao cliente, garantindo que o servidor nunca devolva um XML fora do contrato.

---

## 6. Explicação Linha por Linha: Cliente Java (`Client.java`)

Arquivo: [`Client.java`](file:///c:/Users/marce/Documents/Faculdade/SDIS/soap-cpf-cnpj/Client.java)

1. **Carregamento do XML Schema (Linhas 30 a 36):**
   ```java
   File xsdFile = new File("validador.xsd");
   if (!xsdFile.exists()) xsdFile = new File("soap-cpf-cnpj/validador.xsd");
   Schema schema = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI)
           .newSchema(xsdFile);
   DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
   dbf.setNamespaceAware(true);
   ```
   - Usa a API nativa do Java (`javax.xml.validation.SchemaFactory`) para carregar o `validador.xsd`.
   - `dbf.setNamespaceAware(true)` é essencial no SOAP para que o parser DOM do Java entenda os prefixos `soap:` e `tns:`.

2. **Construção e Validação XSD da Requisição no Cliente (Linhas 38 a 45):**
   ```java
   String reqPayload = "<tns:ValidarDocumentoRequest xmlns:tns=\"" + TNS + "\">"
           + "<tns:document_type>" + docType + "</tns:document_type>"
           + "<tns:value>" + val + "</tns:value>"
           + "</tns:ValidarDocumentoRequest>";

   // Valida requisição contra o XSD antes de enviar
   Document reqDoc = dbf.newDocumentBuilder().parse(new InputSource(new StringReader(reqPayload)));
   schema.newValidator().validate(new DOMSource(reqDoc));
   ```
   - Antes mesmo de abrir conexão HTTP, o cliente Java valida seu próprio XML de requisição contra o `validador.xsd`.

3. **Envio do Envelope SOAP via HTTP POST (Linhas 47 a 60):**
   - Empacota `reqPayload` dentro de `<soap:Envelope><soap:Body>...</soap:Body></soap:Envelope>` e envia via `HttpClient` com os cabeçalhos padrão do SOAP 1.1:
     - `Content-Type: text/xml; charset=utf-8`
     - `SOAPAction: "http://sdis.ifsp.edu.br/validador/ValidarDocumento"`

4. **Leitura e Validação XSD da Resposta no Cliente (Linhas 62 a 75):**
   - Faz o parse do XML retornado pelo servidor Python.
   - Verifica se há `<soap:Fault>`. Se não houver, extrai o elemento `<tns:ValidarDocumentoResponse>`, **valida-o contra o `validador.xsd`** (`schema.newValidator().validate(new DOMSource(respElem))`) e imprime `message + ": " + cpf_cnpj`.

---

## 7. Exemplos dos Envelopes XML Trocados na Rede

### Exemplo de Requisição SOAP enviada pelo Cliente Java:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <tns:ValidarDocumentoRequest xmlns:tns="http://sdis.ifsp.edu.br/validador">
      <tns:document_type>CPF</tns:document_type>
      <tns:value>529.982.247-25</tns:value>
    </tns:ValidarDocumentoRequest>
  </soap:Body>
</soap:Envelope>
```

### Exemplo de Resposta SOAP enviada pelo Servidor Python:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://sdis.ifsp.edu.br/validador">
  <soap:Body>
    <tns:ValidarDocumentoResponse xmlns:tns="http://sdis.ifsp.edu.br/validador">
      <tns:cpf_cnpj>52998224725</tns:cpf_cnpj>
      <tns:valid>true</tns:valid>
      <tns:message>CPF validado</tns:message>
    </tns:ValidarDocumentoResponse>
  </soap:Body>
</soap:Envelope>
```

### Exemplo de Resposta `SOAP Fault` (quando o XSD falha):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://sdis.ifsp.edu.br/validador">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Client</faultcode>
      <faultstring>Element '{http://sdis.ifsp.edu.br/validador}document_type': [facet 'enumeration'] The value 'RG' is not an element of the set {'CPF', 'CNPJ'}.</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>
```

---

## 8. Perguntas Clássicas de Professor (Cola para Apresentação)

1. **"Vocês usaram DTD ou XML Schema (XSD) para validar? Por quê?"**
   - **Resposta:** Usamos **XML Schema (XSD)** (`validador.xsd`). Diferente do DTD (que é antigo, não usa sintaxe XML e não tem tipos de dados fortes), o XSD permite definir tipos (`xs:boolean`, `xs:string`), suporta namespaces (`tns:`) exigidos pelo SOAP e permite criar restrições como `<xs:enumeration>`, garantindo que `document_type` só aceite `CPF` ou `CNPJ`.

2. **"Onde acontece a validação do XML Schema no projeto de vocês?"**
   - **Resposta:** Nas duas pontas e nos dois sentidos!
     - No **Cliente Java**, usamos `javax.xml.validation.Schema` para validar a requisição antes de enviar e validar a resposta quando ela chega.
     - No **Servidor Python**, usamos `lxml.etree.XMLSchema` (`SCHEMA.assertValid(...)`) para validar a requisição recebida do cliente e também para validar a resposta gerada antes de devolvê-la.

3. **"O que acontece se um cliente enviar um XML fora do padrão do XSD para o servidor?"**
   - **Resposta:** O método `SCHEMA.assertValid(payload)` lança uma exceção `DocumentInvalid` do `lxml`, e o servidor captura essa exceção e devolve um envelope padrão de erro do protocolo SOAP (`<soap:Fault>` com `<faultcode>soap:Client</faultcode>` e HTTP 500), informando exatamente qual regra do XSD foi violada.

4. **"Qual a diferença entre o SOAP que vocês implementaram agora e o gRPC da atividade anterior?"**
   - **Resposta:** Ambos permitem comunicação entre linguagens diferentes com contrato bem definido, mas o **SOAP** é baseado em texto **XML** sobre HTTP/1.1, usando **WSDL** e **XSD** para contrato e validação (muito comum em sistemas bancários, governamentais como Nota Fiscal Eletrônica e legados corporativos). Já o **gRPC** usa serialização binária (**Protocol Buffers**) sobre HTTP/2 com contrato `.proto`, sendo mais leve e rápido na rede, porém não legível por humanos no tráfego bruto como o XML do SOAP.
