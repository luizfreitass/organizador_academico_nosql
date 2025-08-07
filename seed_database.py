from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os

# Carrega variáveis do .env
load_dotenv()

# Conexão com MongoDB usando variáveis de ambiente
mongo_uri = os.getenv("MONGO_URI")
db_name = os.getenv("DB_NAME")
client = MongoClient(mongo_uri)
db = client[db_name]

# Apagar coleções existentes (para recriar do zero)
db.usuarios.drop()
db.disciplinas.drop()
db.professores.drop()
db.fotos.drop()

# Coleção: usuários
usuarios = [
    {"_id": "u001", "nome": "Ana Costa", "email": "ana@email.com"},
    {"_id": "u002", "nome": "Bruno Lima", "email": "bruno@email.com"},
    {"_id": "u003", "nome": "Carla Mendes", "email": "carla@email.com"}
]
db.usuarios.insert_many(usuarios)

# Coleção: professores
professores = [
    {"_id": "p001", "nome": "Prof. João Silva"},
    {"_id": "p002", "nome": "Profa. Marina Alves"},
    {"_id": "p003", "nome": "Prof. Ricardo Borges"}
]
db.professores.insert_many(professores)

# Coleção: disciplinas
disciplinas = [
    {"_id": "d001", "nome": "Algoritmos", "semestre": "1º", "professor_id": "p001"},
    {"_id": "d002", "nome": "Banco de Dados", "semestre": "3º", "professor_id": "p002"},
    {"_id": "d003", "nome": "Engenharia de Software", "semestre": "4º", "professor_id": "p003"}
]
db.disciplinas.insert_many(disciplinas)

# Coleção: fotos (conteúdos da lousa)
fotos = [
    {
        "usuario_id": "u001",
        "disciplina_id": "d001",
        "professor_id": "p001",
        "semestre": "1º",
        "data_upload": datetime(2025, 7, 28, 10, 30),
        "url_foto": "https://exemplo.com/fotos/aula1_algoritmos.jpg",
        "descricao": "Introdução a algoritmos - aula 1"
    },
    {
        "usuario_id": "u002",
        "disciplina_id": "d002",
        "professor_id": "p002",
        "semestre": "3º",
        "data_upload": datetime(2025, 7, 28, 14, 00),
        "url_foto": "https://exemplo.com/fotos/aula_bd.jpg",
        "descricao": "Modelo relacional - exemplos em sala"
    },
    {
        "usuario_id": "u003",
        "disciplina_id": "d003",
        "professor_id": "p003",
        "semestre": "4º",
        "data_upload": datetime(2025, 7, 29, 9, 0),
        "url_foto": "https://exemplo.com/fotos/esw_diagrama.jpg",
        "descricao": "Casos de uso - diagrama da aula"
    }
]
db.fotos.insert_many(fotos)

print("Banco de dados populado com sucesso!")
