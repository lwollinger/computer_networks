# Protocolo de Monitoramento de Sensores IoT

Projeto desenvolvido para a disciplina de Redes de Computadores do curso de Engenharia Eletrônica (IFSC).

Alunos: Gabriel da Silva Huebra & Lucas Martins Wollinger 

---

# 1. Visão Geral

O sistema simula uma rede de sensores IoT conectados a uma central de monitoramento através do protocolo TCP.

Cada sensor pode:

* Realizar cadastro na central;
* Enviar leituras periódicas;
* Enviar eventos de alarme;
* Receber confirmação de recebimento (ACK) do servidor.

O servidor atua como uma central de monitoramento responsável por:

* Registrar sensores cadastrados;
* Armazenar leituras e eventos;
* Detectar condições de alarme;
* Responder às requisições dos sensores.

Toda a comunicação utiliza mensagens de tamanho fixo de **60 bytes**.

---

# 2. Estrutura da Mensagem

Cada mensagem possui exatamente **60 bytes (480 bits)**.

| Bloco       | Tamanho  | Descrição                     |
| ----------- | -------- | ----------------------------- |
| Controle    | 5 bytes  | Cabeçalho e valor da leitura  |
| Data/Hora   | 5 bytes  | Timestamp compactado          |
| Localização | 50 bytes | Local de instalação do sensor |

## 2.1 Cabeçalho de Controle

O cabeçalho utiliza 33 bits úteis armazenados em 5 bytes.

| Campo               | Bits |
| ------------------- | ---- |
| Tipo da Mensagem    | 2    |
| ID do Sensor        | 10   |
| Tipo do Sensor      | 4    |
| Indicador de Alarme | 1    |
| Valor da Leitura    | 16   |

### Tipo da Mensagem

| Valor | Significado    |
| ----- | -------------- |
| 0     | Cadastro       |
| 1     | Leitura        |
| 2     | Evento         |
| 3     | Resposta (ACK) |

### Tipo do Sensor

| Valor | Significado          |
| ----- | -------------------- |
| 0     | Temperatura          |
| 1     | Presença             |
| 2     | Fumaça               |
| 3     | Falha de Equipamento |

---

## 2.2 Data e Hora

A data e hora utilizam 38 bits úteis armazenados em 5 bytes.

| Campo             | Bits |
| ----------------- | ---- |
| Ano (offset 2000) | 11   |
| Mês               | 4    |
| Dia               | 5    |
| Hora              | 5    |
| Minuto            | 6    |
| Segundo           | 6    |

Exemplo:

Data real:

```text
31/05/2026 14:35:20
```

Ano enviado:

```text
2026 - 2000 = 26
```

---

## 2.3 Localização

Campo ASCII de 50 bytes utilizado para identificar a posição física do sensor.

Exemplos:

```text
Laboratorio 01
Corredor Norte
Bloco B - Sala 204
```

Caso a string possua menos de 50 caracteres, o restante é preenchido com bytes nulos.

---

# 3. Fluxo de Comunicação

O sistema utiliza TCP no modelo cliente-servidor.

## Cadastro

1. O sensor envia uma mensagem do tipo 0.
2. O servidor registra os dados em `sensores.txt`.
3. O servidor responde com um ACK (tipo 3).

## Leitura

1. O sensor envia uma mensagem do tipo 1.
2. O servidor verifica condições de alarme.
3. O servidor registra o evento em `log_eventos.txt`.
4. O servidor responde com um ACK.

## Evento de Alarme

1. O sensor envia uma mensagem do tipo 2.
2. O servidor registra o evento.
3. O servidor responde com ACK contendo o estado final do alarme.

---

# 4. Armazenamento de Dados

## sensores.txt

Arquivo utilizado para armazenar os sensores cadastrados.

Formato:

```text
ID:0101 | Tipo:TEMPERATURA | Local:Laboratorio 01
```

O sistema evita registros duplicados do mesmo sensor.

---

## log_eventos.txt

Arquivo utilizado para armazenar leituras e eventos.

Formato:

```text
31/05/2026 14:35:20 |
ID:0101 |
SENSOR:TEMPERATURA |
EVENTO:LEITURA |
VALOR:237 |
STATUS:NORMAL
```

Quando uma condição de alarme é detectada:

```text
STATUS:*** ALARME ***
```

---

# 5. Detecção de Alarmes

O servidor verifica automaticamente as condições de alarme.

## Sensor de Temperatura

O alarme é ativado quando:

```text
Temperatura > 40°C
```

Como a temperatura é enviada multiplicada por 10:

```text
42.5°C → valor enviado = 425
```

## Outros Sensores

Para sensores de presença, fumaça e falha de equipamento, o alarme é determinado pelo bit de alarme enviado na mensagem.

---

# 6. Tratamento de Falhas

## Retry Automático

Caso o servidor não responda, o cliente realiza até 3 tentativas.

Timeouts utilizados:

| Tentativa | Timeout |
| --------- | ------- |
| 1         | 5 s     |
| 2         | 10 s    |
| 3         | 15 s    |

## Recepção Completa de Pacotes

Como o TCP é orientado a fluxo e pode fragmentar dados, cliente e servidor utilizam uma rotina que garante o recebimento dos 60 bytes completos antes do processamento.

## Validação do ACK

O cliente valida:

* Tipo da mensagem recebido;
* ID do sensor retornado.

Isso garante que a resposta corresponde à requisição enviada.

---

# 7. Execução do Sistema

## Passo 1 - Iniciar o Servidor

Abra um terminal e execute:

```bash
python server.py
```

Saída esperada:

```text
============================================================
  Central de Monitoramento IoT
  Endereço : 127.0.0.1:65432
  Sensores : sensores.txt
  Log      : log_eventos.txt
  Modo     : Multithread
============================================================
```

## Passo 2 - Iniciar o Cliente

Abra outro terminal e execute:

```bash
python cliente.py
```

Será exibido o menu:

```text
=============================================
       SIMULADOR DE SENSOR IoT
=============================================
  1. Enviar Cadastro
  2. Enviar Leitura
  3. Enviar Evento de Alarme
  4. Sair
```

---

# 8. Testes e Validação

## Teste 1 - Cadastro de Sensor

1. Selecione a opção "Enviar Cadastro".
2. Escolha um sensor.

Resultado esperado:

* Recebimento do ACK.
* Registro em `sensores.txt`.

Exemplo:

```text
ID:0101 | Tipo:TEMPERATURA | Local:Laboratorio 01
```

---

## Teste 2 - Leitura Normal

1. Escolha o sensor de temperatura.
2. Informe uma temperatura de 25°C.

Resultado esperado:

* ACK recebido.
* Registro em `log_eventos.txt`.
* Status NORMAL.

---

## Teste 3 - Alarme por Temperatura

1. Escolha o sensor de temperatura.
2. Informe uma temperatura acima de 40°C.

Exemplo:

```text
45°C
```

Resultado esperado:

* ACK recebido.
* Campo de alarme ativado.
* Registro contendo:

```text
STATUS:*** ALARME ***
```

---

## Teste 4 - Evento de Alarme

1. Selecione "Enviar Evento de Alarme".

Resultado esperado:

* ACK recebido.
* Registro em log.
* Alarme ativo.

---

## Teste 5 - Retry de Comunicação

1. Execute apenas o cliente.
2. Não execute o servidor.

Resultado esperado:

```text
[RETRY 1/3]
[RETRY 2/3]
[RETRY 3/3]
[FALHA]
```

Validando o mecanismo de retransmissão implementado no cliente.

