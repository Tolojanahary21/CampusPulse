import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.auth import router as auth_router
from app.api.domain import router as domain_router
from app.core.config import settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title='CampusPulse API', version='1.0.0', description='Plateforme universitaire multi-établissements. Sessions par cookie et contrôle des permissions sur chaque ressource.', lifespan=lifespan, docs_url='/docs' if settings.app_env != 'production' else None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'], allow_headers=['Content-Type', 'X-CSRF-Token'], expose_headers=['Content-Disposition'])


@app.middleware('http')
async def security_headers(request: Request, call_next):
    origin = request.headers.get('origin')
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin not in settings.cors_origins:
        return JSONResponse({'detail': 'Origine de la requête non autorisée.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    if settings.app_env == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request, error):
    return JSONResponse({'detail': 'Cette opération entre en conflit avec des données existantes ou des références invalides.'}, status_code=409)


@app.exception_handler(SQLAlchemyError)
async def database_error(request, error):
    logger.error('Database operation failed: %s', type(error).__name__)
    return JSONResponse({'detail': 'Le service de données est temporairement indisponible.'}, status_code=503)


@app.get('/health/live', tags=['Exploitation'])
def live():
    return {'status': 'ok'}


@app.get('/health', tags=['Exploitation'])
def health():
    with SessionLocal() as db:
        db.execute(text('SELECT 1'))
    return {'status': 'ok', 'service': 'campuspulse', 'version': '1.0.0'}


app.include_router(auth_router, prefix='/api/v1')
app.include_router(domain_router, prefix='/api/v1')
