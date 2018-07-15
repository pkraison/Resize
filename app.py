#!/usr/bin/python2.7
import os
# We'll render HTML templates and access data sent by POST
# using the request object from flask. Redirect and url_for
# will be used to redirect the user once the upload is done
# and send_from_directory will help us to send/show on the
# browser the file that the user just uploaded
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, make_response
from werkzeug import secure_filename
import logging
from PIL import Image

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

# Size limit of uploads folder in KB
UPLOAD_FOLDER_LIMIT = 200 * 1024 # 200MB
DOWNLOAD_FOLDER_LIMIT = 200 * 1024 # 200MB
UPLOAD_FILE_LIMIT = 20 * 1024 # 20MB

# Cookies
session = {'filename': '', 'params': {}, 'filename_resized': ''}

# Initialize the Flask application
app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)
# This is the path to the upload directory
app.config['UPLOAD_FOLDER'] = os.path.join(THIS_FOLDER, 'uploads/')
app.config['DOWNLOAD_FOLDER'] = os.path.join(THIS_FOLDER, 'downloads/')
# Create upload_folder and download_folder if not exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['DOWNLOAD_FOLDER']):
    os.makedirs(app.config['DOWNLOAD_FOLDER'])

# These are the extension that we are accepting to be uploaded
app.config['ALLOWED_EXTENSIONS'] = set(['png', 'jpg', 'jpeg','bmp','gif','svg',])
# Cache related to prevent cache problems
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300
# Limit the upload file size
app.config['MAX_CONTENT_LENGTH'] = UPLOAD_FILE_LIMIT * 1024 # Need to be in bytes

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return ('.' in filename) and ((filename.rsplit('.', 1)[1]).lower() in app.config['ALLOWED_EXTENSIONS'])

def resizer_defined(img, width = None, height = None):
    res = img.resize((width, height), Image.ANTIALIAS)
    return res

# Calculate the total size of all files in a directory
def size_calculate(directory_path):
    size_total = 0
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        size_total += os.path.getsize(file_path)
    # Turn byte to KB
    size_total = size_total/1024
    return size_total

# Clean up all the files in a directory
def directory_cleanup(directory_path):
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)
    return

# This route will show a form to perform an AJAX request
# jQuery is loaded to execute the request and update the
# value of the operation
@app.route('/')
def index():
    return render_template('index.html')

# Route that will process the file upload
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Calculate the total size of upload folder and download folder
    # Cleanup the folders if the size exceeds the limits
    upload_folder_size = size_calculate(app.config['UPLOAD_FOLDER'])
    download_folder_size = size_calculate(app.config['DOWNLOAD_FOLDER'])
    if upload_folder_size > UPLOAD_FOLDER_LIMIT:
        directory_cleanup(app.config['UPLOAD_FOLDER'])
    if download_folder_size > DOWNLOAD_FOLDER_LIMIT:
        directory_cleanup(app.config['DOWNLOAD_FOLDER'])

    if request.method == 'POST':
        # Get the name of the uploaded file
        file = request.files['file']
        # Check if the file is one of the allowed types/extensions
        if file and allowed_file(file.filename):
            # Make the filename safe, remove unsupported chars
            filename = secure_filename(file.filename)
            # Move the file form the temporal folder to the upload folder we setup
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # Get the size user requested
            width = request.form['width']
            height = request.form['height']
            # User-defined parameter dictionary
            params = {'width': width, 'height': height}
            
            # Save parameters to cookies
            session['filename'] = filename
            session['params'] = params
            
            # Redirect the user to the resize_image route
            return redirect(url_for('resize_image'))
# This route is expecting a parameter containing the name
# of a file. Then it will locate that file on the upload
# directory and show it on the browser, so if the user uploads
# an image, that image is going to be show after the upload
@app.route('/resize')
def resize_image():
    filename = session['filename']
    params = session['params']

    # Read image
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = Image.open(file_path)
    width = int(params['width'])
    height = int(params['height'])
    res = resizer_defined(img, width = width, height = height)

    # Save resized image
    filename_resized_prefix = filename.rsplit('.', 1)[0]
    #ext = os.path.splitext(filename)[1][1:].strip().lower()
    #if ext in app.config['ALLOWED_EXTENSIONS']:
    filename_resized = filename_resized_prefix + 'resized_.jpeg'
    session['filename_resized'] = filename_resized

    dst_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename_resized)

    # Save resized image
    res.save(dst_path)

    # Original image file size in byte
    filesize_original = os.path.getsize(file_path)
    # Turn byte to KB
    filesize_original = int(filesize_original/1024)

    # Resized image file size in byte
    filesize_resized = os.path.getsize(dst_path)
    # Turn byte to KB
    filesize_resized = int(filesize_resized/1024)

    return render_template('download.html', filesize_original = filesize_original, filesize_resized = filesize_resized)

@app.route('/download', methods=['GET', 'POST'])
def download():
    filename_resized = session['filename_resized']
    if request.method == 'GET':
        return send_from_directory(directory = app.config['DOWNLOAD_FOLDER'], filename = filename_resized)

@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r
if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get('PORT', 33507))
    app.run(host="0.0.0.0", port=port)
