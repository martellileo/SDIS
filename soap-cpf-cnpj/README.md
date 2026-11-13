# Validador de CPF e CNPJ com SOAP e XML Schema (Python + Java)

Implementação de um Serviço Web utilizando **SOAP 1.1**, **WSDL 1.1** e validação estrita de requisições e respostas via **XML Schema (XSD)**, com servidor em **Python** e cliente em **Java**.

---

## Estrutura de Pastas

```text
soap-cpf-cnpj/
├── validador.xsd      # XML Schema (XSD) para validação de Requisição e Resposta
├── validador.wsdl     # Contrato WSDL 1.1 do Serviço Web SOAP
├── server.py          # Servidor SOAP em Python (http.server + lxml XSD)
├── Client.java        # Cliente SOAP em Java (HttpClient + javax.xml.validation)
├── README.md          # Instruções de instalação e execução
└── MANUAL_ESTUDO.md   # Explicação linha a linha e guia para apresentação
```

---

## Pré-requisitos

- **Python 3.10+** (com pacote `lxml` instalado)
- **Java JDK 11+** (testado com Java 21; executa `Client.java` diretamente sem precisar de `javac` manual)

---

## 1. Instalação das Dependências

### No Servidor (Python)
Instale as bibliotecas necessárias (`spyne`, `lxml` e `legacy-cgi`):

```powershell
python -m pip install spyne lxml legacy-cgi
```

### No Cliente (Java)
**Nenhuma dependência externa é necessária.** O cliente utiliza apenas pacotes nativos da biblioteca padrão do Java (`java.net.http`, `javax.xml.parsers` e `javax.xml.validation`).

---

## 2. Como Executar

### Passo 1: Iniciar o Servidor (Terminal 1)

Dentro da pasta `soap-cpf-cnpj`:

```powershell
python server.py
```

Saída esperada:
```text
Servidor SOAP iniciado em http://localhost:8000/soap
```

### Passo 2: Executar o Cliente (Terminal 2)

Sintaxe:
```powershell
java Client.java <CPF|CNPJ> <valor> [url]
```

#### Exemplos de Teste:

1. **CPF Válido (com ou sem pontuação):**
   ```powershell
   java Client.java CPF 52998224725
   java Client.java CPF "529.982.247-25"
   ```
   Saída:
   ```text
   CPF validado: 52998224725
   ```

2. **CPF Inválido:**
   ```powershell
   java Client.java CPF 11111111111
   ```
   Saída:
   ```text
   CPF invalido: 11111111111
   ```

3. **CNPJ Válido (com ou sem pontuação):**
   ```powershell
   java Client.java CNPJ 11222333000181
   java Client.java CNPJ "11.222.333/0001-81"
   ```
   Saída:
   ```text
   CNPJ validado: 11222333000181
   ```

4. **CNPJ Inválido:**
   ```powershell
   java Client.java CNPJ 11222333000199
   ```
   Saída:
   ```text
   CNPJ invalido: 11222333000199
   ```

5. **Teste de Violação do XML Schema (XSD):**
   Caso passe um tipo de documento fora da enumeração permitida pelo `validador.xsd` (`CPF` ou `CNPJ`), a validação XSD barra a requisição imediatamente:
   ```powershell
   java Client.java RG 123456789
   ```
   Saída (exceção `SAXParseException` do validador XSD):
   ```text
   Exception in thread "main" org.xml.sax.SAXParseException; ... cvc-enumeration-valid: Value 'RG' is not facet-valid with respect to enumeration '[CPF, CNPJ]'.
   ```
