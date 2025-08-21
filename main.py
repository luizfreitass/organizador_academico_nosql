from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

import os, json
import redis
from dotenv import load_dotenv

load_dotenv()

r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
                         decode_responses=True)
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "300"))

def cache_get_json(key: str):
    v = r.get(key)
    return json.loads(v) if v else None

def cache_set_json(key: str, value, ttl: int = CACHE_TTL):
    # default=str resolve datetime para string ISO
    r.set(key, json.dumps(value, default=str), ex=ttl)

def cache_invalidate_prefix(prefix: str):
    for k in r.scan_iter(match=f"{prefix}*"):
        r.delete(k)

from database import usuarios, professores, disciplinas, fotos, create_indexes
from models import (
    UsuarioIn, ProfessorIn, DisciplinaIn, FotoIn,
    UsuarioOut, ProfessorOut, DisciplinaOut, FotoOut,
    to_dict
)

app = FastAPI(title="Organizador Acadêmico API")

# ---------- EVENTOS ----------
@app.on_event("startup")
def startup_event():
    create_indexes()

# ---------- HELPERS ----------
def _parse_iso(dt: Optional[str]) -> Optional[datetime]:
    if not dt:
        return None
    # aceita final 'Z'
    return datetime.fromisoformat(dt.replace("Z", "+00:00"))

# ---------- USUÁRIOS ----------
@app.post("/usuarios", response_model=UsuarioOut)
def create_usuario(usuario: UsuarioIn):
    res = usuarios.insert_one(usuario.dict())
    doc = usuarios.find_one({"_id": res.inserted_id})
    return to_dict(doc)

@app.get("/usuarios", response_model=List[UsuarioOut])
def list_usuarios():
    return [to_dict(u) for u in usuarios.find()]

@app.put("/usuarios/{usuario_id}", response_model=UsuarioOut)
def update_usuario(usuario_id: str, dados: UsuarioIn):
    atualizado = usuarios.find_one_and_update(
        {"_id": ObjectId(usuario_id)},
        {"$set": dados.dict()},
        return_document=True
    )
    if not atualizado:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return to_dict(atualizado)

# ---------- PROFESSORES ----------
@app.post("/professores", response_model=ProfessorOut)
def create_professor(prof: ProfessorIn):
    res = professores.insert_one(prof.dict())
    doc = professores.find_one({"_id": res.inserted_id})
    return to_dict(doc)

@app.get("/professores", response_model=List[ProfessorOut])
def list_professores():
    return [to_dict(p) for p in professores.find()]

@app.put("/professores/{professor_id}", response_model=ProfessorOut)
def update_professor(professor_id: str, dados: ProfessorIn):
    atualizado = professores.find_one_and_update(
        {"_id": ObjectId(professor_id)},
        {"$set": dados.dict()},
        return_document=True
    )
    if not atualizado:
        raise HTTPException(status_code=404, detail="Professor não encontrado")
    return to_dict(atualizado)

# ---------- DISCIPLINAS ----------
@app.post("/disciplinas", response_model=DisciplinaOut)
def create_disciplina(disc: DisciplinaIn):
    # opcional: checar existência do professor
    if not professores.find_one({"_id": disc.professor_id}):
        raise HTTPException(status_code=404, detail="Professor não encontrado")
    res = disciplinas.insert_one(disc.dict())
    doc = disciplinas.find_one({"_id": res.inserted_id})
    return to_dict(doc)

@app.get("/disciplinas", response_model=List[DisciplinaOut])
def list_disciplinas():
    return [to_dict(d) for d in disciplinas.find()]

@app.put("/disciplinas/{disciplina_id}", response_model=DisciplinaOut)
def update_disciplina(disciplina_id: str, dados: DisciplinaIn):
    atualizado = disciplinas.find_one_and_update(
        {"_id": ObjectId(disciplina_id)},
        {"$set": dados.dict()},
        return_document=True
    )
    if not atualizado:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada")
    return to_dict(atualizado)

# ---------- FOTOS ----------
@app.post("/fotos", response_model=FotoOut)
def upload_foto(foto: FotoIn):
    res = fotos.insert_one(foto.dict())
    doc = fotos.find_one({"_id": res.inserted_id})
    # invalida caches que dependem de fotos
    cache_invalidate_prefix("fotos:search:")
    cache_invalidate_prefix("analytics:fpd:")   # fotos-por-disciplina
    cache_invalidate_prefix("analytics:top:")   # top-contribuidores
    return to_dict(doc)

# ---- BUSCA (usa índices) - manter ANTES de /fotos/{foto_id} ----
@app.get("/fotos/search", response_model=List[FotoOut])
def search_fotos(
    disciplina_id: str = Query(..., description="ID da disciplina (obrigatório)"),
    order_by: str = Query("data_upload", pattern="^(data_upload)$"),
    direction: str = Query("desc", pattern="^(asc|desc)$"),
    skip: int = 0,
    limit: int = 20,
):
    sort_flag = -1 if direction == "desc" else 1
    cache_key = f"fotos:search:disc={disciplina_id}|ob={order_by}|dir={direction}|sk={skip}|lim={limit}"

    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    cursor = (fotos.find({"disciplina_id": disciplina_id})
                  .sort(order_by, sort_flag)
                  .skip(skip)
                  .limit(limit))
    result = [to_dict(f) for f in cursor]

    cache_set_json(cache_key, result)
    return result

@app.get("/fotos/{foto_id}", response_model=FotoOut)
def get_foto(foto_id: str):
    doc = fotos.find_one({"_id": ObjectId(foto_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    return to_dict(doc)

@app.put("/fotos/{foto_id}", response_model=FotoOut)
def update_foto(foto_id: str, dados: FotoIn):
    atualizado = fotos.find_one_and_update(
        {"_id": ObjectId(foto_id)},
        {"$set": dados.dict()},
        return_document=True
    )
    if not atualizado:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    cache_invalidate_prefix("fotos:search:")
    cache_invalidate_prefix("analytics:fpd:")
    cache_invalidate_prefix("analytics:top:")
    return to_dict(atualizado)

@app.delete("/fotos/{foto_id}")
def delete_foto(foto_id: str):
    if fotos.delete_one({"_id": ObjectId(foto_id)}).deleted_count == 0:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    cache_invalidate_prefix("fotos:search:")
    cache_invalidate_prefix("analytics:fpd:")
    cache_invalidate_prefix("analytics:top:")
    return {"ok": True}

# ---------- ANALYTICS: MULTI-STAGE AGG PIPELINES ----------

# 1) Fotos por disciplina (group + lookups + project + paginação)
@app.get("/analytics/fotos-por-disciplina")
def fotos_por_disciplina(
    semestre: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 10,
    skip: int = 0,
):
    cache_key = f"analytics:fpd:sem={semestre}|st={start}|en={end}|lim={limit}|sk={skip}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        # 🚩 indica que a resposta veio do cache
        return {"from_cache": True, "data": cached}

    # monta filtro
    match_stage = {}
    if semestre:
        match_stage["semestre"] = semestre
    if start or end:
        match_stage["data_upload"] = {}
        if start:
            match_stage["data_upload"]["$gte"] = datetime.fromisoformat(start.replace("Z",""))
        if end:
            match_stage["data_upload"]["$lte"] = datetime.fromisoformat(end.replace("Z",""))

    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
        {"$group": {
            "_id": {"disciplina_id": "$disciplina_id", "professor_id": "$professor_id", "semestre": "$semestre"},
            "total_fotos": {"$sum": 1},
            "ultimo_upload": {"$max": "$data_upload"}
        }},
        {"$sort": {"total_fotos": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$lookup": {"from": "disciplinas", "localField": "_id.disciplina_id", "foreignField": "_id", "as": "disc"}},
        {"$unwind": "$disc"},
        {"$lookup": {"from": "professores", "localField": "_id.professor_id", "foreignField": "_id", "as": "prof"}},
        {"$unwind": "$prof"},
        {"$project": {
            "_id": 0,
            "disciplina_id": "$_id.disciplina_id",
            "disciplina": "$disc.nome",
            "semestre": "$_id.semestre",
            "professor_id": "$_id.professor_id",
            "professor": "$prof.nome",
            "total_fotos": 1,
            "ultimo_upload": 1
        }}
    ]

    result = list(fotos.aggregate(pipeline))
    cache_set_json(cache_key, result, ttl=60)  # TTL de 60s
    return {"from_cache": False, "data": result}


@app.get("/analytics/top-contribuidores")
def top_contribuidores(limit: int = 5):
    cache_key = f"analytics:tc:lim={limit}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return {"from_cache": True, "data": cached}

    pipeline = [
        {"$group": {"_id": "$usuario_id", "total_fotos": {"$sum": 1}}},
        {"$sort": {"total_fotos": -1}},
        {"$limit": limit},
        {"$lookup": {"from": "usuarios", "localField": "_id", "foreignField": "_id", "as": "usr"}},
        {"$unwind": "$usr"},
        {"$project": {
            "_id": 0,
            "usuario_id": "$_id",
            "usuario": "$usr.nome",
            "total_fotos": 1
        }}
    ]

    result = list(fotos.aggregate(pipeline))
    cache_set_json(cache_key, result, ttl=60)
    return {"from_cache": False, "data": result}
