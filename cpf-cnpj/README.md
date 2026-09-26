# Protocolo TCP de validação de CPF e CNPJ

Entrega da atividade: servidor Python multithread e cliente Java.

## Execução

```powershell
python server.py --host 127.0.0.1 --port 5000 --max-connections 32
```

Em outro terminal:

```powershell
javac cliente.java
java cliente 127.0.0.1 5000 CPF 529.982.247-25
java cliente 127.0.0.1 5000 CNPJ 11.222.333/0001-81
```

O servidor mantém os sockets ativos em um dicionário dinâmico (`active_sockets`) protegido por lock. Um `BoundedSemaphore` limita o número de conexões simultâneas; novas conexões acima do limite recebem `SERVER_BUSY` e são fechadas.

## Arquivos

- `server.py`: servidor TCP multithread.
- `cliente.java`: cliente TCP.
- `protocolo-cpf-cnpj.pdf`: especificação normativa das mensagens, regras de validação e diagrama de estados.
- `make_delivery.ps1`: recompila o cliente e cria `entrega-cpf-cnpj.zip`.

O transporte usa TCP, UTF-8 e mensagens JSON delimitadas por LF (`\n`). Cada linha é uma mensagem independente. O PDF é a referência normativa para interoperabilidade.
