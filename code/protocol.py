# ============================================================ #
# Define o formato da mensagem e as funções de empacotamento e #
# desempacotamento usando bitwise, conforme especificado.      #
# ============================================================ #

import struct
import datetime

# CONSTANTES DO PROTOCOLO (Tamanho em Bits)

# Cabeçalho de Controle (33 bits) --> 5 Bytes
TAM_TIPO_MSG = 2     # 0=Cad, 1=Leitura, 2=Evento, 3=Resp (2 bits cobrem isso)
TAM_ID_SENSOR = 10   # Permite até 1024 sensores
TAM_TIPO_SENSOR = 4  # Até 16 tipos (0=Temp, 1=Presença, 2=Porta)
TAM_ALARME = 1       # 0=Normal, 1=Alarme
TAM_VALOR = 16       # Valor do sensor (Inteiro de 16 bits)

# Data e Hora (38 bits) --> 5 Bytes
# Definido os tamanhos com base nos valores máximos:
TAM_DIA = 5          # 0-31 dias
TAM_MES = 4          # 0-12 meses
TAM_ANO = 11         # Permite anos até 2048 (offset de 2000 é usado para economizar bits --> 2000-4047)
TAM_HORA = 5         # 0-23 horas
TAM_MINUTO = 6       # 0-59 minutos
TAM_SEGUNDO = 6      # 0-59 segundos

# Nome do Usuário (50 caracteres) --> 50 Bytes
TAM_NOME_BYTES = 50  # 50 caracteres * 1 byte/char (pela tabela ASCII) 

# Tamanho Total da Mensagem
TAM_CABECALHO_E_DATA_BYTES = 10 # 5 bytes para o cabeçalho (33 bits) + 5 bytes para data/hora (38 bits) = 10 bytes
TAM_MSG_TOTAL = TAM_CABECALHO_E_DATA_BYTES + TAM_NOME_BYTES # Total de 60 bytes


##################################################################
# Funções Necessárias para segmentação e dessegmentação de bits  #
##################################################################

# FUNÇÕES DE EMPACOTAMENTO 

def empacotar_requisicao_cliente(tipo_msg, id_sensor, tipo_sensor, valor, alarme, localizacao):

    # Me retorna o horário e datas atuais para preencher os campos de data e hora da mensagem, implementado pelo datatimePython
    agora = datetime.datetime.now() 
    dia, mes, ano = agora.day, agora.month, agora.year
    hora, minuto, segundo = agora.hour, agora.minute, agora.second


    #################################################
    # Montagem dos 20 bits do Cabeçalho de Controle #
    #################################################

    # Ordem: Tipo de Mensagem (2) | ID do Sensor (10) | Tipo do Sensor (4) | Alarme (1) | Valor (16)
    cabecalho = 0 # Inicializa o cabeçalho vazio

    # Tipo de Mensagem
    cabecalho = (cabecalho | tipo_msg) << TAM_ID_SENSOR
    cabecalho = (cabecalho | id_sensor) << TAM_TIPO_SENSOR
    cabecalho = (cabecalho | tipo_sensor) << TAM_ALARME
    cabecalho = (cabecalho | alarme) << TAM_VALOR
    cabecalho = (cabecalho | valor)

    print(cabecalho)


    #######################################
    # Montagem dos 37 bits de Data e Hora #
    #######################################
    
    # Ordem: Ano(11) | Mes(4) | Dia(5) | Hora(5) | Minuto(6) | Segundo(6)
    
    data_hora = 0
    # Ano (com o offset)
    data_hora = (data_hora | (ano - 2000)) << TAM_MES
    # Mês
    data_hora = (data_hora | mes) << TAM_DIA
    # Dia
    data_hora = (data_hora | dia) << TAM_HORA
    # Horas
    data_hora = (data_hora | hora) << TAM_MINUTO
    # Minutos
    data_hora = (data_hora | minuto) << TAM_SEGUNDO
    # Segundos
    data_hora = (data_hora | segundo)

    print(data_hora)


    ########################################################################################
    # Serialização para Bytes (8 bytes), sendo 3 bytes do cabeçalho e 5 bytes da data/hora #
    ########################################################################################
    
    # 5 bytes para o cabeçalho (40 bits) - Big Endian
    dados_controle = cabecalho.to_bytes(5, 'big')
    # 5 bytes para data/hora (40 bits) - Big Endian
    dados_data_hora = data_hora.to_bytes(5, 'big')
    

    ####################################
    # Empacotamento do Nome (50 bytes) #
    ####################################

    # Formato string de 50 bytes, preenchida com nulos se o nome for menor que 50 caracteres
    nome_bytes = struct.pack(f'{TAM_NOME_BYTES}s', localizacao.encode('ascii'))
    

    #############################
    # Mensagem Total (59 bytes) #
    #############################

    mensagem_bytes = dados_controle + dados_data_hora + nome_bytes
    
    return mensagem_bytes


def empacotar_resposta_servidor(req_bytes, alarme_status):
    """
    Modifica a mensagem de requisição para criar uma resposta do servidor.
    Define o Tipo de Mensagem como 3 (Resposta) e atualiza o bit de Alarme.
    """
    
    # 1. Agora pegamos os primeiros 5 bytes (onde estão os 33 bits de controle)
    cabecalho = int.from_bytes(req_bytes[:5], 'big')
    
    # 2. Precisamos LIMPAR o Tipo de Mensagem (bits 31-32) e o Alarme (bit 16)
    # para inserir os novos valores de resposta.
    
    # Máscara para manter ID (bits 21-30), Tipo Sensor (17-20) e Valor (0-15)
    # E zerar o Tipo_Msg e o Alarme.
    # Shift do Alarme = TAM_VALOR (16)
    # Shift do Tipo_Msg = ID(10) + TipoS(4) + Alarme(1) + Valor(16) = 31
    
    mascara_limpeza = ~((3 << 31) | (1 << TAM_VALOR))
    novo_cabecalho = cabecalho & mascara_limpeza

    # 3. Adiciona o Tipo de Mensagem = 3 (Resposta)
    tipo_resposta = 3
    novo_cabecalho |= (tipo_resposta << 31)
    
    # 4. Adiciona o status do Alarme (vinda do parâmetro da função)
    novo_cabecalho |= (alarme_status << TAM_VALOR)

    # 5. Reconstrói os 5 bytes de controle
    dados_controle_resposta = novo_cabecalho.to_bytes(5, 'big')
    
    # 6. A resposta mantém a Data/Hora e a Localização originais
    # req_bytes[5:] pega do byte 5 até o final (byte 60)
    mensagem_bytes_resposta = dados_controle_resposta + req_bytes[5:]
    
    return mensagem_bytes_resposta

# FUNÇÃO DE DESEMPACOTAMENTO

def desempacotar_mensagem(mensagem_bytes):
    """
    Desempacota uma sequência de 60 bytes (5 controle + 5 data + 50 local)
    e retorna um dicionário com os dados do sensor.
    """
    
    # Extração da Localização (os últimos 50 bytes)
    # Agora começa no índice 10 (5 controle + 5 data)
    local_bytes = mensagem_bytes[10:]
    localizacao = struct.unpack(f'{TAM_NOME_BYTES}s', local_bytes)[0].decode('ascii').strip('\x00')
    
    # 2. Divisão dos blocos binários (os primeiros 10 bytes)
    # cabecalho_data_bytes terá 10 bytes no total
    cabecalho_bytes = mensagem_bytes[:5]    # 0 a 4 (5 bytes)
    data_hora_bytes = mensagem_bytes[5:10]  # 5 a 9 (5 bytes)

    # Conversão para inteiros para manipulação bitwise
    cabecalho = int.from_bytes(cabecalho_bytes, 'big')
    data_hora = int.from_bytes(data_hora_bytes, 'big')

    # Extração do Cabeçalho (do MENOS significativo para o MAIS significativo)
    # (Ordem de empacotamento foi: TipoMsg -> ID -> TipoSensor -> Alarme -> Valor). Portanto, extraímos na ordem inversa.
    
    # Valor do Sensor (16 bits)
    valor = cabecalho & ((1 << TAM_VALOR) - 1)
    cabecalho >>= TAM_VALOR
    
    # Indicador de Alarme (1 bit)
    alarme = cabecalho & ((1 << TAM_ALARME) - 1)
    cabecalho >>= TAM_ALARME
    
    # Tipo de Sensor (4 bits)
    tipo_sensor = cabecalho & ((1 << TAM_TIPO_SENSOR) - 1)
    cabecalho >>= TAM_TIPO_SENSOR
    
    # ID do Sensor (10 bits)
    id_sensor = cabecalho & ((1 << TAM_ID_SENSOR) - 1)
    cabecalho >>= TAM_ID_SENSOR
    
    # Tipo de Mensagem (2 bits)
    tipo_msg = cabecalho & ((1 << TAM_TIPO_MSG) - 1)

    
    # Extração de Data/Hora (do MENOS significativo para o MAIS)
    # (Ordem de empacotamento: Ano -> Mes -> Dia -> Hora -> Minuto -> Segundo)
    
    segundo = data_hora & ((1 << TAM_SEGUNDO) - 1)
    data_hora >>= TAM_SEGUNDO
    
    minuto = data_hora & ((1 << TAM_MINUTO) - 1)
    data_hora >>= TAM_MINUTO
    
    hora = data_hora & ((1 << TAM_HORA) - 1)
    data_hora >>= TAM_HORA
    
    dia = data_hora & ((1 << TAM_DIA) - 1)
    data_hora >>= TAM_DIA
    
    mes = data_hora & ((1 << TAM_MES) - 1)
    data_hora >>= TAM_MES
    
    ano = (data_hora & ((1 << TAM_ANO) - 1)) + 2000

    # Retorno dos dados processados
    return {
        "tipo_msg": tipo_msg,       # 0=Cad, 1=Leitura, 2=Evento, 3=Resp
        "id_sensor": id_sensor,
        "tipo_sensor": tipo_sensor,
        "alarme": alarme,           # 0=Normal, 1=Alarme
        "valor": valor,
        "localizacao": localizacao,
        "data_hora": f"{dia:02d}/{mes:02d}/{ano} {hora:02d}:{minuto:02d}:{segundo:02d}"
    }
