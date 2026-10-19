# Validador de CPF e CNPJ com gRPC (Python + Node.js)

Implementação de um serviço distribuído de validação de documentos (CPF e CNPJ) utilizando **gRPC** e **Protocol Buffers (proto3)**, com servidor em **Python** e cliente em **Node.js (JavaScript)**.

---

## Estrutura de Pastas

```text
grpc-cpf-cnpj/
├── validador.proto              # Definição do contrato gRPC e mensagens Protobuf
├── README.md                    # Instruções de instalação e execução
├── servidor/                    # Servidor em Python
│   ├── validador.proto
│   ├── server.py                # Implementação do servidor e regra de validação
│   ├── validador_pb2.py         # Classes de mensagens geradas pelo protoc
│   └── validador_pb2_grpc.py    # Stubs e Servicer gRPC gerados pelo protoc
└── cliente/                     # Cliente em Node.js
    ├── validador.proto
    ├── client.js                # Implementação do cliente gRPC
    ├── package.json             # Dependências do cliente (@grpc/grpc-js, @grpc/proto-loader)
    └── package-lock.json
```

---

## Pré-requisitos

- **Python 3.10+** (com `pip`)
- **Node.js 18+** (com `npm`)

---

## 1. Instalação das Dependências

### No Servidor (Python)
Instale os pacotes `grpcio` e `grpcio-tools`:

```powershell
python -m pip install grpcio grpcio-tools
```

*(Opcional)* Os arquivos `validador_pb2.py` e `validador_pb2_grpc.py` já estão gerados na pasta `servidor/`. Caso queira regerá-los a partir do `.proto`:

```powershell
python -m grpc_tools.protoc -I . --python_out=servidor --grpc_python_out=servidor validador.proto
```

### No Cliente (Node.js)
Instale as dependências listadas no `package.json`:

```powershell
npm --prefix cliente install
```

---

## 2. Como Executar

### Passo 1: Iniciar o Servidor (Terminal 1)

```powershell
python servidor/server.py
```

Saída esperada:
```text
Servidor gRPC iniciado na porta 50051...
```

### Passo 2: Executar o Cliente (Terminal 2)

Sintaxe:
```powershell
node cliente/client.js <CPF|CNPJ> <valor> [host:port]
```

#### Exemplos de Teste:

1. **CPF Válido (com ou sem pontuação):**
   ```powershell
   node cliente/client.js CPF 52998224725
   node cliente/client.js CPF "529.982.247-25"
   ```
   Saída:
   ```text
   CPF validado: 52998224725
   ```

2. **CPF Inválido:**
   ```powershell
   node cliente/client.js CPF 11111111111
   ```
   Saída:
   ```text
   CPF invalido: 11111111111
   ```

3. **CNPJ Válido (com ou sem pontuação):**
   ```powershell
   node cliente/client.js CNPJ 11222333000181
   node cliente/client.js CNPJ "11.222.333/0001-81"
   ```
   Saída:
   ```text
   CNPJ validado: 11222333000181
   ```

4. **CNPJ Inválido:**
   ```powershell
   node cliente/client.js CNPJ 11222333000199
   ```
   Saída:
   ```text
   CNPJ invalido: 11222333000199
   ```
