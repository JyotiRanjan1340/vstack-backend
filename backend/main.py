from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Backend API is running"}

@app.post("/pdf/merge")
async def merge_pdfs(files: list[UploadFile] = File(...)):
    # Save uploaded files temporarily
    filenames = []
    for file in files:
        out_path = f"temp_{file.filename}"
        with open(out_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        filenames.append(out_path)
    # Merge PDFs using PyPDF2
    from PyPDF2 import PdfMerger
    merger = PdfMerger()
    for fname in filenames:
        merger.append(fname)
    output_file = "merged.pdf"
    merger.write(output_file)
    merger.close()
    # Cleanup temp files
    for fname in filenames:
        os.remove(fname)
    return FileResponse(output_file, media_type="application/pdf", filename="merged.pdf")