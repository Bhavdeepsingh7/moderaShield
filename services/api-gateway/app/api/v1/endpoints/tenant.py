from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant_service import tenant_service

router = APIRouter()

