from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
import logging
from datetime import datetime
from PIL import Image
import mimetypes

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/images'
LOG_FILE = '/logs/app.log'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Setup logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    logging.info('Main page accessed')
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        return render_template('upload.html')

    if 'file' not in request.files:
        logging.error('No file part in request')
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        logging.error('No selected file')
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        if file_size > MAX_FILE_SIZE:
            logging.error(f'File too large: {file_size} bytes')
            return jsonify({'error': 'File too large'}), 400

        # Reset file pointer
        file.seek(0)

        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{ext}"
        filename = secure_filename(unique_filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            # Save file
            file.save(filepath)

            # Verify image format using Pillow
            try:
                Image.open(filepath).verify()
            except Exception:
                os.remove(filepath)
                logging.error(f'Invalid image file: {filename}')
                return jsonify({'error': 'Invalid image file'}), 400

            image_url = f"/images/{filename}"
            logging.info(f'Success: image {filename} uploaded')
            return jsonify({
                'message': 'File uploaded successfully',
                'filename': filename,
                'url': image_url
            }), 200

        except Exception as e:
            logging.error(f'Error saving file: {str(e)}')
            return jsonify({'error': 'Error saving file'}), 500

    logging.error(f'Unsupported file format: {file.filename}')
    return jsonify({'error': 'Unsupported file format'}), 400


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000)