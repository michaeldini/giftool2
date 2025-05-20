document.getElementById('uploadBtn').onclick = function () {
    document.getElementById('videoFile').click();
};
document.getElementById('videoFile').onchange = async function () {
    if (this.files.length > 0) {
        const formData = new FormData(document.getElementById('uploadForm'));
        let resp = await fetch('/upload_video', {
            method: 'POST',
            body: formData
        });
        if (resp.ok) {
            // Optionally, you can reload or update UI here
            location.reload();
        } else {
            alert('Failed to upload video.');
        }
    }
};

let frame = 0;
let frameCount = 0;
let playInterval = null;

function updateFrame() {
    // Update the main preview (now startFrameImg)
    document.getElementById('startFrameImg').src = '/frame?i=' + frame + '&_=' + Date.now();
    document.getElementById('frameInput').value = frame;
    document.getElementById('frameSlider').value = frame;
    document.getElementById('frameLabel').innerText = ' / ' + (frameCount - 1);
    updateEndFrame();
}

function updateEndFrame() {
    let lengthVal = parseInt(document.getElementById('gifLength').value);
    if (isNaN(lengthVal) || lengthVal <= 0) lengthVal = 90;
    let endFrame = Math.min(frame + lengthVal - 1, frameCount - 1);
    document.getElementById('endFrameImg').src = '/frame?i=' + endFrame + '&_=' + Date.now();
    document.getElementById('startFrameLabel').innerText = 'Frame: ' + frame;
    document.getElementById('endFrameLabel').innerText = 'Frame: ' + endFrame;
}

function seek(df) {
    frame = Math.max(0, Math.min(frameCount - 1, frame + df));
    updateFrame();
}
function setFrame() {
    let f = parseInt(document.getElementById('frameInput').value);
    if (!isNaN(f)) {
        frame = Math.max(0, Math.min(frameCount - 1, f));
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

    let slider = document.getElementById('frameSlider');
    slider.max = frameCount - 1;
    slider.value = 0;
}
async function createGif() {
    document.getElementById('gifStatus').innerText = 'Creating GIF...';
    let lengthVal = parseInt(document.getElementById('gifLength').value);
    if (isNaN(lengthVal) || lengthVal <= 0) lengthVal = 90;
    let brightnessVal = parseFloat(document.getElementById('brightnessInput').value);
    if (isNaN(brightnessVal) || brightnessVal <= 0) brightnessVal = 1.0;
    let resp = await fetch('/create_gif?start=' + frame + '&length=' + lengthVal + '&brightness=' + brightnessVal, { method: 'POST' });
    if (resp.ok) {
        let data = await resp.json();
        document.getElementById('gifStatus').innerHTML = 'GIF saved: <a href="' + data.path + '" target="_blank">' + data.path + '</a>';
    } else {
        document.getElementById('gifStatus').innerText = 'GIF creation failed.';
    }
}
function playFrames() {
    if (playInterval !== null) return;
    playInterval = setInterval(() => {
        if (frame + 10 >= frameCount) {
            frame = frameCount - 1;
            updateFrame();
            pauseFrames();
        } else {
            frame = Math.min(frame + 10, frameCount - 1);
            updateFrame();
        }
    }, 120);
}

function pauseFrames() {
    if (playInterval !== null) {
        clearInterval(playInterval);
        playInterval = null;
    }
}
document.getElementById('gifLength').addEventListener('input', updateEndFrame);
getVideoInfo().then(updateFrame);
