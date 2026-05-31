# ======================================================================
# ARQUIVO: cliente.py
#
# Lado Cliente:
# 1) Enviar mensagens de cadastro; 
# 2) Enviar leituras do sensor; 
# 3) Enviar eventos; 
# 4) Receber resposta do servidor; 
# 5) Mostrar a resposta na tela. 
# ======================================================================
#
# Melhorias implementadas:
#   [FIX]  tipo de sensor correto: 0=Temperatura, 1=Presença (estava trocado)
#   [FIX]  chamadas no menu com argumentos corretos (opcoes 2 e 3 travavam)
#   [NEW]  recv() em loop — garante leitura dos 60 bytes de resposta completos
#   [NEW]  Retry com backoff exponencial — tenta até 3 vezes antes de desistir
#   [NEW]  ACK validado — confirma que a resposta é realmente para este sensor
#   [NEW]  Exibição detalhada do ACK — mostra alarme, valor e localização
#   [NEW]  Menu estendido — permite escolher sensor e digitar valor de leitura
# ======================================================================

import socket
import protocol

# ── Configurações ──────────────────────────────────────────────────────────────
HOST        = '127.0.0.1'
PORT        = 65432
TAM_PACOTE  = 60
MAX_RETRY   = 3      # tentativas máximas por envio
TIMEOUT_BASE = 5     # segundos — multiplicado pela tentativa (backoff)

# ── Definição dos sensores ─────────────────────────────────────────────────────
# [FIX] Tipos corrigidos: 0=Temperatura, 1=Presença (estavam trocados)
sensor_temp = {
    "id":    101,
    "tipo":  0,              # 0 = Temperatura (corrigido de 1)
    "local": "Laboratorio 01"
}

sensor_presenca = {
    "id":    202,
    "tipo":  1,              # 1 = Presença (corrigido de 2)
    "local": "Corredor Norte"
}

SENSORES_DISPONIVEIS = {
    "1": sensor_temp,
    "2": sensor_presenca,
}

# ── Recepção robusta ───────────────────────────────────────────────────────────

def receber_pacote_completo(sock: socket.socket, tamanho: int) -> bytes:
    """
    [NEW] Garante leitura de exatamente `tamanho` bytes do stream TCP.
    TCP pode entregar fragmentos — recv(N) não garante N bytes de uma vez.
    """
    buffer = b''
    while len(buffer) < tamanho:
        fragmento = sock.recv(tamanho - len(buffer))
        if not fragmento:
            raise ConnectionError(
                f"Servidor fechou a conexão antes de enviar o ACK completo "
                f"({len(buffer)}/{tamanho} bytes recebidos)."
            )
        buffer += fragmento
    return buffer

# ── Envio com retry ────────────────────────────────────────────────────────────

def enviar_ao_servidor(tipo_msg: int, valor: int = 0, alarme: int = 0,
                       sensor: dict = None) -> dict | None:
    """
    [NEW] Envia pacote ao servidor com retry e backoff exponencial.
    Tenta até MAX_RETRY vezes antes de desistir.
    Retorna dicionário com dados do ACK ou None em caso de falha total.
    """
    if sensor is None:
        print("[ERRO] Nenhum sensor configurado.")
        return None

    for tentativa in range(1, MAX_RETRY + 1):
        timeout = TIMEOUT_BASE * tentativa   # backoff: 5s → 10s → 15s
        sock = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((HOST, PORT))

            pacote = protocol.empacotar_requisicao_cliente(
                tipo_msg,
                sensor["id"],
                sensor["tipo"],
                valor,
                alarme,
                sensor["local"]
            )
            sock.sendall(pacote)

            # [NEW] Loop de recv — garante os 60 bytes do ACK
            resposta_bytes = receber_pacote_completo(sock, TAM_PACOTE)
            dados_resp     = protocol.desempacotar_mensagem(resposta_bytes)

            # [NEW] Valida ACK — confirma que é resposta para este sensor
            if dados_resp['tipo_msg'] != 3:
                print(f"[AVISO] Resposta inesperada: tipo_msg={dados_resp['tipo_msg']} (esperado 3)")
                continue

            if dados_resp['id_sensor'] != sensor["id"]:
                print(f"[AVISO] ACK para sensor errado: "
                      f"recebido={dados_resp['id_sensor']}, esperado={sensor['id']}")
                continue

            # Sucesso
            if tentativa > 1:
                print(f"[OK] Comunicação estabelecida na tentativa {tentativa}/{MAX_RETRY}")
            return dados_resp

        except socket.timeout:
            print(f"[RETRY {tentativa}/{MAX_RETRY}] Timeout após {timeout}s — sem resposta do servidor.")
        except ConnectionRefusedError:
            print(f"[RETRY {tentativa}/{MAX_RETRY}] Servidor recusou conexão em {HOST}:{PORT}.")
        except ConnectionError as e:
            print(f"[RETRY {tentativa}/{MAX_RETRY}] Erro de conexão: {e}")
        except Exception as e:
            print(f"[RETRY {tentativa}/{MAX_RETRY}] Erro inesperado: {type(e).__name__}: {e}")
        finally:
            if sock:
                sock.close()

    print(f"[FALHA] Sensor {sensor['id']} — dado perdido após {MAX_RETRY} tentativas.")
    return None

# ── Exibição do ACK ────────────────────────────────────────────────────────────

def exibir_ack(dados_resp: dict) -> None:
    """[NEW] Exibe o ACK recebido de forma detalhada e legível."""
    if not dados_resp:
        return

    status_alarme = "⚠  ALARME ATIVO" if dados_resp['alarme'] else "✓  Normal"
    print(f"\n  ┌─ ACK do Servidor ──────────────────────────┐")
    print(f"  │  Sensor     : {dados_resp['id_sensor']:04d}")
    print(f"  │  Valor      : {dados_resp['valor']}")
    print(f"  │  Timestamp  : {dados_resp['data_hora']}")
    print(f"  │  Local      : {dados_resp['localizacao']}")
    print(f"  │  Status     : {status_alarme}")
    print(f"  └────────────────────────────────────────────┘")

# ── Funções de operação ────────────────────────────────────────────────────────

def cadastrar(sensor: dict) -> None:
    print(f"\n[→] Enviando Cadastro — {sensor['local']} (ID:{sensor['id']:04d})")
    ack = enviar_ao_servidor(tipo_msg=0, sensor=sensor)
    exibir_ack(ack)


def enviar_leitura(sensor: dict, valor: int) -> None:
    print(f"\n[→] Enviando Leitura — {sensor['local']} (ID:{sensor['id']:04d}) valor={valor}")
    ack = enviar_ao_servidor(tipo_msg=1, valor=valor, sensor=sensor)
    exibir_ack(ack)


def enviar_evento_alarme(sensor: dict) -> None:
    print(f"\n[→] Enviando Evento de Alarme — {sensor['local']} (ID:{sensor['id']:04d})")
    ack = enviar_ao_servidor(tipo_msg=2, valor=99, alarme=1, sensor=sensor)
    exibir_ack(ack)

# ── Menu interativo ─────────────────────────────────────────────────────────────

def selecionar_sensor() -> dict | None:
    """Exibe lista de sensores disponíveis e retorna o escolhido."""
    print("\n  Sensores disponíveis:")
    for key, s in SENSORES_DISPONIVEIS.items():
        print(f"    {key}. ID:{s['id']:04d} — {s['local']}")
    escolha = input("  Escolha o sensor: ").strip()
    sensor = SENSORES_DISPONIVEIS.get(escolha)
    if not sensor:
        print("[ERRO] Sensor inválido.")
    return sensor


def menu_principal() -> None:
    while True:
        print("\n" + "=" * 45)
        print("       SIMULADOR DE SENSOR IoT")
        print("=" * 45)
        print("  1. Enviar Cadastro")
        print("  2. Enviar Leitura")
        print("  3. Enviar Evento de Alarme")
        print("  4. Sair")
        print("-" * 45)
        opcao = input("  Escolha: ").strip()

        if opcao == '1':
            sensor = selecionar_sensor()
            if sensor:
                cadastrar(sensor)

        elif opcao == '2':
            sensor = selecionar_sensor()
            if sensor:
                try:
                    # Sensor de temperatura
                    if sensor["tipo"] == 0:
                        temp = float(input("  Temperatura (°C): ").strip())
                        # Valores, EX: 23.7°C -> 237
                        valor = int(temp * 10) # [FIX] Arrumei o valor de temperatura para ser multiplicado por 10, considerando que o protocolo espera um inteiro (ex: 23.7°C → 237).
                    # Sensor de presença
                    elif sensor["tipo"] == 1:
                        valor = int(input("  Presença (0=Não / 1=Sim): ").strip())
                        if valor not in (0, 1):
                            print("[ERRO] Use apenas 0 ou 1.")
                            continue
                    enviar_leitura(sensor, valor)
                except ValueError:
                    print("[ERRO] Valor inválido.")

        elif opcao == '3':
            sensor = selecionar_sensor()
            if sensor:
                enviar_evento_alarme(sensor)

        elif opcao == '4':
            print("Encerrando simulador.")
            break

        else:
            print("[ERRO] Opção inválida.")


if __name__ == "__main__":
    menu_principal()