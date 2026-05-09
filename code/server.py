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

def recebe_mensagem_cadastro_cliente():
    """
    Recebe a mensagem de cadastro do cliente, desempacota os dados e armazena as informações do sensor em um arquivo de texto.
    """
def recebe_mensagem_leitura():
    """
    Recebe a mensagem de leitura do cliente, desempacota os dados e registra o evento em um arquivo de log.
    """
def verifica_condicoes_alarme():
    """
    Verifica as condições de alarme com base nas leituras recebidas e envia uma resposta ao cliente indicando se o alarme foi acionado ou não.
    """
def envia_resposta_cliente():
    """
    Envia uma resposta ao cliente indicando se o alarme foi acionado ou não.
    """




host = '' 
porta = 7000 
addr = (host, porta) 
#criar o socket para o servidor passando a família do protocolo de transporte 
#socket.AF_INET define que é um protocolo para rede IP (AF_BLUETOOTH definiria comunicação bluetooth, por exemplo)
#socket.SOCK_STREAM para TCP
#socket.SOCK_DGRAM para UDP
socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#reserva o socket para a nossa aplicação
socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
#define quais IP's e em qual porta o server vai aguardar conexão
socket_servidor.bind(addr) 
#define que servidor aguarda conexões e quantas conexão serão recebidas. Não é necessário caso UDP
socket_servidor.listen(10) 
print ('aguardando conexao')
con, cliente = socket_servidor.accept() #espera por conexão
print ('conectado') 
print ("aguardando mensagem") 
recebe = con.recv(1024) #recebe mensagem (em bytes, com tamanho max definido pelo parâmetro)
print ("mensagem recebida: ")  
print(recebe.decode()) 
socket_servidor.close()