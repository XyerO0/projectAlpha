from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from ai_detector import analyze_document_with_ai

import os

from database import init_database, save_verification, get_history

import uuid

from utils import process_document, calculate_combined_risk, get_combined_risk_level


app = Flask(__name__)
init_database()
# =========================================================
# CONFIGURATION
# =========================================================

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


# =========================================================
# FILE VALIDATION
# =========================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_uploaded_file(file):

    original_filename = secure_filename(file.filename)

    extension = original_filename.rsplit(".", 1)[1].lower()

    filename = str(uuid.uuid4()) + "." + extension

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(filepath)

    return filepath, filename


def delete_file(filepath):

    try:

        if os.path.exists(filepath):

            os.remove(filepath)

    except OSError as e:

        print(f"Could not delete file: {e}")


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# WEB VERIFICATION
# =========================================================

@app.route("/verify", methods=["GET", "POST"])
def verify():

    if request.method == "GET":

        return render_template("verify.html")


    # -----------------------------------------
    # Get form data
    # -----------------------------------------

    docType = request.form.get("documentType")

    name = request.form.get("name")

    document = request.form.get("document")


    # -----------------------------------------
    # Validate document type
    # -----------------------------------------

    if docType not in ["pan", "aadhaar", "visa"]:

        return render_template(
            "verify.html",
            error="Invalid document type"
        )


    # -----------------------------------------
    # Validate name
    # -----------------------------------------

    if not name or not name.strip():

        return render_template(
            "verify.html",
            error="Name is required"
        )


    # -----------------------------------------
    # Validate document number
    # -----------------------------------------

    if not document or not document.strip():

        return render_template(
            "verify.html",
            error="Document number is required"
        )


    # -----------------------------------------
    # Get file
    # -----------------------------------------

    file = request.files.get("documentFile")

    if not file:

        return render_template(
            "verify.html",
            error="No file uploaded"
        )

    if file.filename == "":

        return render_template(
            "verify.html",
            error="No file selected"
        )


    # -----------------------------------------
    # Validate extension
    # -----------------------------------------

    if not allowed_file(file.filename):

        return render_template(
            "verify.html",
            error="Invalid file type"
        )


    # -----------------------------------------
    # Save file
    # -----------------------------------------

    filepath, filename = save_uploaded_file(file)


    try:

        # -----------------------------------------
        # Process document
        # -----------------------------------------

        result = process_document(
            docType,
            name,
            document,
            filepath
        )


        # -----------------------------------------
        # Processing error
        # -----------------------------------------

        if not result["success"]:

            return render_template(
                "verify.html",
                error=result["error"]
            )


        # -----------------------------------------
        # AI visual analysis
        # -----------------------------------------

        try:

            ai_result = analyze_document_with_ai(
                filepath,
                docType
            )

        except Exception as e:

            print("AI analysis error:", e)

            ai_result = {
                "Status": "unavailable",
                "suspicious": None,
                "confidence": 0,
                "risk_score": 0,
                "reasons": [
                    "AI analysis was unavailable"
                ]
            }


        # -----------------------------------------
        # Display result
        # -----------------------------------------

        return render_template(
            "verify.html",

            docType=docType,

            name=name,

            document=document,

            filename=filename,

            extracted_document=result["document"]["detected_number"],

            document_status=result["document"]["number_match"],

            name_similarity=result["identity"]["name_similarity"],

            document_format_valid=result["document"]["format_valid"],

            risk_score=result["risk"]["score"],

            risk_level=result["risk"]["level"],

            ai_analysis=ai_result,

            status="Analysis Complete"
        )

    finally:

        # -----------------------------------------
        # Delete uploaded file
        # -----------------------------------------

        delete_file(filepath)


# =========================================================
# API VERIFICATION
# =========================================================

@app.route("/api/verify", methods=["POST"])
def api_verify():


    # -----------------------------------------
    # Get form data
    # -----------------------------------------

    docType = request.form.get("documentType")

    name = request.form.get("name")

    document = request.form.get("document")


    # -----------------------------------------
    # Validate document type
    # -----------------------------------------

    if docType not in ["pan", "aadhaar", "visa"]:

        return {
            "success": False,
            "error": "Invalid document type"
        }, 400


    # -----------------------------------------
    # Validate name
    # -----------------------------------------

    if not name or not name.strip():

        return {
            "success": False,
            "error": "Name is required"
        }, 400


    # -----------------------------------------
    # Validate document number
    # -----------------------------------------

    if not document or not document.strip():

        return {
            "success": False,
            "error": "Document number is required"
        }, 400


    # -----------------------------------------
    # Get file
    # -----------------------------------------

    file = request.files.get("documentFile")

    if not file:

        return {
            "success": False,
            "error": "No file uploaded"
        }, 400

    if file.filename == "":

        return {
            "success": False,
            "error": "No file selected"
        }, 400


    # -----------------------------------------
    # Validate extension
    # -----------------------------------------

    if not allowed_file(file.filename):

        return {
            "success": False,
            "error": "Invalid file type"
        }, 400


    # -----------------------------------------
    # Save file
    # -----------------------------------------

    filepath, filename = save_uploaded_file(file)


    try:

        # -----------------------------------------
        # Process document
        # -----------------------------------------

        result = process_document(
            docType,
            name,
            document,
            filepath
        )


        # -----------------------------------------
        # Processing error
        # -----------------------------------------

        if not result["success"]:

            return result, 400


        # -----------------------------------------
        # AI visual analysis
        # -----------------------------------------

        try:

            ai_result = analyze_document_with_ai(
                filepath,
                docType
            )

        except Exception as e:

            print("AI analysis error:", e)

            ai_result = {
                "Status": "unavailable",
                "suspicious": None,
                "confidence": 0,
                "risk_score": 0,
                "reasons": [
                    "AI analysis was unavailable"
                ]
            }


        # -----------------------------------------
        # Add AI result to existing result
        # -----------------------------------------

        result["ai_analysis"] = {

            "suspicious": ai_result["suspicious"],

            "confidence": ai_result["confidence"],

            "risk_score": ai_result["risk_score"],

            "reasons": ai_result["reasons"]
        }

        rule_risk = result["risk"]["score"]

        if ai_result.get("status") == "available":
            ai_risk = ai_result["risk_score"]

            combined_risk = calculate_combined_risk(
                rule_risk,
                ai_risk
            )

            final_risk = {
                "score": combined_risk,
                "level": get_combined_risk_level(combined_risk),
                "ai_included": True
            }

        else:
            final_risk = {
                "score": rule_risk,
                "level": result["risk"]["level"],
                "ai_included": False
            }

        result["final_risk"] = final_risk
        # -----------------------------------------
        # Save verification history
        # -----------------------------------------
        try:
            history_data = {
                "document_type": docType,
                "entered_name": name,

                "entered_document_number": mask_document_number(
                    result["document"]["entered_number"],
                    docType
                ),

                "detected_document_number": mask_document_number(
                    result["document"]["detected_number"],
                    docType
                ),

                "document_status": (
                    "Match"
                    if result["document"]["number_match"]
                    else "Mismatch"
                ),

                "name_similarity": result["identity"]["name_similarity"],

                "format_valid": result["document"]["format_valid"],

                "rule_risk_score": result["risk"]["score"],
                "rule_risk_level": result["risk"]["level"],

                "ai_status": (
                    "available"
                    if ai_result.get("status") == "available"
                    else "unavailable"
                ),

                "ai_suspicious": ai_result.get("suspicious"),
                "ai_confidence": ai_result.get("confidence"),
                "ai_risk_score": ai_result.get("risk_score"),
                "ai_reasons": ", ".join(ai_result.get("reasons", [])),

                "final_risk_score": final_risk["score"],
                "final_risk_level": final_risk["level"]
            }
            save_verification(history_data)

        except Exception as e:
            print("Database save error:", e)
        # -----------------------------------------
        # Return final result
        # -----------------------------------------

        return result, 200


    finally:

        # -----------------------------------------
        # Delete uploaded file
        # -----------------------------------------

        delete_file(filepath)

@app.route("/api/history", methods=["GET"])
def api_history():
    try:
        history = get_history(limit=20)

        safe_history = []

        for record in history:
            safe_history.append({
                "id": record["id"],
                "document_type": record["document_type"],
                "masked_document_number": record["detected_document_number"],
                "risk_level": record["final_risk_level"],
                "final_risk_score": record["final_risk_score"],
                "created_at": record["created_at"]
            })

        return {
            "success": True,
            "history": safe_history
        }, 200

    except Exception as e:
        print("Database history error:", e)

        return {
            "success": False,
            "error": "Could not retrieve verification history"
        }, 500
    
def mask_document_number(document_number, document_type):
    """Return a privacy-safe masked document number."""

    if not document_number:
        return None

    value = str(document_number).replace(" ", "").strip()

    if document_type == "aadhaar":
        # Aadhaar: show only last 4 digits
        return "XXXX XXXX " + value[-4:]

    if document_type == "pan":
        # PAN: show only last 4 characters
        return "XXXXX" + value[-4:]

    if document_type == "visa":
        # Visa: show only last 4 characters
        return "XXXX" + value[-4:]

    return "XXXX" + value[-4:]

# =========================================================
# HEALTH-CHECK
# =========================================================

@app.route("/api/health", methods=["GET"])
def health():

    return {
        "success": True,
        "status": "Backend is running"
    }, 200


# =========================================================
# FILE TOO LARGE
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    return {
        "success": False,
        "error": "File is too large. Maximum size is 5 MB."
    }, 413


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)

