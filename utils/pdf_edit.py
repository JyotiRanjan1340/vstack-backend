from PyPDF2 import PdfReader, PdfWriter

def split_pdf(pdf_path, page_ranges, output_paths):
    reader = PdfReader(pdf_path)
    for i, (start, end) in enumerate(page_ranges):
        writer = PdfWriter()
        for page_num in range(start, end + 1):
            writer.add_page(reader.pages[page_num])
        with open(output_paths[i], "wb") as out_f:
            writer.write(out_f)
    return output_paths

def rotate_pdf(pdf_path, rotation, output_path):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(rotation)
        writer.add_page(page)
    with open(output_path, "wb") as out_f:
        writer.write(out_f)
    return output_path

def reorder_pdf(pdf_path, new_order, output_path):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for idx in new_order:
        writer.add_page(reader.pages[idx])
    with open(output_path, "wb") as out_f:
        writer.write(out_f)
    return output_path

def delete_pages_pdf(pdf_path, pages_to_delete, output_path):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i not in pages_to_delete:
            writer.add_page(page)
    with open(output_path, "wb") as out_f:
        writer.write(out_f)
    return output_path