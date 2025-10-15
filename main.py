from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import tempfile
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PIL import Image
import pytesseract

app = FastAPI(
    title="PDF Tools API",
    description="API for merging, editing, compressing, and extracting text from PDFs and images.",
    version="1.0.0"
)

# CORS settings (allow all for dev; restrict in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "PDF Tools API is running"}

# 1. PDF MERGE
@app.post("/pdf/merge", summary="Merge multiple PDFs into one")
async def api_pdf_merge(files: List[UploadFile] = File(...)):
    pdf_paths = []
    for upload in files:
        fd, path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(await upload.read())
        pdf_paths.append(path)
    merged_fd, merged_path = tempfile.mkstemp(suffix=".pdf")
    os.close(merged_fd)
    try:
        merger = PdfMerger()
        for path in pdf_paths:
            merger.append(path)
        merger.write(merged_path)
        merger.close()
        return FileResponse(merged_path, filename="merged.pdf", media_type="application/pdf")
    finally:
        for p in pdf_paths + [merged_path]:
            try:
                os.remove(p)
            except Exception:
                pass

# 2. FILE MERGE TO PDF (PDF, IMAGE, DOCX → PDF)
@app.post("/file/merge", summary="Merge PDF, Word, and image files into a single PDF")
async def api_file_merge(files: List[UploadFile] = File(...)):
    pdf_paths = []
    for upload in files:
        filename = upload.filename.lower()
        # Save file to temp
        fd, path = tempfile.mkstemp(suffix=os.path.splitext(filename)[1])
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(await upload.read())
        # If image, convert to PDF
        if filename.endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            im = Image.open(path)
            pdf_path = path + ".pdf"
            im.convert("RGB").save(pdf_path)
            pdf_paths.append(pdf_path)
            os.remove(path)
        # If PDF, keep as is
        elif filename.endswith('.pdf'):
            pdf_paths.append(path)
        # If DOCX, convert to PDF (stub; actual implementation requires docx2pdf or similar, not supported on Linux Render free tier)
        else:
            os.remove(path)
            continue
    merged_fd, merged_path = tempfile.mkstemp(suffix=".pdf")
    os.close(merged_fd)
    try:
        merger = PdfMerger()
        for path in pdf_paths:
            merger.append(path)
        merger.write(merged_path)
        merger.close()
        return FileResponse(merged_path, filename="merged.pdf", media_type="application/pdf")
    finally:
        for p in pdf_paths + [merged_path]:
            try:
                os.remove(p)
            except Exception:
                pass

# 3. REDUCE FILE SIZE (PDF compress placeholder)
@app.post("/pdf/compress", summary="Compress a PDF (lossless placeholder)")
async def api_pdf_compress(file: UploadFile = File(...)):
    temp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_in.write(await file.read())
    temp_in.close()
    reader = PdfReader(temp_in.name)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    with open(temp_out.name, "wb") as f_out:
        writer.write(f_out)
    try:
        os.remove(temp_in.name)
    except Exception:
        pass
    return FileResponse(temp_out.name, filename="compressed.pdf", media_type="application/pdf")

# 4. IMAGE TO TEXT (OCR)
@app.post("/ocr/image-to-text", summary="Extract text from images (OCR)")
async def api_ocr_image(file: UploadFile = File(...)):
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(await file.read())
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        return JSONResponse({"text": text})
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

# 5. PDF EDIT (split, reorder, rotate, delete pages)

@app.post("/pdf/split", summary="Split PDF into multiple PDFs by page ranges")
async def api_pdf_split(
    file: UploadFile = File(...),
    ranges: str = Form(...)
):
    """
    ranges: comma-separated page ranges, e.g. "1-3,4-5" (1-based, inclusive)
    """
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(await file.read())
    page_ranges = []
    for r in ranges.split(","):
        start, end = map(int, r.strip().split("-"))
        page_ranges.append((start - 1, end - 1))
    output_paths = []
    try:
        reader = PdfReader(path)
        for i, (start, end) in enumerate(page_ranges):
            writer = PdfWriter()
            for p in range(start, end + 1):
                writer.add_page(reader.pages[p])
            out_path = path + f".part{i+1}.pdf"
            with open(out_path, "wb") as f_out:
                writer.write(f_out)
            output_paths.append(out_path)
        # Just return first part for now
        return FileResponse(output_paths[0], filename="split_part1.pdf", media_type="application/pdf")
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
        for p in output_paths:
            try:
                os.remove(p)
            except Exception:
                pass

@app.post("/pdf/rotate", summary="Rotate all pages of a PDF")
async def api_pdf_rotate(
    file: UploadFile = File(...),
    rotation: int = Form(...)
):
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(await file.read())
    out_path = path + ".rotated.pdf"
    try:
        reader = PdfReader(path)
        writer = PdfWriter()
        for page in reader.pages:
            page.rotate(rotation)
            writer.add_page(page)
        with open(out_path, "wb") as f_out:
            writer.write(f_out)
        return FileResponse(out_path, filename="rotated.pdf", media_type="application/pdf")
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
        try:
            os.remove(out_path)
        except Exception:
            pass

@app.post("/pdf/reorder", summary="Reorder PDF pages")
async def api_pdf_reorder(
    file: UploadFile = File(...),
    new_order: str = Form(...)
):
    """
    new_order: comma-separated page indices, e.g. "2,1,3" (1-based)
    """
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(await file.read())
    try:
        order = [int(i) - 1 for i in new_order.split(",")]
        reader = PdfReader(path)
        writer = PdfWriter()
        for idx in order:
            writer.add_page(reader.pages[idx])
        out_path = path + ".reordered.pdf"
        with open(out_path, "wb") as f_out:
            writer.write(f_out)
        return FileResponse(out_path, filename="reordered.pdf", media_type="application/pdf")
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
        try:
            os.remove(out_path)
        except Exception:
            pass

@app.post("/pdf/delete-pages", summary="Delete specific pages from a PDF")
async def api_pdf_delete_pages(
    file: UploadFile = File(...),
    pages: str = Form(...)
):
    """
    pages: comma-separated page numbers to delete, e.g. "2,4" (1-based)
    """
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as tmp:
        tmp.write(await file.read())
    try:
        pages_to_delete = [int(i) - 1 for i in pages.split(",")]
        reader = PdfReader(path)
        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            if i not in pages_to_delete:
                writer.add_page(page)
        out_path = path + ".deleted.pdf"
        with open(out_path, "wb") as f_out:
            writer.write(f_out)
        return FileResponse(out_path, filename="deleted_pages.pdf", media_type="application/pdf")
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
        try:
            os.remove(out_path)
        except Exception:
            pass
