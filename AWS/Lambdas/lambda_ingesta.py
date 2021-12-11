import os
import uuid
import json
import boto3

def lambda_handler(event, context):
    try:
        
        s3 = boto3.client('s3')
        s3.put_object(
             Bucket='pruebas-clasificador',
             Key=f'transient/{uuid.uuid1()}.txt',
             Body=event['body'],
        )
        
        return "Ingesta exitosa"
    except:
        return "Ingesta fallida"
