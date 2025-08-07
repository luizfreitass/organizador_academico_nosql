from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional

# ----- MODELOS ENTRADA/SAÍDA ----------
class UsuarioIn(BaseModel):
    nome: str
    email: EmailStr

class ProfessorIn(BaseModel):
    nome: str

class DisciplinaIn(BaseModel):
    nome: str
    semestre: str
    professor_id: str

class FotoIn(BaseModel):
    usuario_id: str
    disciplina_id: str
    professor_id: str
    semestre: str
    url_foto: str
    descricao: Optional[str] = ""
    data_upload: datetime = Field(default_factory=datetime.utcnow)

# ---------- MODELOS DE SAÍDA ----------

class UsuarioOut(BaseModel):
    id: str = Field(..., alias="_id")
    nome: str
    email: EmailStr

    class Config:
        allow_population_by_field_name = True

class ProfessorOut(BaseModel):
    id: str = Field(..., alias="_id")
    nome: str

    class Config:
        allow_population_by_field_name = True

class DisciplinaOut(BaseModel):
    id: str = Field(..., alias="_id")
    nome: str
    semestre: str
    professor_id: str

    class Config:
        allow_population_by_field_name = True

class FotoOut(BaseModel):
    id: str = Field(..., alias="_id")
    usuario_id: str
    disciplina_id: str
    professor_id: str
    semestre: str
    url_foto: str
    descricao: Optional[str] = ""
    data_upload: datetime

    class Config:
        allow_population_by_field_name = True

# Modelo de saída genérico que inclui o _id convertido p/ string
def to_dict(doc):
    doc["_id"] = str(doc["_id"])
    return doc
