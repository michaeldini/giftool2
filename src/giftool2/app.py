from flask import Flask, send_file, request, render_template_string, abort, jsonify, session
import cv2
import io
from PIL import Image
import os
import ffmpeg
import uuid
import time

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CLEANUP_MAX_AGE = 60 * 60 * 6  # 6 hours in seconds

def cleanup_old_uploads():
    now = time.time()
    for fname in os.listdir(UPLOAD_FOLDER):
        fpath = os.path.join(UPLOAD_FOLDER, fname)
        if os.path.isfile(fpath):
            try:
                if now - os.path.getmtime(fpath) > CLEANUP_MAX_AGE:
                    os.remove(fpath)
            except Exception:
                pass

app = Flask(__name__, static_folder='static')
app.secret_key = 'dev'  # Needed for session

@app.before_request
def before_request_cleanup():
    # Run cleanup on every request (lightweight for small folders)
    cleanup_old_uploads()

def get_video_path():
    return session.get('video_path')

@app.route('/', methods=['GET'])
def index():
    # Minimal HTML/JS for frame navigation
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <style>
    body {
    font-family: Arial, sans-serif;
    background: #181a1b;
    color: #e0e0e0;
    margin: 0;
    padding: 30px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
}

.main-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    /* max-width: 700px; */
}

h2 {
    margin-top: 0;
    color: #fff;
}

.button-row {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 4px;
    justify-content: center;
    margin: 10px 0 0 0;
}

.range-row {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    margin: 16px 0 0 0;
}

.gif-row {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    margin: 18px 0 0 0;
    gap: 40px;
}

button {
    margin: 2px 2px;
    padding: 6px 14px;
    font-size: 1em;
    border-radius: 4px;
    border: 1px solid #444;
    background: #23272a;
    color: #e0e0e0;
    cursor: pointer;
    transition: background 0.2s, color 0.2s;
}

button:hover {
    background: #444950;
    color: #fff;
}

input[type="number"],
input[type="range"] {
    margin: 0 4px;
    font-size: 1em;
    border-radius: 3px;
    border: 1px solid #333;
    padding: 2px 6px;
    background: #23272a;
    color: #e0e0e0;
}

#frame,
#startFrameImg,
#endFrameImg {
    border: 1px solid #444;
    background: #23272a;
    margin-bottom: 8px;
}

#gifStatus {
    display: inline-block;
    min-width: 120px;
    margin-left: 10px;
    color: #b3e283;
}

#frameLabel,
#frameCountLabel {
    font-weight: bold;
    margin-left: 8px;
    color: #b3e283;
}
    </style>
    <head>
        <title>Video Frame Viewer</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <form id="uploadForm" method="post" enctype="multipart/form-data" action="/upload_video" style="margin-bottom:20px;">
            <label for="videoFile">Upload video file:</label>
            <input type="file" id="videoFile" name="videoFile" accept="video/*" required />
            <button type="submit">Upload Video</button>
        </form>
        <div class="main-container">
            <h2>Video Frame Viewer</h2>
            <img id="frame" width="480" style="display:block;" />
            <div class="button-row">
                <button onclick="seek(-5)">-5</button>
                <input type="number" id="frameInput" value="0" step="1" min="0" style="width:60px;" onchange="setFrame()" />
                <button onclick="seek(5)">+5</button>
                <button onclick="seek(10)">+10</button>
                <button onclick="seek(20)">+20</button>
                <button onclick="seek(40)">+40</button>
                <button onclick="seek(80)">+80</button>
                <button onclick="seek(160)">+160</button>
                <button onclick="seek(320)">+320</button>
                <button onclick="seek(640)">+640</button>
                <span id="frameCountLabel"></span>
            </div>
            <div class="range-row">
                <input type="range" id="frameSlider" min="0" max="0" value="0" step="1" style="width:480px;" onchange="sliderSeek()" />
                <span id="frameLabel"></span>
            </div>
            <div class="gif-row">
                <button onclick="createGif()">Create GIF from current frame</button>
                <span>Length (frames):</span>
                <input type="number" id="gifLength" value="90" min="1" step="1" style="width:60px;" />
                <span id="gifStatus"></span>
            </div>
            <div class="gif-row" style="margin-top:28px;">
                <div style="text-align:center;">
                    <div>Start Frame</div>
                    <img id="startFrameImg" width="240" />
                    <div id="startFrameLabel"></div>
                </div>
                <div style="text-align:center;">
                    <div>End Frame</div>
                    <img id="endFrameImg" width="240" />
                    <div id="endFrameLabel"></div>
                </div>
            </div>
        </div>
        <script>
        document.getElementById('uploadForm').onsubmit = async function(e) {
            e.preventDefault();
            const formData = new FormData(document.getElementById('uploadForm'));
            let resp = await fetch('/upload_video', {
                method: 'POST',
                body: formData
            });
            if (resp.ok) {
                location.reload();
            } else {
                alert('Failed to upload video.');
            }
        };
        let frame = 0;
        let frameCount = 0;
        function updateFrame() {
            document.getElementById('frame').src = '/frame?i=' + frame + '&_=' + Date.now();
            document.getElementById('frameInput').value = frame;
            document.getElementById('frameSlider').value = frame;
            document.getElementById('frameLabel').innerText = 'Frame: ' + frame + ' / ' + (frameCount-1);
            updateStartEndFrames();
        }
        function updateStartEndFrames() {
            let lengthVal = parseInt(document.getElementById('gifLength').value);
            if (isNaN(lengthVal) || lengthVal <= 0) lengthVal = 90;
            let startFrame = frame;
            let endFrame = Math.min(frame + lengthVal - 1, frameCount-1);
            document.getElementById('startFrameImg').src = '/frame?i=' + startFrame + '&_=' + Date.now();
            document.getElementById('endFrameImg').src = '/frame?i=' + endFrame + '&_=' + Date.now();
            document.getElementById('startFrameLabel').innerText = 'Frame: ' + startFrame;
            document.getElementById('endFrameLabel').innerText = 'Frame: ' + endFrame;
        }
        function seek(df) {
            frame = Math.max(0, Math.min(frameCount-1, frame + df));
            updateFrame();
        }
        function setFrame() {
            let f = parseInt(document.getElementById('frameInput').value);
            if (!isNaN(f)) {
                frame = Math.max(0, Math.min(frameCount-1, f));
                updateFrame();
            }
        }
        function sliderSeek() {
            let f = parseInt(document.getElementById('frameSlider').value);
            if (!isNaN(f)) {
                frame = f;
                updateFrame();
            }
        }
        async function getVideoInfo() {
            let resp = await fetch('/video_info');
            let data = await resp.json();
            frameCount = data.frame_count;
            document.getElementById('frameCountLabel').innerText = '/ ' + (frameCount-1);
            let slider = document.getElementById('frameSlider');
            slider.max = frameCount - 1;
            slider.value = 0;
        }
        async function createGif() {
            document.getElementById('gifStatus').innerText = 'Creating GIF...';
            let lengthVal = parseInt(document.getElementById('gifLength').value);
            if (isNaN(lengthVal) || lengthVal <= 0) lengthVal = 90;
            let resp = await fetch('/create_gif?start=' + frame + '&length=' + lengthVal, {method: 'POST'});
            if (resp.ok) {
                let data = await resp.json();
                document.getElementById('gifStatus').innerHTML = 'GIF saved: <a href="' + data.path + '" target="_blank">' + data.path + '</a>';
            } else {
                document.getElementById('gifStatus').innerText = 'GIF creation failed.';
            }
        }
        document.getElementById('gifLength').addEventListener('input', updateStartEndFrames);
        getVideoInfo().then(updateFrame);
        </script>
    </body>
    </html>
    ''')

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
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        abort(404, 'Video not found')
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if fps <= 0:
        abort(500, 'Invalid FPS')
    if start < 0 or start >= frame_count:
        abort(400, 'Invalid start frame')
    if length <= 0:
        abort(400, 'Invalid length')
    start_time = start / fps
    duration = length / fps
    gif_path = f'gif_{start}.gif'
    (
        ffmpeg
        .input(video_path, ss=start_time, t=duration)
        .output(
            gif_path,
            vf='fps=10,scale=360:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
            loop=0
        )
        .run(overwrite_output=True)
    )
    return jsonify({'path': f'/gif/{gif_path}'})

@app.route('/gif/<path:filename>')
def serve_gif(filename):
    gif_dir = os.getcwd()  # or specify a directory if you want
    gif_path = os.path.join(gif_dir, filename)
    if not os.path.isfile(gif_path):
        abort(404, 'GIF not found')
    return send_file(gif_path, mimetype='image/gif')

if __name__ == '__main__':
    app.run(debug=True)
