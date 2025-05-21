from flask import Flask, send_file, request, render_template, abort, jsonify, session
import cv2
import io
from PIL import Image
import os
import ffmpeg
import uuid
import time
import hashlib

GIF_FOLDER = os.path.join(os.path.expanduser('~'), '.giftool2_gifs')
os.makedirs(GIF_FOLDER, exist_ok=True)

UPLOAD_FOLDER = os.path.join(os.path.expanduser('~'), '.giftool2_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'dev'  # Needed for session

def cleanup_old_uploads():
    for fname in os.listdir(UPLOAD_FOLDER):
        fpath = os.path.join(UPLOAD_FOLDER, fname)
        if os.path.isfile(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

@app.before_request
def before_request_cleanup():
    # Run cleanup on every request (lightweight for small folders)
    cleanup_old_uploads()

def get_video_path():
    return session.get('video_path')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload_video', methods=['POST'])
def upload_video():
    file = request.files.get('videoFile')
    if not file:
        abort(400, 'No file uploaded')
    filename_raw = file.filename or ''
    ext = os.path.splitext(filename_raw)[1] if '.' in filename_raw else ''
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    session['video_path'] = path
    return jsonify({'success': True, 'filename': filename})

@app.route('/frame')
def get_frame():
    video_path = get_video_path()
    if not video_path:
        abort(400, 'No video selected')
    i = int(request.args.get('i', 0))
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        abort(404, 'Video not found')
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        abort(404, 'Frame not found')
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/video_info')
def get_video_info():
    video_path = get_video_path()
    if not video_path:
        abort(400, 'No video selected')
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        abort(404, 'Video not found')
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return {'frame_count': frame_count}

@app.route('/create_gif', methods=['POST'])
def create_gif():
    video_path = get_video_path()
    if not video_path:
        abort(400, 'No video selected')
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 90))
    brightness = float(request.args.get('brightness', 1.0))
    fps = float(request.args.get('fps', 10))  # Default to 10 if not provided
    scale = request.args.get('scale', '360:-1')  # Default to 360px wide, keep aspect
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        abort(404, 'Video not found')
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if video_fps <= 0:
        abort(500, 'Invalid FPS')
    if start < 0 or start >= frame_count:
        abort(400, 'Invalid start frame')
    if length <= 0:
        abort(400, 'Invalid length')
    start_time = start / video_fps
    duration = length / video_fps
    video_hash = hashlib.sha1(video_path.encode('utf-8')).hexdigest()[:10]
    gif_filename = f'{video_hash}_{start}.gif'
    gif_path = os.path.join(GIF_FOLDER, gif_filename)
    vf_filters = f'fps={fps},scale={scale}:-1:flags=lanczos'
    if brightness != 1.0:
        vf_filters += f',eq=brightness={brightness - 1.0}'
    (
        ffmpeg
        .input(video_path, ss=start_time, t=duration)
        .output(
            gif_path,
            vf=f'{vf_filters},split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
            loop=0
        )
        .run(overwrite_output=True)
    )
    return jsonify({'path': f'/gif/{gif_filename}'})

@app.route('/gifs_list')
def gifs_list():
    files = []
    for fname in os.listdir(GIF_FOLDER):
        if fname.lower().endswith('.gif'):
            fpath = os.path.join(GIF_FOLDER, fname)
            if os.path.isfile(fpath):
                files.append(fname)
    files.sort()
    return render_template('gif_list.html', gifs=files)

@app.route('/gif/<path:filename>')
def serve_gif(filename):
    gif_path = os.path.join(GIF_FOLDER, filename)
    if not os.path.isfile(gif_path):
        abort(404, 'GIF not found')
    return send_file(gif_path, mimetype='image/gif')

@app.route('/delete_gif/<path:filename>', methods=['DELETE'])
def delete_gif(filename):
    gif_path = os.path.join(GIF_FOLDER, filename)
    if not os.path.isfile(gif_path):
        return jsonify({'error': 'File not found'}), 404
    try:
        os.remove(gif_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export_gif/<path:filename>')
def export_gif(filename):
    gif_path = os.path.join(GIF_FOLDER, filename)
    if not os.path.isfile(gif_path):
        abort(404, 'GIF not found')
    new_name = request.args.get('new_name', filename)
    # Sanitize filename
    new_name = os.path.basename(new_name)
    if not new_name.lower().endswith('.gif'):
        new_name += '.gif'
    return send_file(gif_path, as_attachment=True, download_name=new_name)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.isfile(file_path):
        abort(404, 'File not found')
    return send_file(file_path, as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True)
