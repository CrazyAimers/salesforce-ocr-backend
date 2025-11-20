import io
import re
import gc 
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps
import pytesseract
import docx 
from pypdf import PdfReader 

app = Flask(__name__)
CORS(app)

def optimize_image(image):
    """
    Reduces image size and color depth to prevent 
    Render Free Tier Server Memory Crashes (OOM).
    """
    # 1. Convert to Grayscale (Reduces memory usage by ~66% immediately)
    if image.mode != 'L':
        image = ImageOps.grayscale(image)
    
    # 2. Resize if the image is huge
    # We cap the width at 1024px. This is large enough for OCR
    # but small enough to fit in 512MB RAM.
    max_width = 1024
    if image.width > max_width:
        ratio = max_width / float(image.width)
        new_height = int(float(image.height) * ratio)
        image = image.resize((max_width, new_height), Image.LANCZOS)
    
    return image

def extract_key_points(text):
    """
    Extracts specific insights like Errors, Emails, and Dates.
    """
    key_points = []
    
    # 1. Search for "Error" keywords
    error_match = re.search(r'(Error Message|Error ID|Exception|GACK)[:\s]+(.*?)(?=\n|$)', text, re.IGNORECASE)
    if error_match:
        key_points.append(f"🔴 Error Detected: {error_match.group(2).strip()}")

    # 2. Find Emails
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if emails:
        unique_emails = list(set(emails))
        key_points.append(f"📧 Emails: {', '.join(unique_emails)}")

    # 3. Find Dates
    dates = re.findall(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}', text)
    if dates:
        unique_dates = list(set(dates))
        key_points.append(f"📅 Dates: {', '.join(unique_dates)}")

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
        # 1. IMAGE PROCESSING (Optimized for Low RAM)
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            image = Image.open(file.stream)
            
            # OPTIMIZE: Resize & Grayscale before OCR
            image = optimize_image(image)
            
            text_content = pytesseract.image_to_string(image)
            
            # Free memory immediately
            del image
            gc.collect()

        # 2. PDF PROCESSING
        elif filename.endswith('.pdf'):
            reader = PdfReader(file.stream)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
            
            if not text_content.strip():
                 return jsonify({"error": "Scanned PDF detected. Convert to JPG."}), 400

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
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
