import os
import tempfile
import shutil
from typing import List
from fastapi import UploadFile

def save_upload_files_tmp(files: List[UploadFile]) -> List[str]:
    """Save uploaded files to temp files and return their paths."""
    filepaths = []
    for upload in files:
        _, ext = os.path.splitext(upload.filename)
        fd, path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, "wb") as tmp:
            shutil.copyfileobj(upload.file, tmp)
        filepaths.append(path)
    return filepaths

def save_upload_file_tmp(file: UploadFile) -> str:
    return save_upload_files_tmp([file])[0]

def cleanup_files(filepaths: List[str]):
    for path in filepaths:
        try:
            os.remove(path)
        except Exception:
            pass