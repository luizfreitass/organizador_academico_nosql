from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from bson import ObjectId
from database import usuarios, professores, disciplinas, fotos, create_indexes
from models import *

app = FastAPI(title="Organizador Acadêmico API")

# ---------- EVENTOS ----------
@app.on_event("startup")
def startup_event():
    create_indexes()

# ---------- USUÁRIOS ----------
@app.post("/usuarios", response_model=UsuarioOut)
def create_usuario(usuario: UsuarioIn):
    res = usuarios.insert_one(usuario.dict())
    return {"id": str(res.inserted_id)}

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
    return {"id": str(res.inserted_id)}

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
    # (opcional) checar se professor existe
    if not professores.find_one({"_id": disc.professor_id}):
        raise HTTPException(404, "Professor não encontrado")
    res = disciplinas.insert_one(disc.dict())
    return {"id": str(res.inserted_id)}

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
    return {"id": str(res.inserted_id)}

# ---------- BUSCA DE FOTOS PELO ÍNDICE----------
@app.get("/fotos/search", response_model=List[FotoOut])
def search_fotos(
    disciplina_id: Optional[str] = None,
    professor_id:  Optional[str] = None,
    semestre:      Optional[str] = None,
    order_by: str = Query("data_upload", pattern="^(data_upload|semestre)$"),
    direction: str = Query("desc",       pattern="^(asc|desc)$"),
    limit: int  = 20,
    repeat: int = 1,  # executa a busca N vezes (teste de cache/perf.)
):
    filtro = {}
    if disciplina_id: filtro["disciplina_id"] = disciplina_id
    if professor_id:  filtro["professor_id"]  = professor_id
    if semestre:      filtro["semestre"]      = semestre

    sort_flag = -1 if direction == "desc" else 1

    result = None
    for _ in range(max(1, repeat)):  # repete a operação se quiser testar desempenho
        cursor = fotos.find(filtro).sort(order_by, sort_flag).limit(limit)
        result = [to_dict(f) for f in cursor]

    return result

@app.get("/fotos/{foto_id}", response_model=dict)
def get_foto(foto_id: str):
    doc = fotos.find_one({"_id": ObjectId(foto_id)})
    if not doc:
        raise HTTPException(404, "Foto não encontrada")
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
        raise HTTPException(404, "Foto não encontrada")
    return {"ok": True}

