from services.rag_services import process_pdf
import fitz
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route("/book", methods=["POST"])
def upload_book():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files allowed"}), 400

    filename = secure_filename(file.filename)

    upload_folder = current_app.config["UPLOAD_FOLDER"]

    filepath = os.path.join(upload_folder, filename)

    file.save(filepath)

    pages, index_path = process_pdf(
    filepath,
    user_id=1
)
    
    doc = fitz.open(filepath)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    pages = len(fitz.open(filepath))

    return jsonify({
    "success": True,
    "message": "Book indexed successfully",
    "filename": filename,
    "pages": pages,
    "index": index_path
}), 200

@upload_bp.route("/books", methods=["GET"])
def get_books():

    upload_folder = current_app.config["UPLOAD_FOLDER"]

    books = []

    if os.path.exists(upload_folder):

        for filename in os.listdir(upload_folder):

            if filename.lower().endswith(".pdf"):

                filepath = os.path.join(upload_folder, filename)

                try:
                    doc = fitz.open(filepath)

                    books.append({
                        "id": len(books) + 1,
                        "title": filename.replace(".pdf", ""),
                        "subject": "General",
                        "pages": len(doc),
                        "created_at": os.path.getctime(filepath)
                    })

                    doc.close()

                except Exception:
                    pass

    return jsonify(books)