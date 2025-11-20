import io
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import pytesseract
import docx 
from pypdf import PdfReader 

app = Flask(__name__)
CORS(app)

def extract_key_points(text):
    """
    Smart extraction for Salesforce Errors, Dates, and Emails.
    """
    key_points = []
    
    # 1. Search for "Error" keywords (Specific to your PDF context)
    error_match = re.search(r'(Error Message|Error ID|Exception|GACK)[:\s]+(.*?)(?=\n|$)', text, re.IGNORECASE)
    if error_match:
        key_points.append(f"🔴 Error Detected: {error_match.group(2).strip()}")

    # 2. Find Emails
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if emails:
        key_points.append(f"📧 Emails: {', '.join(set(emails))}")

    # 3. Find Dates
    dates = re.findall(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}', text)
    if dates:
        key_points.append(f"📅 Dates: {', '.join(set(dates))}")

    # 4. Fallback Summary
    if not key_points:
        clean_text = text.replace('\n', ' ').strip()
        key_points.append(f"📝 Preview: {clean_text[:150]}...")

    return "\n\n".join(key_points)

@app.route('/ocr-upload', methods=['POST'])
def upload_file():
    print("--- Processing File ---")
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    filename = file.filename.lower()
    text_content = ""

    try:
        # 1. IMAGE PROCESSING (OCR)
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            image = Image.open(file.stream)
            text_content = pytesseract.image_to_string(image)

        # 2. PDF PROCESSING (Digital Text)
        elif filename.endswith('.pdf'):
            reader = PdfReader(file.stream)
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
            
            if not text_content.strip():
                 return jsonify({"error": "This appears to be a scanned PDF. Please convert it to an Image (PNG/JPG) first to use OCR."}), 400

        # 3. WORD DOC PROCESSING
        elif filename.endswith('.docx'):
            doc = docx.Document(file.stream)
            text_content = "\n".join([para.text for para in doc.paragraphs])

        # 4. TEXT FILE
        elif filename.endswith('.txt'):
            text_content = file.read().decode('utf-8')

        else:
            return jsonify({"error": "Unsupported file type"}), 400

        key_points = extract_key_points(text_content)

        return jsonify({
            "status": "success",
            "filename": file.filename,
            "ocr_content": text_content,
            "key_points": key_points
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
