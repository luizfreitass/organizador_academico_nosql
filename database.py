from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
import os

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

usuarios     = db["usuarios"]
professores  = db["professores"]
disciplinas  = db["disciplinas"]
fotos        = db["fotos"]

def create_indexes():
    """
    Cria (ou garante) índices para consultas rápidas.
    Chamado pelo evento 'startup' do FastAPI.
    """
    fotos.create_index([("disciplina_id", ASCENDING)])
    fotos.create_index([("professor_id", ASCENDING)])
    fotos.create_index([("semestre", ASCENDING)])
    fotos.create_index([("data_upload", DESCENDING)])  # para ordenação recente
