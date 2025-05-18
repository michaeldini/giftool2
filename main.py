from flask import Flask, send_file, request, render_template_string, abort
import cv2
import io
from PIL import Image

app = Flask(__name__)

VIDEO_PATH = 'sample.mp4'  # Change this to your video file path

@app.route('/')
def index():
    # Minimal HTML/JS for frame navigation
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Video Frame Viewer</title></head>
    <body>
        <h2>Video Frame Viewer</h2>
        <img id="frame" width="480" />
        <br>
        <button onclick="prevFrame()">Prev</button>
        <span id="frameNum">0</span>
        <button onclick="nextFrame()">Next</button>
        <script>
        let frame = 0;
        function updateFrame() {
            document.getElementById('frame').src = '/frame?i=' + frame + '&_=' + Date.now();
            document.getElementById('frameNum').innerText = frame;
        }
        function nextFrame() { frame++; updateFrame(); }
        function prevFrame() { if(frame>0) frame--; updateFrame(); }
        updateFrame();
        </script>
    </body>
    </html>
    ''')

@app.route('/frame')
def get_frame():
    i = int(request.args.get('i', 0))
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        abort(404, 'Video not found')
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        abort(404, 'Frame not found')
    # Convert BGR to RGB and encode as PNG
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)
