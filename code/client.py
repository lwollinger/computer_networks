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

import socket
import protocol

HOST = '127.0.0.1'
PORT = 65432

# Sensores (exemplo)
sensor_temp = {
    "id": 101,
    "tipo": 1, # Temperatura
    "local": "Laboratorio 01"
}

sensor_presenca = {
    "id": 202,
    "tipo": 2, # Presença
    "local": "Corredor Norte"
}

def enviar_ao_servidor(tipo_msg, valor=0, alarme=0, sensor=None):
    """
    Abre conexão, envia 60 bytes e recebe ACK.
    """
    if not sensor:
        print("Erro: Nenhuma configuração de sensor fornecida.")
        return

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((HOST, PORT))
        
        # O empacotador usa os dados do dicionário que você passou
        pacote = protocol.empacotar_requisicao_cliente(
            tipo_msg, 
            sensor["id"], 
            sensor["tipo"], 
            valor, 
            alarme, 
            sensor["local"]
        )
        
        sock.sendall(pacote)
        
        resposta_bytes = sock.recv(60)
        if resposta_bytes:
            dados_resp = protocol.desempacotar_mensagem(resposta_bytes)
            print(f"\n[SERVIDOR] ACK Recebido - Sensor: {dados_resp['id_sensor']}")
            print(f"Status: {dados_resp['tipo_msg']} | Hora: {dados_resp['data_hora']}")
        
        sock.close()

    except Exception as e:
        print(f"Erro na comunicação: {e}")

def cadastrar(sensor):
    print(f"\nIniciando Cadastro: {sensor['local']}")
    enviar_ao_servidor(tipo_msg=0, sensor=sensor)

def enviar_leitura(sensor, valor):
    print(f"Enviando leitura de {valor} para ID {sensor['id']}...")
    enviar_ao_servidor(tipo_msg=1, valor=valor, sensor=sensor)

def enviar_evento_alarme(sensor):
    print(f"### ENVIANDO EVENTO DE ALARME: {sensor['local']} ###")
    # tipo_msg=2 é 'Evento' conforme seu README
    # alarme=1 ativa a flag de alarme
    enviar_ao_servidor(tipo_msg=2, valor=99, alarme=1, sensor=sensor)



# Arrumar aqui 
if __name__ == "__main__":
    # Menu simples para você testar
    while True:
        print("\n--- SIMULADOR DE SENSOR ---")
        print("1. Enviar Cadastro")
        print("2. Enviar Leitura (Normal)")
        print("3. Enviar Evento (Alarme)")
        print("4. Sair")
        opcao = input("Escolha: ")
        
        if opcao == '1': cadastrar(sensor_temp)
        elif opcao == '2': enviar_leitura()
        elif opcao == '3': enviar_evento_alarme()
        elif opcao == '4': break