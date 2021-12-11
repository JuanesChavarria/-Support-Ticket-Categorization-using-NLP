import re
import os
import json
import boto3

def limpieza(ticket):
    ticket = re.sub(r'[^A-Za-z0-9]+',' ',ticket)
    tokens = ticket.split()
    tokens = [token for token in tokens if token.isalpha()]
    lista_nombres=[]
    lista_apellidos=[]
    for token in tokens:
        if token in lista_nombres:
            tokens.remove(token)
            continue
        elif token in lista_apellidos:
            tokens.remove(token)
            continue
    return " ".join(tokens)
    

def lambda_handler(event, context):

    nombre_ticket=event['Records'][0]['s3']['object']['key'].split("/")[-1]
    s3 = boto3.client('s3')
    # print(nombre)
    ticket=s3.get_object(
         Bucket='pruebas-clasificador',
         Key=f'transient/{nombre_ticket}',
    )['Body'].read().decode('utf-8')
    # print(ticket)
    
    ticket = limpieza(ticket)
    
    s3.put_object(
         Bucket='pruebas-clasificador',
         Key=f'raw/{nombre_ticket}',
         Body=ticket,
    )

    return None
