# ======================================================================
# ARQUIVO: server.py
#
# Lado Servidor:
# A aplicação do servidor será a central de monitoramento e deverá:
# 1) Receber cadastro de sensores;
#   1.1) Armazenar sensores em arquivo;
# 2) Receber leituras e eventos dos sensores;
#   2.1) Registrar eventos em arquivo de log;
# 3) Verificar condições de alarme;
# 4) Enviar resposta aos clientes.
#  
# Armazenamento de dados:
# O sistema deverá utilizar arquivos em formato TXT para armazenamento de dados, sendo um
# arquivo de sensores (com ID do sensor, tipo e localização) e um arquivo de registro (log)
# (com data e hora, ID do sensor, tipo de evento, valor e indicação de alarme).
# ======================================================================
#
# Melhorias implementadas:
#   [FIX]  Tipo de sensor correto para alarme (0=Temperatura, não 1)
#   [FIX]  recv() em loop — garante leitura de exatamente 60 bytes do stream TCP
#   [NEW]  Servidor multithread — atende múltiplos sensores simultaneamente
#   [NEW]  Lock de arquivo — escrita thread-safe em sensores.txt e log_eventos.txt
#   [NEW]  Verificação de duplicata no cadastro — não registra o mesmo ID duas vezes
#   [NEW]  Log unificado em log_eventos.txt com formato legível e padronizado
#   [NEW]  Retry no recv — tolerante a fragmentação de pacotes TCP
# ======================================================================

import socket
import threading
import protocol

# ── Configurações ──────────────────────────────────────────────────────────────
HOST            = '127.0.0.1'
PORT            = 65432
TAM_PACOTE      = 60

ARQUIVO_SENSORES = "sensores.txt"
ARQUIVO_LOG      = "log_eventos.txt"

# Limites de alarme por tipo de sensor
LIMITES_ALARME = {
    0: 40,   # Temperatura  > 40 °C
    1: None, # Presença     — sem limite numérico, alarme vem pelo bit
    2: None, # Porta/Fumaça — sem limite numérico, alarme vem pelo bit
    3: None, # Falha Equip  — sem limite numérico, alarme vem pelo bit
}

NOMES_TIPO_MSG  = {0: "CADASTRO", 1: "LEITURA ", 2: "EVENTO  ", 3: "RESP_ACK"}
NOMES_TIPO_SENS = {0: "TEMPERATURA", 1: "PRESENCA   ", 2: "FUMACA     ", 3: "FALHA_EQUIP"}

# Lock global — protege escrita simultânea nos arquivos .txt
_lock_arquivo = threading.Lock()

# ── Utilitários de arquivo ─────────────────────────────────────────────────────

def salvar_em_arquivo(nome_arquivo: str, linha: str) -> None:
    """Escrita thread-safe em qualquer arquivo .txt."""
    with _lock_arquivo:
        with open(nome_arquivo, "a", encoding="utf-8") as f:
            f.write(linha + "\n")


def sensor_ja_cadastrado(id_sensor: int) -> bool:
    """Verifica se o ID já existe em sensores.txt para evitar duplicatas."""
    try:
        with _lock_arquivo:
            with open(ARQUIVO_SENSORES, "r", encoding="utf-8") as f:
                for linha in f:
                    if f"ID:{id_sensor:04d}" in linha:
                        return True
    except FileNotFoundError:
        pass
    return False

# ── Handlers de mensagem ───────────────────────────────────────────────────────

def processar_cadastro(dados: dict) -> None:
    """
    Armazena ID, Tipo e Localização no arquivo de sensores.
    Ignorado se o sensor já estiver cadastrado (evita duplicatas por retry do cliente).
    """
    id_s = dados['id_sensor']

    if sensor_ja_cadastrado(id_s):
        print(f"[CADASTRO] Sensor {id_s:04d} já cadastrado — ignorando duplicata.")
        return

    tipo_nome = NOMES_TIPO_SENS.get(dados['tipo_sensor'], f"TIPO_{dados['tipo_sensor']}")
    linha = (
        f"ID:{id_s:04d} | "
        f"Tipo:{tipo_nome} | "
        f"Local:{dados['localizacao']}"
    )
    salvar_em_arquivo(ARQUIVO_SENSORES, linha)
    print(f"[CADASTRO] Sensor {id_s:04d} registrado em {ARQUIVO_SENSORES}.")


def processar_leitura_evento(dados: dict, status_alarme: int) -> None:
    """
    Registra leitura ou evento no arquivo de log com formato unificado e legível.
    Formato: DATA_HORA | ID | SENSOR | EVENTO | VALOR | STATUS
    """
    tipo_evento = NOMES_TIPO_MSG.get(dados['tipo_msg'], "DESCONHECIDO")
    tipo_sensor = NOMES_TIPO_SENS.get(dados['tipo_sensor'], f"TIPO_{dados['tipo_sensor']}")
    status      = "*** ALARME ***" if status_alarme else "NORMAL        "

    linha = (
        f"{dados['data_hora']} | "
        f"ID:{dados['id_sensor']:04d} | "
        f"SENSOR:{tipo_sensor} | "
        f"EVENTO:{tipo_evento} | "
        f"VALOR:{dados['valor']:>6} | "
        f"STATUS:{status}"
    )
    salvar_em_arquivo(ARQUIVO_LOG, linha)
    print(f"[LOG] Sensor {dados['id_sensor']:04d} — {tipo_evento.strip()} "
          f"valor={dados['valor']} {'⚠ ALARME' if status_alarme else ''}")

# ── Lógica de alarme ───────────────────────────────────────────────────────────

def verificar_alarme(dados: dict) -> int:
    """
    Retorna 1 se alarme deve ser ativado, 0 caso contrário.
    Critérios:
      - Bit de alarme já veio ativo pelo cliente (qualquer tipo de sensor).
      - Valor ultrapassa o limite definido em LIMITES_ALARME para o tipo de sensor.
    """
    if dados['alarme'] == 1:
        return 1

    limite = LIMITES_ALARME.get(dados['tipo_sensor'])
    if limite is not None and dados['valor'] > limite:
        return 1

    return 0

# ── Recepção robusta ────────────────────────────────────────────────────────────

def receber_pacote_completo(conn: socket.socket, tamanho: int) -> bytes:
    """
    [FIX] Garante leitura de exatamente `tamanho` bytes do stream TCP.
    TCP pode entregar fragmentos — recv(N) não garante N bytes de uma vez.
    """
    buffer = b''
    while len(buffer) < tamanho:
        fragmento = conn.recv(tamanho - len(buffer))
        if not fragmento:
            raise ConnectionError(
                f"Conexão encerrada antes de receber pacote completo "
                f"({len(buffer)}/{tamanho} bytes recebidos)."
            )
        buffer += fragmento
    return buffer

# ── Handler de conexão (roda em thread própria) ────────────────────────────────

def handle_conexao(conn: socket.socket, addr: tuple) -> None:
    """
    Processa UMA conexão de sensor.
    Executado em thread separada pelo servidor multithread.
    """
    ip, porta = addr
    print(f"[CONEXÃO] {ip}:{porta}")

    try:
        # [FIX] Loop de recv — garante os 60 bytes completos
        pacote_bruto = receber_pacote_completo(conn, TAM_PACOTE)

        # Desempacota os bits
        dados = protocol.desempacotar_mensagem(pacote_bruto)

        # Calcula status de alarme antes de salvar no log
        status_alarme = verificar_alarme(dados)

        # Despacha para o handler correto
        if dados['tipo_msg'] == 0:
            processar_cadastro(dados)
        else:
            processar_leitura_evento(dados, status_alarme)

        # Envia ACK (tipo_msg=3) com status de alarme atualizado
        resposta = protocol.empacotar_resposta_servidor(pacote_bruto, status_alarme)
        conn.sendall(resposta)
        print(f"[RESPOSTA] ACK enviado para {ip}:{porta} — alarme={status_alarme}")

    except ConnectionError as e:
        print(f"[ERRO CONEXÃO] {ip}:{porta} — {e}")
    except Exception as e:
        print(f"[ERRO] {ip}:{porta} — {type(e).__name__}: {e}")
    finally:
        conn.close()

# ── Servidor principal ──────────────────────────────────────────────────────────

def iniciar_servidor() -> None:
    """
    [NEW] Servidor multithread — cada conexão de sensor roda em thread própria.
    Permite N sensores simultâneos sem bloqueio.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()

    print("=" * 60)
    print(f"  Central de Monitoramento IoT")
    print(f"  Endereço : {HOST}:{PORT}")
    print(f"  Sensores : {ARQUIVO_SENSORES}")
    print(f"  Log      : {ARQUIVO_LOG}")
    print(f"  Modo     : Multithread")
    print("=" * 60)

    try:
        while True:
            conn, addr = server.accept()
            # [NEW] Thread separada por conexão — não bloqueia o loop principal
            t = threading.Thread(
                target=handle_conexao,
                args=(conn, addr),
                daemon=True
            )
            t.start()
    except KeyboardInterrupt:
        print("\n[SERVIDOR] Encerrado pelo usuário.")
    finally:
        server.close()


if __name__ == "__main__":
    iniciar_servidor()