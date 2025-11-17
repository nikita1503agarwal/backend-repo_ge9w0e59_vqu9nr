from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import db, create_document, get_documents
from schemas import Certification, Project, BlogPost, SocialLinks, Resume, User
import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

app = FastAPI(title="Developer Portfolio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Token(BaseModel):
    access_token: str
    token_type: str

# Utility functions

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # simple lookup by username
    user_doc = db["user"].find_one({"username": username})
    if not user_doc:
        raise credentials_exception
    return User(**{k: user_doc[k] for k in ["username", "hashed_password", "role"]})

# Public endpoints

@app.get("/")
def root():
    status_info = {
        "message": "Portfolio API running",
        "backend": "fastapi",
        "database": "mongodb" if db is not None else "unavailable",
        "collections": sorted(db.list_collection_names()) if db is not None else [],
    }
    return status_info

@app.get("/test")
def test():
    return {
        "backend": "fastapi",
        "database": "mongodb" if db is not None else "unavailable",
        "database_url": os.getenv("DATABASE_URL", "not-set"),
        "database_name": os.getenv("DATABASE_NAME", "not-set"),
        "connection_status": "ok" if db is not None else "not connected",
        "collections": sorted(db.list_collection_names()) if db is not None else [],
    }

# Portfolio content - public fetch
@app.get("/certifications", response_model=List[Certification])
def list_certifications():
    docs = get_documents("certification")
    return [Certification(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]

@app.get("/projects", response_model=List[Project])
def list_projects(featured: Optional[bool] = None):
    q = {}
    if featured is not None:
        q["featured"] = featured
    docs = get_documents("project", q)
    return [Project(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]

@app.get("/blog", response_model=List[BlogPost])
def list_blog():
    docs = get_documents("blogpost")
    return [BlogPost(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]

@app.get("/social", response_model=SocialLinks)
def get_social():
    doc = db["sociallinks"].find_one() or {}
    if "_id" in doc:
        del doc["_id"]
    return SocialLinks(**doc) if doc else SocialLinks()

@app.get("/resume", response_model=Resume)
def get_resume():
    doc = db["resume"].find_one()
    if not doc:
        raise HTTPException(404, "Resume not found")
    return Resume(**{k: v for k, v in doc.items() if k != "_id"})

# Auth endpoints
@app.post("/auth/register")
def register(user: User):
    if db["user"].find_one({"username": user.username}):
        raise HTTPException(400, "Username already exists")
    hashed = get_password_hash(user.hashed_password)
    user_dict = {"username": user.username, "hashed_password": hashed, "role": user.role}
    create_document("user", user_dict)
    return {"message": "registered"}

@app.post("/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_doc = db["user"].find_one({"username": form_data.username})
    if not user_doc or not verify_password(form_data.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Admin-protected content management
@app.post("/admin/certifications", response_model=str)
def add_cert(cert: Certification, user: User = Depends(get_current_user)):
    return create_document("certification", cert)

@app.post("/admin/projects", response_model=str)
def add_project(project: Project, user: User = Depends(get_current_user)):
    return create_document("project", project)

@app.post("/admin/blog", response_model=str)
def add_blog(post: BlogPost, user: User = Depends(get_current_user)):
    return create_document("blogpost", post)

@app.post("/admin/social", response_model=str)
def set_social(links: SocialLinks, user: User = Depends(get_current_user)):
    db["sociallinks"].delete_many({})
    return create_document("sociallinks", links)

@app.post("/admin/resume", response_model=str)
def set_resume(resume: Resume, user: User = Depends(get_current_user)):
    db["resume"].delete_many({})
    return create_document("resume", resume)
