from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

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
    filtro = {"disciplina_id": disciplina_id}
    sort_flag = -1 if direction == "desc" else 1
    cursor = (fotos.find(filtro)
                    .sort(order_by, sort_flag)
                    .skip(skip)
                    .limit(limit))
    return [to_dict(f) for f in cursor]

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
    return to_dict(atualizado)

@app.delete("/fotos/{foto_id}")
def delete_foto(foto_id: str):
    if fotos.delete_one({"_id": ObjectId(foto_id)}).deleted_count == 0:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    return {"ok": True}

# ---------- ANALYTICS: MULTI-STAGE AGG PIPELINES ----------

# 1) Fotos por disciplina (group + lookups + project + paginação)
@app.get("/analytics/fotos-por-disciplina", response_model=List[dict])
def fotos_por_disciplina(
    semestre: Optional[str] = Query(None, description="Ex: 1º, 2º, 3º..."),
    start: Optional[str] = Query(None, description="ISO inicial, ex: 2025-07-01T00:00:00Z"),
    end: Optional[str] = Query(None, description="ISO final, ex: 2025-08-31T23:59:59Z"),
    limit: int = 10,
    skip: int = 0,
):
    match: dict = {}
    if semestre:
        match["semestre"] = semestre

    di = _parse_iso(start)
    df = _parse_iso(end)
    if di or df:
        match["data_upload"] = {}
        if di: match["data_upload"]["$gte"] = di
        if df: match["data_upload"]["$lte"] = df

    pipeline = [
        {"$match": match if match else {}},
        {"$group": {
            "_id": {"disciplina_id": "$disciplina_id"},
            "total_fotos": {"$sum": 1},
            "ultimo_upload": {"$max": "$data_upload"}
        }},
        {"$sort": {"total_fotos": -1}},
        {"$lookup": {
            "from": "disciplinas",
            "localField": "_id.disciplina_id",
            "foreignField": "_id",
            "as": "disc"
        }},
        {"$unwind": "$disc"},
        {"$lookup": {
            "from": "professores",
            "localField": "disc.professor_id",
            "foreignField": "_id",
            "as": "prof"
        }},
        {"$unwind": "$prof"},
        {"$project": {
            "_id": 0,
            "disciplina_id": "$_id.disciplina_id",
            "disciplina": "$disc.nome",
            "semestre": "$disc.semestre",
            "professor_id": "$prof._id",
            "professor": "$prof.nome",
            "total_fotos": 1,
            "ultimo_upload": 1
        }},
        {"$skip": skip},
        {"$limit": limit},
    ]
    return list(fotos.aggregate(pipeline))

# 2) Top contribuidores (group por usuário + lookup + project + paginação)
@app.get("/analytics/top-contribuidores", response_model=List[dict])
def top_contribuidores(
    disciplina_id: Optional[str] = Query(None, description="Filtra por disciplina (ex: d001)"),
    start: Optional[str] = Query(None, description="ISO inicial"),
    end: Optional[str] = Query(None, description="ISO final"),
    limit: int = 10,
    skip: int = 0,
):
    match: dict = {}
    if disciplina_id:
        match["disciplina_id"] = disciplina_id

    di = _parse_iso(start)
    df = _parse_iso(end)
    if di or df:
        match["data_upload"] = {}
        if di: match["data_upload"]["$gte"] = di
        if df: match["data_upload"]["$lte"] = df

    pipeline = [
        {"$match": match if match else {}},
        {"$group": {
            "_id": {"usuario_id": "$usuario_id"},
            "total_fotos": {"$sum": 1},
            "ultimo_upload": {"$max": "$data_upload"}
        }},
        {"$sort": {"total_fotos": -1, "ultimo_upload": -1}},
        {"$lookup": {
            "from": "usuarios",
            "localField": "_id.usuario_id",
            "foreignField": "_id",
            "as": "user"
        }},
        {"$unwind": "$user"},
        {"$project": {
            "_id": 0,
            "usuario_id": "$_id.usuario_id",
            "usuario_nome": "$user.nome",
            "usuario_email": "$user.email",
            "total_fotos": 1,
            "ultimo_upload": 1
        }},
        {"$skip": skip},
        {"$limit": limit},
    ]
    return list(fotos.aggregate(pipeline))