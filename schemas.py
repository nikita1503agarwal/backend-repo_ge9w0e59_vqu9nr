from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime

# Each model maps to a MongoDB collection with the lowercase class name.

class Certification(BaseModel):
    title: str
    issuer: str
    issued_at: datetime
    logo_url: Optional[HttpUrl] = None
    credential_id: Optional[str] = None
    credential_url: Optional[HttpUrl] = None

class Project(BaseModel):
    name: str
    slug: str
    summary: str
    marketplace_url: Optional[HttpUrl] = None
    featured: bool = False
    skills: List[str] = []
    technologies: List[str] = []
    features: List[str] = []
    screenshots: List[HttpUrl] = []

class BlogPost(BaseModel):
    title: str
    slug: str
    excerpt: str
    content: str
    published_at: datetime

class SocialLinks(BaseModel):
    linkedin: Optional[HttpUrl] = None
    github: Optional[HttpUrl] = None
    medium: Optional[HttpUrl] = None
    google_dev: Optional[HttpUrl] = None
    email: Optional[str] = None

class Resume(BaseModel):
    url: HttpUrl
    updated_at: datetime

class User(BaseModel):
    username: str
    hashed_password: str
    role: str = "admin"
