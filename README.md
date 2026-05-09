# Protocolo de Monitoramento de Sensores (IoT)
Projeto desenvolvido para a disciplina de Redes de Computadores - Engenharia Eletrônica (IFSC).

## 1. Formato da Mensagem (Serialização Bitwise)

O protocolo foi projetado para ser eficiente em termos de largura de banda, utilizando um tamanho fixo de **60 bytes** (480 bits). A estrutura divide-se em blocos binários para dados numéricos e um bloco de texto para a localização física.

### 1.1 Divisão dos Blocos (Slicing de Memória)
| Bloco | Tamanho | Conteúdo | Índices de Bytes |
| :--- | :--- | :--- | :--- |
| **Controle** | 5 Bytes | Cabeçalho com metadados e valor da leitura. | `0 a 4` |
| **Data/Hora** | 5 Bytes | Timestamp compactado (38 bits utilizados). | `5 a 9` |
| **Localização** | 50 Bytes | Identificação do local do sensor (ASCII). | `10 a 59` |

### 1.2 Detalhamento dos Campos (Campos de Bits)

#### Cabeçalho de Controle (33 bits ativos em 5 Bytes)
* **Tipo de Mensagem (2 bits):** * `0`: Cadastro
    * `1`: Leitura Periódica
    * `2`: Evento/Alarme
    * `3`: Resposta do Servidor (ACK)
* **ID do Sensor (10 bits):** Identificador numérico único (0 a 1023).
* **Tipo de Sensor (4 bits):** Define a grandeza (0=Temp, 1=Presença, 2=Fumaça, etc).
* **Indicador de Alarme (1 bit):** Flag binária (`0` Normal, `1` Alarme).
* **Valor do Sensor (16 bits):** Valor inteiro da leitura (0 a 65535).

#### Data e Hora (38 bits ativos em 5 Bytes)
* **Ano (11 bits):** Armazena o ano com offset de 2000 (Ex: 2026 é enviado como 26).
* **Mês (4 bits):** 1 a 12.
* **Dia (5 bits):** 1 a 31.
* **Hora (5 bits):** 0 a 23.
* **Minuto (6 bits):** 0 a 59.
* **Segundo (6 bits):** 0 a 59.

---

## 2. Fluxo de Comunicação

O sistema utiliza o protocolo de transporte **TCP**, garantindo a entrega dos pacotes. A comunicação é do tipo "requisição-resposta" com conexões não-persistentes.

1. **Cadastro:** O sensor envia seus dados e localização. O servidor registra no arquivo `sensores.txt`.
2. **Monitoramento:** O sensor envia leituras ou eventos. O servidor processa e salva no `log.txt`.
3. **Resposta:** Para cada pacote recebido, o servidor devolve uma confirmação (Tipo 3) espelhando os dados para validação no cliente.

---

## 3. Armazenamento de Dados (Persistência)

Os dados são persistidos em arquivos `.txt` no diretório do servidor:

* **sensores.txt:** `ID_SENSOR | TIPO | LOCALIZACAO`
    * *Objetivo:* Manter o inventário de quais sensores estão ativos na planta.
* **log.txt:** `DATA_HORA | ID | TIPO_MSG | VALOR | ALARME`
    * *Objetivo:* Histórico para auditoria e análise de eventos.

---

## 4. Tratamento de Erros e Conexão

| Erro | Solução Proposta |
| :--- | :--- |
| **Perda de Pacote** | O cliente aguarda o ACK (Tipo 3). Caso não receba, tenta o reenvio 3 vezes. |
| **Tamanho Inválido** | O servidor descarta qualquer pacote que não possua exatamente 60 bytes. |
| **Timeout** | Implementado via `socket.settimeout(5)` para evitar travamento da aplicação. |
| **Truncamento** | Strings de localização superiores a 50 caracteres são cortadas automaticamente. |

---

## 5. Justificativa Técnica

A escolha por **5 bytes** para o controle e **5 bytes** para a data deve-se ao alinhamento de memória. Embora os bits úteis totalizem 71, o uso de 10 bytes (80 bits) permite que o desempacotamento ocorra de forma isolada e limpa, evitando que bits de data e bits de controle compartilhem o mesmo byte, o que simplifica a lógica de `shift` e `mask`.