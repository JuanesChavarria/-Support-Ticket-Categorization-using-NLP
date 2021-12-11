import os
import re
import json
import nltk
import boto3
import joblib
import numpy as np

nltk.download("punkt")
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
nltk.download('words')
stopwords_nltk = set(nltk.corpus.stopwords.words('english'))
tag_dict = {
    "J": nltk.corpus.wordnet.ADJ,
    "N": nltk.corpus.wordnet.NOUN,
    "V": nltk.corpus.wordnet.VERB,
    "R": nltk.corpus.wordnet.ADV
}
lemmatizer = nltk.stem.WordNetLemmatizer()
noun=nltk.corpus.wordnet.NOUN
stemmer=nltk.stem.SnowballStemmer("english")
          
def obtenerModelo(bucket,modelo):
    S3 = boto3.client('s3')
    S3.download_file(bucket,"modelos/"+modelo,modelo)
    return joblib.load(modelo)
    
def procesamiento_raw(bucket,ticket):
    S3 = boto3.client('s3')
    texto = S3.get_object(Bucket=bucket,Key=f"raw/{ticket}")['Body'].read().decode('utf-8')

    tokens=nltk.word_tokenize(texto)
    tokens=[re.sub(r'[^A-Za-z0-9]+',' ',token) for token in tokens]
    tokens=[token.lower() for token in tokens if len(token)>2]
    tokens=[token for token in tokens if token not in stopwords_nltk]
    tokens=[lemmatizer.lemmatize(token, tag_dict.get(nltk.pos_tag([token])[0][1][0].upper(), noun)) for token in tokens]
    tokens=[stemmer.stem(w) for w in tokens]
    
    vectorizer=obtenerModelo(bucket,"vectorizer_externo.joblib")
    tfidf=vectorizer.transform([" ".join(tokens)]).toarray()
    
    datos_trusted=json.dumps([{'tokens':tokens,'tfidf':list(tfidf[0].astype(float))}], indent=4)
    nombre=ticket.split(".")[0]
    S3.put_object(Body=datos_trusted,Bucket=bucket,Key=f"trusted/{nombre}.json")
    
def text2tfidf(texto,vectorizer):
    tokens=nltk.word_tokenize(texto)
    tokens=[re.sub(r'[^A-Za-z0-9]+',' ',token) for token in tokens]
    tokens=[token.lower() for token in tokens if len(token)>2]
    tokens=[token for token in tokens if token not in stopwords_nltk]
    tokens=[lemmatizer.lemmatize(token, tag_dict.get(nltk.pos_tag([token])[0][1][0].upper(), noun)) for token in tokens]
    tokens=[stemmer.stem(w) for w in tokens]
    return vectorizer.transform([" ".join(tokens)]).toarray()
    
def procesamiento_trusted(bucket,ticket):
    categorias={0:{1: 'Admin', 2: 'Mylife', 3: 'Master Data Input', 4: 'Payroll', 0: 'Otros'},
          1:{1: 'Bswift',2: 'OM (organizationa mgmt)',3: 'Leaves',4: 'Year-End',5: 'Time',6: 'Systems NA',0: 'Otros'}}
    S3 = boto3.client('s3')
    ticket_json = json.loads(S3.get_object(Bucket=bucket,Key=f"trusted/{ticket}")['Body'].read().decode('utf-8'))[0]
    tfidf=ticket_json['tfidf']
    modelo=obtenerModelo(bucket,"modelo_externo.joblib")
    clasificacion=modelo.predict(np.array(tfidf).reshape(1,len(tfidf)))
    clasificador=0
    if clasificacion[0]==0:
        vectorizer_interno=obtenerModelo(bucket,"vectorizer_interno.joblib")
        modelo_interno=obtenerModelo(bucket,"modelo_interno.joblib")
        tfidf_interno=text2tfidf(" ".join(ticket_json['tokens']),vectorizer_interno)
        clasificacion=modelo_interno.predict(tfidf_interno)
        clasificador=1
    
    datos_refined=json.dumps({'tokens':ticket_json['tokens'],'clasificacion':categorias[clasificador][clasificacion[0]]}, indent=4)      
    S3.put_object(Body=datos_refined,Bucket=bucket,Key=f"refined/{ticket}")

bucket="pruebas-clasificador"

S3 = boto3.client('s3')

tickets = S3.list_objects_v2(Bucket=bucket, Prefix="transient/")['Contents']

ticket = [obj['Key'] for obj in sorted(tickets, key=lambda obj: int(obj['LastModified'].strftime('%s')))][1]

ticket = (ticket.split("/")[-1]).split(".")[0]

procesamiento_raw(bucket,f"{ticket}.txt")
procesamiento_trusted(bucket,f"{ticket}.json")
    