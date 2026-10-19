# Manual Completo de Estudo e Apresentação — Validador CPF/CNPJ com gRPC

Este manual foi preparado para você estudar e apresentar o trabalho ao professor. Ele cobre:
1. **Visão Geral e Arquitetura (Sockets vs. gRPC)**
2. **Explicação linha por linha do `validador.proto`**
3. **Explicação dos arquivos gerados automaticamente (`validador_pb2.py` e `validador_pb2_grpc.py`)**
4. **Explicação linha por linha do Servidor Python (`server.py`)**
5. **Explicação linha por linha do Cliente Node.js (`client.js`)**
6. **Exemplos de Entrada e Saída**
7. **Possíveis Perguntas do Professor (e como responder)**

---

## 1. Visão Geral: O que mudou dos Sockets para o gRPC?

No trabalho anterior (com **Sockets TCP puros**), você precisava:
- Abrir conexões manualmente (`socket.bind`, `socket.listen`, `socket.accept`);
- Controlar leitura de bytes e quebras de linha (`\n`), tamanho máximo de buffer e timeout;
- Fazer parsing manual de texto JSON (`json.loads`, `json.dumps`);
- Tratar manualmente qual função chamar olhando para `message.get("type") == "validate"`.

Com **gRPC**:
- **Chamada de Procedimento Remoto (RPC):** O cliente em Node.js chama `client.ValidarDocumento(...)` como se fosse uma função local, e o gRPC se encarrega de enviar pela rede até o método `ValidarDocumento(...)` no servidor Python.
- **Protocol Buffers (Protobuf):** Em vez de enviar texto JSON pesado e fazer parsing manual, os dados são serializados em **formato binário compacto** seguindo um contrato rígido definido no arquivo [`validador.proto`](file:///c:/Users/marce/Documents/Faculdade/SDIS/grpc-cpf-cnpj/validador.proto).
- **HTTP/2 por baixo dos panos:** O gRPC usa HTTP/2 nativamente, o que já traz multiplexação de requisições, controle de fluxo e gerenciamento de conexões sem precisar programar sockets manualmente.
- **Interoperabilidade entre linguagens:** Como o contrato está no `.proto`, o cliente (JavaScript/Node.js) e o servidor (Python) conversam perfeitamente mesmo sendo escritos em linguagens diferentes.

---

## 2. Explicação Linha por Linha: `validador.proto`

Arquivo: [`validador.proto`](file:///c:/Users/marce/Documents/Faculdade/SDIS/grpc-cpf-cnpj/validador.proto)

```protobuf
syntax = "proto3";

package validador;

service Validador {
  rpc ValidarDocumento (DocumentoRequest) returns (DocumentoResponse);
}

message DocumentoRequest {
  string document_type = 1; // "CPF" ou "CNPJ"
  string value = 2;
}

message DocumentoResponse {
  string cpf_cnpj = 1;
  bool valid = 2;
  string message = 3;
}
```

### O que cada linha faz:
- **`syntax = "proto3";`**
  Define que estamos usando a versão 3 da linguagem Protocol Buffers (a versão padrão atual do gRPC, mais simples e sem campos `required`/`optional` obrigatórios do proto2).
- **`package validador;`**
  Define um namespace lógico (`validador`) para evitar conflitos de nomes entre serviços diferentes. No Node.js, acessamos o serviço através desse pacote (`loadPackageDefinition(...).validador`).
- **`service Validador { ... }`**
  Declara o serviço gRPC (equivalente a uma interface remota).
- **`rpc ValidarDocumento (DocumentoRequest) returns (DocumentoResponse);`**
  Declara um método remoto unário (1 requisição $\rightarrow$ 1 resposta) chamado `ValidarDocumento`. Ele recebe um objeto do tipo `DocumentoRequest` e devolve um `DocumentoResponse`.
- **`message DocumentoRequest { ... }`**
  Define a estrutura de dados que o cliente envia para o servidor:
  - `string document_type = 1;` $\rightarrow$ Tipo do documento (`"CPF"` ou `"CNPJ"`). O número `= 1` é a **tag numérica única** que identifica esse campo no binário do Protobuf (não é o valor do campo, é o identificador da posição dele na serialização binária!).
  - `string value = 2;` $\rightarrow$ O número do CPF ou CNPJ (com ou sem máscara). Tag `= 2`.
- **`message DocumentoResponse { ... }`**
  Define a estrutura de dados que o servidor responde ao cliente:
  - `string cpf_cnpj = 1;` $\rightarrow$ O número higienizado (apenas dígitos). Tag `= 1`.
  - `bool valid = 2;` $\rightarrow$ Booleano (`true` ou `false`) indicando se é válido. Tag `= 2`.
  - `string message = 3;` $\rightarrow$ Mensagem textual (`"CPF valido"`, `"CPF invalido"`, `"CNPJ valido"`, `"CNPJ invalido"`). Tag `= 3`.

---

## 3. O que são os arquivos gerados no Servidor Python?

Quando rodamos o compilador `grpc_tools.protoc` sobre o `validador.proto`, ele gera dois arquivos na pasta `servidor/`:

1. **[`validador_pb2.py`](file:///c:/Users/marce/Documents/Faculdade/SDIS/grpc-cpf-cnpj/servidor/validador_pb2.py) (Código do Protocol Buffers):**
   Contém as classes de dados em Python: `DocumentoRequest` e `DocumentoResponse`, além dos descritores binários para serializar e desserializar essas mensagens.
2. **[`validador_pb2_grpc.py`](file:///c:/Users/marce/Documents/Faculdade/SDIS/grpc-cpf-cnpj/servidor/validador_pb2_grpc.py) (Código do gRPC):**
   Contém três coisas principais:
   - `ValidadorStub`: classe usada caso você fizesse um cliente em Python.
   - `ValidadorServicer`: classe base abstrata que o nosso servidor Python herda para implementar o método `ValidarDocumento`.
   - `add_ValidadorServicer_to_server(...)`: função que registra a nossa classe `ValidadorServicer` dentro do motor do servidor gRPC.

---

## 4. Explicação Linha por Linha: Servidor Python (`servidor/server.py`)

Arquivo: [`server.py`](file:///c:/Users/marce/Documents/Faculdade/SDIS/grpc-cpf-cnpj/servidor/server.py)

### Bloco 1: Importações (Linhas 1 a 5)
```python
from concurrent import futures
import re
import grpc
import validador_pb2
import validador_pb2_grpc
```
- **`from concurrent import futures`**: Importa o `ThreadPoolExecutor` da biblioteca padrão do Python. O servidor gRPC em Python usa um pool de threads para atender várias requisições simultaneamente.
- **`import re`**: Módulo de expressões regulares (usado para remover pontos, traços e barras do CPF/CNPJ).
- **`import grpc`**: Biblioteca oficial do gRPC em Python.
- **`import validador_pb2`**: Importa as classes de mensagens (`DocumentoRequest`, `DocumentoResponse`) geradas pelo `protoc`.
- **`import validador_pb2_grpc`**: Importa a classe base do serviço (`ValidadorServicer`) e a função de registro no servidor.

### Bloco 2: Limpeza dos dígitos (Linhas 8 e 9)
```python
def digits(value: str) -> str:
    return re.sub(r"\D", "", value)
```
- **`re.sub(r"\D", "", value)`**: Substitui tudo que **não for dígito numérico** (`\D`) por vazio (`""`).
  - Exemplo: `"123.456.789-00"` vira `"12345678900"`.

### Bloco 3: Cálculo do Dígito Verificador Módulo 11 (Linhas 12 a 15)
```python
def check_digit(numero: str, digitos: tuple, position: int) -> bool:
    total = sum(int(digit) * peso for digit, peso in zip(numero, digitos))
    expected = 0 if total % 11 < 2 else 11 - total % 11
    return expected == int(numero[position])
```
- **`zip(numero, digitos)`**: Combina cada algarismo do CPF/CNPJ com seu respectivo peso na tabela da Receita Federal.
- **`total = sum(int(digit) * peso ...)`**: Multiplica cada algarismo pelo peso e soma tudo.
- **`expected = 0 if total % 11 < 2 else 11 - total % 11`**: Regra oficial do Módulo 11: divide a soma por 11; se o resto (`total % 11`) for menor que 2 (ou seja, 0 ou 1), o dígito verificador esperado é `0`. Caso contrário, é `11 - resto`.
- **`return expected == int(numero[position])`**: Compara o dígito calculado com o dígito real que está na posição `position` (9º e 10º índices no CPF; 12º e 13º índices no CNPJ).

### Bloco 4: Validação de CPF e CNPJ (Linhas 18 a 40)
```python
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
    return True, numero, f"{doc_type} valido"
```
- **`doc_type = document_type.upper()`**: Padroniza o tipo para letras maiúsculas (`"cpf"` $\rightarrow$ `"CPF"`).
- **`regras`**: Dicionário onde cada chave (`"CPF"` ou `"CNPJ"`) guarda uma tupla com:
  1. A quantidade total de dígitos (`11` para CPF, `14` para CNPJ);
  2. Os pesos do **1º dígito verificador**;
  3. Os pesos do **2º dígito verificador**.
- **`if regra is None or len(numero) != regra[0] or len(set(numero)) == 1:`**:
  Rejeita imediatamente se:
  - O tipo não for `"CPF"` nem `"CNPJ"` (`regra is None`);
  - O tamanho após limpar pontuação for diferente de 11 (CPF) ou 14 (CNPJ);
  - Todos os dígitos forem iguais (`len(set(numero)) == 1`), como `"111.111.111-11"` (que passaria na conta matemática do módulo 11, mas é inválido pela Receita Federal).
- **`for position, pesos in enumerate(regra[1:], start=regra[0] - 2):`**:
  Testa o 1º e o 2º dígitos verificadores chamando `check_digit`. Se qualquer um falhar, retorna `(False, numero, "<TIPO> invalido")`.
- Se passar pelos dois dígitos verificadores, retorna `(True, numero, "<TIPO> valido")`.

### Bloco 5: Classe do Serviço gRPC (Linhas 43 a 50)
```python
class ValidadorServicer(validador_pb2_grpc.ValidadorServicer):
    def ValidarDocumento(self, request, context):
        valid, normalized, text = validar_documento(request.value, request.document_type)
        return validador_pb2.DocumentoResponse(
            cpf_cnpj=normalized,
            valid=valid,
            message=text,
        )
```
- **`class ValidadorServicer(validador_pb2_grpc.ValidadorServicer):`**: Herda da classe gerada pelo gRPC.
- **`def ValidarDocumento(self, request, context):`**: Implementa exatamente o método definido no `validador.proto`.
  - `request`: É o objeto `DocumentoRequest` já desserializado automaticamente pelo gRPC! Acessamos os campos diretamente com `request.value` e `request.document_type`.
  - `context`: Objeto do gRPC com metadados da chamada (IP do cliente, timeout, códigos de status gRPC, etc.).
- **`return validador_pb2.DocumentoResponse(...)`**: Cria e retorna o objeto de resposta do Protobuf preenchido com `cpf_cnpj`, `valid` e `message`.

### Bloco 6: Inicialização do Servidor (Linhas 53 a 64)
```python
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    validador_pb2_grpc.add_ValidadorServicer_to_server(ValidadorServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("Servidor gRPC iniciado na porta 50051...")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
```
- **`grpc.server(futures.ThreadPoolExecutor(max_workers=10))`**: Cria a instância do servidor gRPC com até 10 threads trabalhadoras simultâneas.
- **`add_ValidadorServicer_to_server(...)`**: Conecta a nossa classe `ValidadorServicer` ao servidor criado.
- **`server.add_insecure_port("[::]:50051")`**: Abre a porta `50051` (porta padrão histórica do gRPC) em todas as interfaces IPv4/IPv6 sem exigir certificado TLS (`insecure_port`, ideal para ambiente local/acadêmico).
- **`server.start()`**: Inicia o servidor em background.
- **`server.wait_for_termination()`**: Mantém o processo Python rodando e escutando requisições até você apertar `Ctrl+C`.

---

## 5. Explicação Linha por Linha: Cliente Node.js (`cliente/client.js`)

Arquivo: [`client.js`](file:///c:/Users/marce/Documents/Faculdade/SDIS/grpc-cpf-cnpj/cliente/client.js) (baseado diretamente no exemplo `greeter_client.js` da documentação oficial do `grpc.io`)

### Bloco 1: Importações e Carregamento do `.proto` (Linhas 1 a 14)
```javascript
const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");

const PROTO_PATH = __dirname + "/validador.proto";

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const validadorProto = grpc.loadPackageDefinition(packageDefinition).validador;
```
- **`@grpc/grpc-js`** e **`@grpc/proto-loader`**: Bibliotecas oficiais do gRPC para Node.js.
- **`const PROTO_PATH = __dirname + "/validador.proto";`**: Concatena a pasta atual (`__dirname`) com o nome do arquivo `.proto` (exatamente como no exemplo oficial do `grpc.io`).
- **`protoLoader.loadSync(PROTO_PATH, { ... })`**: Carrega o arquivo `.proto` com as opções padrão da documentação:
  - `keepCase: true`: Mantém os nomes dos campos com `_` (`document_type` e `cpf_cnpj`).
  - `defaults: true`: Garante que valores padrão (como `false` em booleanos) venham preenchidos na resposta.
- **`grpc.loadPackageDefinition(packageDefinition).validador`**: Carrega o pacote `validador` definido no `.proto`.

### Bloco 2: Função `main()` e Leitura dos Argumentos (Linhas 16 a 23)
```javascript
function main() {
  const documentType = process.argv[2];
  const value = process.argv[3];

  if (!documentType || !value) {
    console.log("Uso: node client.js <CPF|CNPJ> <valor>");
    return;
  }
```
- **`process.argv[2]` e `process.argv[3]`**: No Node.js, `process.argv[0]` é o comando `node`, `process.argv[1]` é o caminho do `client.js`, então o 1º argumento passado pelo usuário (`CPF` ou `CNPJ`) fica no índice `2`, e o número do documento fica no índice `3`.

### Bloco 3: Conexão com o Servidor e Chamada do Método Remoto (Linhas 25 a 42)
```javascript
  const client = new validadorProto.Validador(
    "localhost:50051",
    grpc.credentials.createInsecure()
  );

  client.ValidarDocumento(
    { document_type: documentType, value: value },
    function (err, response) {
      if (err) {
        console.error("Erro:", err.message);
        return;
      }
      console.log(response.message + ": " + response.cpf_cnpj);
    }
  );
}

main();
```
- **`new validadorProto.Validador("localhost:50051", grpc.credentials.createInsecure())`**: Cria o cliente apontando para a porta `50051` do servidor Python sem TLS (`createInsecure()`).
- **`client.ValidarDocumento({ document_type: documentType, value: value }, function (err, response) { ... })`**:
  Chama o método remoto `ValidarDocumento` passando os dados do `DocumentoRequest` e uma função de retorno (*callback*):
  - Se houver erro de conexão, exibe `err.message`.
  - Quando a resposta chega, exibe `response.message + ": " + response.cpf_cnpj` (ex: `CPF validado: 52998224725`).

---

## 6. Exemplos de Entrada e Saída para Demonstrar na Apresentação

| Comando executado no Cliente | O que o Cliente envia (Protobuf) | O que o Cliente imprime |
| :--- | :--- | :--- |
| `node grpc-cpf-cnpj/cliente/client.js CPF 52998224725` | `document_type="CPF"`, `value="52998224725"` | `CPF validado: 52998224725` |
| `node grpc-cpf-cnpj/cliente/client.js CPF "529.982.247-25"` | `document_type="CPF"`, `value="529.982.247-25"` | `CPF validado: 52998224725` |
| `node grpc-cpf-cnpj/cliente/client.js CPF 11111111111` | `document_type="CPF"`, `value="11111111111"` | `CPF invalido: 11111111111` |
| `node grpc-cpf-cnpj/cliente/client.js CNPJ "11.222.333/0001-81"` | `document_type="CNPJ"`, `value="11.222.333/0001-81"` | `CNPJ validado: 11222333000181` |
| `node grpc-cpf-cnpj/cliente/client.js CNPJ 12345` | `document_type="CNPJ"`, `value="12345"` | `CNPJ invalido: 12345` |

---

## 7. Perguntas Clássicas de Professor (Cola para Apresentação)

1. **"Por que não gerou arquivos `_pb.js` na pasta do cliente em Node.js, mas gerou `_pb2.py` no Python?"**
   - **Resposta:** No ecossistema Node.js, a própria documentação oficial do gRPC recomenda o uso do pacote `@grpc/proto-loader`, que lê o arquivo `validador.proto` dinamicamente em tempo de execução (`protoLoader.loadSync`) e monta os stubs em memória. Já em Python, o fluxo padrão utiliza o `grpc_tools.protoc` para gerar os arquivos estáticos `validador_pb2.py` (mensagens) e `validador_pb2_grpc.py` (serviço/stubs).

2. **"Qual a vantagem de usar gRPC em vez da versão com Sockets que vocês fizeram antes?"**
   - **Resposta:** Nos sockets puros, tivemos que criar um protocolo de aplicação na mão (delimitar mensagens por `\n`, converter para JSON em texto, validar campos ausentes no dicionário e controlar threads/conexões). No gRPC, o contrato é fortemente tipado no `validador.proto`, a serialização é binária via Protocol Buffers (muito menor e mais rápida que JSON), o transporte usa HTTP/2 nativamente e o cliente chama `ValidarDocumento()` como se fosse um método local.

3. **"Para que servem os números `= 1`, `= 2`, `= 3` dentro do arquivo `.proto`?"**
   - **Resposta:** São as *tags* dos campos no Protocol Buffers. Diferente do JSON, que envia o nome do campo como texto toda vez (`"document_type": "CPF"`), o Protobuf envia na rede apenas o número da tag (`1`) seguido do tipo e dos bytes do valor. Isso deixa a mensagem binária muito menor e mais rápida de processar.

4. **"Como o servidor aguenta mais de um cliente ao mesmo tempo?"**
   - **Resposta:** Na linha `grpc.server(futures.ThreadPoolExecutor(max_workers=10))`, configuramos um pool de 10 threads no servidor gRPC, permitindo processar até 10 chamadas `ValidarDocumento` simultaneamente de forma transparente.
