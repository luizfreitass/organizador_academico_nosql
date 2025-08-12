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
    Índices usados pelas buscas e relatórios.
    Chamado no evento 'startup' do FastAPI.
    """
    # ---- FOTOS ----
    # Busca por disciplina + ordenação por data (rota /fotos/search e analytics)
    fotos.create_index([("disciplina_id", ASCENDING), ("data_upload", DESCENDING)])

    # Top contribuidores e filtros por usuário + data (analytics)
    fotos.create_index([("usuario_id", ASCENDING), ("data_upload", DESCENDING)])

    # Filtros adicionais usados em relatórios
    fotos.create_index([("professor_id", ASCENDING)])
    fotos.create_index([("semestre", ASCENDING)])

    # ---- USUÁRIOS ---- (boa prática)
    usuarios.create_index([("email", ASCENDING)], unique=True)

    # ---- DISCIPLINAS ---- (listagens/relatórios)
    disciplinas.create_index([("nome", ASCENDING)])
    disciplinas.create_index([("semestre", ASCENDING)])

    # ---- PROFESSORES ---- (busca por nome)
    professores.create_index([("nome", ASCENDING)])

    print("Índices criados/garantidos com sucesso!")