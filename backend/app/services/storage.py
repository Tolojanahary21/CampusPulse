"""Bounded private uploads, signature validation and opaque storage keys."""
import hashlib
import io
from pathlib import Path
from uuid import uuid4
import zipfile

from fastapi import HTTPException, UploadFile
from app.core.config import settings

TYPES = {
    '.pdf': 'application/pdf', '.txt': 'text/plain', '.png': 'image/png',
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
}


def file_path(key):
    root = Path(settings.storage_path).resolve()
    path = (root / key).resolve()
    if path.parent != root:
        raise HTTPException(404, 'Fichier introuvable.')
    return path


def validate_file(data, extension):
    valid = False
    if extension == '.pdf':
        valid = data.startswith(b'%PDF-') and b'%%EOF' in data[-2048:]
    elif extension == '.png':
        valid = data.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in data[-32:]
    elif extension in {'.jpg', '.jpeg'}:
        valid = data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9')
    elif extension == '.txt':
        try:
            data.decode('utf-8-sig')
            valid = b'\x00' not in data
        except UnicodeDecodeError:
            pass
    elif extension in {'.docx', '.xlsx', '.pptx'}:
        prefix = {'.docx': 'word/document.xml', '.xlsx': 'xl/workbook.xml', '.pptx': 'ppt/presentation.xml'}[extension]
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                infos = archive.infolist()
                names = archive.namelist()
                valid = '[Content_Types].xml' in names and prefix in names and len(infos) < 10000
                valid = valid and sum(info.file_size for info in infos) <= 100 * 1024 * 1024
                valid = valid and not any('vbaproject' in n.lower() or n.lower().endswith(('.exe', '.dll', '.js', '.vbs')) or '..' in n.split('/') for n in names)
        except (zipfile.BadZipFile, OSError):
            pass
    if not valid:
        raise HTTPException(422, 'Le contenu du fichier ne correspond pas à un format autorisé.')


async def save_upload(upload: UploadFile, maximum_mb: int):
    name = (upload.filename or 'document').replace('\\', '/').rsplit('/', 1)[-1]
    if not name or len(name) > 255:
        raise HTTPException(422, 'Nom de fichier invalide.')
    extension = Path(name).suffix.lower()
    if extension not in TYPES:
        raise HTTPException(422, 'Format autorisé : PDF, TXT, PNG, JPEG, DOCX, XLSX ou PPTX.')
    data = await upload.read(maximum_mb * 1024 * 1024 + 1)
    if len(data) > maximum_mb * 1024 * 1024:
        raise HTTPException(413, 'Le fichier dépasse la taille maximale autorisée.')
    if not data:
        raise HTTPException(422, 'Le fichier est vide.')
    validate_file(data, extension)
    key = f'{uuid4().hex}{extension}'
    path = file_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return dict(storage_key=key, original_filename=name, extension=extension,
                mime_type=TYPES[extension], size_bytes=len(data), sha256_hash=hashlib.sha256(data).hexdigest())


async def save_avatar(upload: UploadFile, maximum_mb: int = 5):
    """Save a small raster profile image after checking its signature."""
    name = (upload.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
    extension = Path(name).suffix.lower()
    if extension not in {'.png', '.jpg', '.jpeg'}:
        raise HTTPException(422, 'Choisissez une image PNG ou JPEG.')
    data = await upload.read(maximum_mb * 1024 * 1024 + 1)
    if not data:
        raise HTTPException(422, 'Le fichier image est vide.')
    if len(data) > maximum_mb * 1024 * 1024:
        raise HTTPException(413, 'La photo ne peut pas dépasser 5 Mo.')
    valid = (extension == '.png' and data.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in data[-32:]) or (
        extension in {'.jpg', '.jpeg'} and data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9')
    )
    if not valid:
        raise HTTPException(422, 'Le contenu ne correspond pas à une image PNG ou JPEG valide.')
    key = f'avatar-{uuid4().hex}{extension}'
    path = file_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key
