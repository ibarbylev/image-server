import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
import os
import uuid
import logging
from datetime import datetime
from PIL import Image
import mimetypes
import urllib.parse

# Configuration
HOST = '0.0.0.0'
PORT = 5000
UPLOAD_FOLDER = 'images'
LOG_FILE = 'logs/app.log'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Setup logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename(filename):
    return filename.replace('..', '').replace('/', '').replace('\\', '')

class ImageServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_file('static/index.html', 'text/html')
            logging.info('Main page accessed')
        elif self.path == '/upload':
            self.serve_file('static/upload.html', 'text/html')
            logging.info('Upload page accessed')
        else:
            self.send_error(404, 'Not Found')

    def do_POST(self):
        if self.path == '/upload':
            try:
                # Parse multipart form data
                content_type = self.headers.get('content-type')
                if not content_type or 'multipart/form-data' not in content_type:
                    self.send_error_response(400, 'Invalid content type')
                    logging.error('Invalid content type')
                    return

                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST'}
                )

                if 'file' not in form:
                    self.send_error_response(400, 'No file part')
                    logging.error('No file part in request')
                    return

                file_item = form['file']
                if not file_item.filename:
                    self.send_error_response(400, 'No selected file')
                    logging.error('No selected file')
                    return

                if not allowed_file(file_item.filename):
                    self.send_error_response(400, 'Unsupported file format')
                    logging.error(f'Unsupported file format: {file_item.filename}')
                    return

                # Check file size
                file_data = file_item.file.read()
                if len(file_data) > MAX_FILE_SIZE:
                    self.send_error_response(400, 'File too large')
                    logging.error(f'File too large: {len(file_data)} bytes')
                    return

                # Generate unique filename
                ext = file_item.filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4()}.{ext}"
                filename = secure_filename(unique_filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)

                # Save file
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(file_data)

                # Verify image
                try:
                    Image.open(filepath).verify()
                except Exception:
                    os.remove(filepath)
                    self.send_error_response(400, 'Invalid image file')
                    logging.error(f'Invalid image file: {filename}')
                    return

                image_url = f"/images/{filename}"
                logging.info(f'Success: image {filename} uploaded')

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    'message': 'File uploaded successfully',
                    'filename': filename,
                    'url': image_url
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                self.send_error_response(500, f'Error saving file: {str(e)}')
                logging.error(f'Error saving file: {str(e)}')

        else:
            self.send_error(404, 'Not Found')

    def serve_file(self, filepath, content_type):
        try:
            with open(filepath, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_error(404, 'Not Found')

    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(f'{{"error": "{message}"}}'.encode())

def run():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, ImageServer)
    logging.info('Starting server...')
    httpd.serve_forever()

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    run()