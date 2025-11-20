# 1. Use a lightweight Python base image
FROM python:3.9-slim

# 2. Install Tesseract OCR engine (System Level)
# This installs the actual software that reads text from images
RUN apt-get update && \
    apt-get install -y tesseract-ocr && \
    apt-get clean

# 3. Set the working directory inside the server
WORKDIR /app

# 4. Copy all your local files into the server container
COPY . .

# 5. Install the Python libraries from your requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 6. Run the app using Gunicorn
# This tells the server to listen on port 10000 and serve the 'app' object from 'app.py'
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
