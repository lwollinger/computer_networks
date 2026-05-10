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

import socket
import protocol

# Configurações do Servidor
HOST = '127.0.0.1'
PORT = 65432

def salvar_em_arquivo(nome_arquivo, linha):
    """
    Auxiliar para escrita em .txt
    """
    with open(nome_arquivo, "a", encoding="utf-8") as f:
        f.write(linha + "\n")

def recebe_mensagem_cadastro_cliente(dados):
    """
        Armazena ID, Tipo e Localização no arquivo de sensores.
    """
    linha = f"ID:{dados['id_sensor']} | Tipo:{dados['tipo_sensor']} | Local:{dados['localizacao']}"
    salvar_em_arquivo("sensores.txt", linha)
    print(f"[CADASTRO] Sensor {dados['id_sensor']} registrado.")

def recebe_mensagem_leitura(dados):
    """Registra o evento completo no arquivo de log."""
    # O PDF pede: data/hora, ID, tipo evento, valor e alarme
    tipo_evento = "LEITURA" if dados['tipo_msg'] == 1 else "EVENTO"
    linha = (f"{dados['data_hora']} | ID:{dados['id_sensor']} | "
             f"Evento:{tipo_evento} | Valor:{dados['valor']} | Alarme:{dados['alarme']}")
    salvar_em_arquivo("log.txt", linha)
    print(f"[LOG] Registro do sensor {dados['id_sensor']} salvo.")

def verifica_condicoes_alarme(dados):
    """
    Verifica se o valor ultrapassou um limite ou se o bit de alarme veio ativo.
    Retorna 1 para alarme ativo, 0 para normal.
    """
    # Exemplo: se for temperatura (Tipo 1) e passar de 40 graus, força alarme
    if dados['tipo_sensor'] == 1 and dados['valor'] > 40:
        return 1
    # Ou se o próprio sensor já mandou o bit de alarme ativo
    return dados['alarme']

def envia_resposta_cliente(conn, pacote_original, status_alarme):
    """Gera o ACK de 60 bytes e envia."""
    resposta = protocol.empacotar_resposta_servidor(pacote_original, status_alarme)
    conn.sendall(resposta)
    print(f"[RESPOSTA] ACK enviado com status Alarme={status_alarme}")

def iniciar_servidor():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Servidor Rodando em {HOST}:{PORT}...")

    while True:
        conn, addr = server.accept()
        try:
            pacote_bruto = conn.recv(60)
            if len(pacote_bruto) == 60:
                # 1. Desempacota os bits
                dados = protocol.desempacotar_mensagem(pacote_bruto)
                
                # 2. Verifica se é Cadastro (0) ou Leitura/Evento (1 e 2)
                if dados['tipo_msg'] == 0:
                    recebe_mensagem_cadastro_cliente(dados)
                else:
                    recebe_mensagem_leitura(dados)
                
                # 3. Processa lógica de alarme
                status_alarme = verifica_condicoes_alarme(dados)
                
                # 4. Responde (ACK)
                envia_resposta_cliente(conn, pacote_bruto, status_alarme)
                
        except Exception as e:
            print(f"Erro no processamento: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    iniciar_servidor()