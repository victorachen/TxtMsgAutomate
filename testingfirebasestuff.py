#firebase run C:\Users\Lenovo\PycharmProjects\firebase\venv\main.py
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
cred = credentials.Certificate(r'C:\Users\Lenovo\PycharmProjects\firebase\venv\serviceaccountkey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()
print('hello world')
##db.collection('persons').add({'name':'John','age':40})

#(1) Add something to document
##db.collection('Vacancy').document('rent_ready').update({"Crest 1":"London"})

#(2) Remove something from document
##db.collection('Vacancy').document('just_rented').update({
##    "something":firestore.DELETE_FIELD})

#(3) Delete a document
##db.collection('Vacancy').document('rent_ready').delete()

#(4) Create a document (and add "type" field value)
db.collection('Vacancy').document('rent_ready').set({'type':'rent_ready'})
