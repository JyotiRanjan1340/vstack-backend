from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import tempfile

from utils.file_utils import save_upload_files_tmp, save_upload_file_tmp, cleanup_files
from utils.pdf_merge import merge_pdfs
from utils.pdf_edit import split_pdf, rotate_pdf, reorder_pdf, delete_pages_pdf

app = FastAPI(
    title="PDF Tools API",
    description="API for merging, editing, and processing PDFs.",
    version="1.0.0"
)

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set this to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "PDF Tools API is running"}

# PDF MERGE
@app.post("/pdf/merge", summary="Merge multiple PDFs into one")
async def api_pdf_merge(files: List[UploadFile] = File(...)):
    pdf_paths = save_upload_files_tmp(files)
    merged_fd, merged_path = tempfile.mkstemp(suffix=".pdf")
    os.close(merged_fd)
    try:
        merge_pdfs(pdf_paths, merged_path)
        return FileResponse(merged_path, filename="merged.pdf", media_type="application/pdf")
    finally:
        cleanup_files(pdf_paths + [merged_path])

# PDF SPLIT
@app.post("/pdf/split", summary="Split PDF into multiple PDFs by page ranges")
async def api_pdf_split(
    file: UploadFile = File(...),
    ranges: str = Form(...)
):
    """
    ranges: comma-separated page ranges, e.g. "1-3,4-5" (1-based, inclusive)
    """
    pdf_path = save_upload_file_tmp(file)
    # Parse page ranges
    try:
        page_ranges = []
        for r in ranges.split(","):
            start, end = map(int, r.strip().split("-"))
            # Convert to 0-based indices
            page_ranges.append((start - 1, end - 1))
    except Exception:
        cleanup_files([pdf_path])
        raise HTTPException(status_code=400, detail="Invalid ranges format")
    output_paths = [tempfile.mktemp(suffix=".pdf") for _ in page_ranges]
    try:
        split_pdf(pdf_path, page_ranges, output_paths)
        # Return as a zip file (TODO: for now just first part)
        return FileResponse(output_paths[0], filename="split_part1.pdf", media_type="application/pdf")
    finally:
        cleanup_files([pdf_path] + output_paths)

# PDF ROTATE
@app.post("/pdf/rotate", summary="Rotate all pages of a PDF")
async def api_pdf_rotate(
    file: UploadFile = File(...),
    rotation: int = Form(...)
):
    pdf_path = save_upload_file_tmp(file)
    output_path = tempfile.mktemp(suffix=".pdf")
    try:
        rotate_pdf(pdf_path, rotation, output_path)
        return FileResponse(output_path, filename="rotated.pdf", media_type="application/pdf")
    finally:
        cleanup_files([pdf_path, output_path])

# PDF REORDER
@app.post("/pdf/reorder", summary="Reorder PDF pages")
async def api_pdf_reorder(
    file: UploadFile = File(...),
    new_order: str = Form(...)
):
    """
    new_order: comma-separated page indices, e.g. "2,1,3" (1-based)
    """
    pdf_path = save_upload_file_tmp(file)
    try:
        order = [int(i) - 1 for i in new_order.split(",")]
    except Exception:
        cleanup_files([pdf_path])
        raise HTTPException(status_code=400, detail="Invalid new_order format")
    output_path = tempfile.mktemp(suffix=".pdf")
    try:
        reorder_pdf(pdf_path, order, output_path)
        return FileResponse(output_path, filename="reordered.pdf", media_type="application/pdf")
    finally:
        cleanup_files([pdf_path, output_path])

# PDF DELETE PAGES
@app.post("/pdf/delete-pages", summary="Delete specific pages from a PDF")
async def api_pdf_delete_pages(
    file: UploadFile = File(...),
    pages: str = Form(...)
):
    """
    pages: comma-separated page numbers to delete, e.g. "2,4" (1-based)
    """
    pdf_path = save_upload_file_tmp(file)
    try:
        pages_to_delete = [int(i) - 1 for i in pages.split(",")]
    except Exception:
        cleanup_files([pdf_path])
        raise HTTPException(status_code=400, detail="Invalid pages format")
    output_path = tempfile.mktemp(suffix=".pdf")
    try:
        delete_pages_pdf(pdf_path, pages_to_delete, output_path)
        return FileResponse(output_path, filename="deleted_pages.pdf", media_type="application/pdf")
    finally:
        cleanup_files([pdf_path, output_path])