from pymongo import MongoClient
import pandas as pd

client = MongoClient('localhost', 27017)
db = client.gogumacat

CONST_SI_COL = "시도명"
CONST_GU_COL = "시군구명"
CONST_DONG_COL = "읍면동명"

data = pd.read_csv('juso.csv')
data = data.where(pd.notnull(data), None)

for i in range(len(data)):

    si=data[CONST_SI_COL][i]
    gu=data[CONST_GU_COL][i]
    dong=data[CONST_DONG_COL][i]

    if dong == None:
        continue

    doc = {
        'si': si,
        'gu': gu,
        'dong': dong
    }
    db.korea_address.insert_one(doc)

