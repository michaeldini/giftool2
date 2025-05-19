import toga
from toga.style import Pack
import cv2
from PIL import Image
import ffmpeg
import os
import uuid

class GifToolApp(toga.App):
    def startup(self):
        self.video_path = None
        self.frame = 0
        self.frame_count = 0
        self.fps = 0
        self.current_frame_img_path = None

        # Main layout
        main_box = toga.Box(style=Pack(direction="column", margin=10, align_items="center"))

        # File open button
        self.open_button = toga.Button('Open Video', on_press=self.open_video, style=Pack(margin=5))
        main_box.add(self.open_button)

        # Frame navigation
        nav_box = toga.Box(style=Pack(direction="row", margin=5))
        self.frame_input = toga.TextInput(style=Pack(width=80))
        self.frame_input.value = "0"
        self.seek_button = toga.Button('Go to Frame', on_press=self.seek_frame, style=Pack(margin_left=5))
        nav_box.add(self.frame_input)
        nav_box.add(self.seek_button)
        main_box.add(nav_box)

        # GIF creation
        gif_box = toga.Box(style=Pack(direction="row", margin=5))
        self.length_input = toga.TextInput(style=Pack(width=80))
        self.length_input.value = "90"
        self.gif_button = toga.Button('Create GIF', on_press=self.create_gif, style=Pack(margin_left=5))
        gif_box.add(toga.Label('Length (frames):', style=Pack(margin_right=5)))
        gif_box.add(self.length_input)
        gif_box.add(self.gif_button)
        main_box.add(gif_box)

        # Status label
        self.status_label = toga.Label('', style=Pack(margin=(5, 0)))
        main_box.add(self.status_label)

        # Image preview
        self.image_view = toga.ImageView(None, style=Pack(width=360, height=240, margin=10))
        main_box.add(self.image_view)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

    async def open_video(self, widget):
        # Use the new dialog API for Toga (async)
        dialog = toga.OpenFileDialog("Select a video")
        file_path = await self.main_window.dialog(dialog)
        if file_path is not None:
            self.video_path = str(file_path)
            cap = cv2.VideoCapture(self.video_path)
            self.frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            self.status_label.text = f"Loaded video with {self.frame_count} frames."
            self.frame_input.value = "0"
            self.show_frame(0)

    def seek_frame(self, widget):
        if not self.video_path:
            self.status_label.text = "No video loaded."
            return
        try:
            frame_num = int(self.frame_input.value)
        except ValueError:
            self.status_label.text = "Invalid frame number."
            return
        self.show_frame(frame_num)

    def show_frame(self, frame_num):
        if not self.video_path:
            self.status_label.text = "No video loaded."
            return
        cap = cv2.VideoCapture(str(self.video_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            self.status_label.text = "Frame not found."
            return
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        temp_path = os.path.join(os.path.dirname(__file__), f"current_frame_{uuid.uuid4().hex}.png")
        img.save(temp_path)
        self.current_frame_img_path = temp_path
        self.image_view.image = toga.Image(temp_path)
        self.status_label.text = f"Frame {frame_num} loaded."

    def create_gif(self, widget):
        if not self.video_path:
            self.status_label.text = "No video loaded."
            return
        try:
            length = int(self.length_input.value)
            start = int(self.frame_input.value)
        except ValueError:
            self.status_label.text = "Invalid input."
            return
        if self.fps <= 0:
            self.status_label.text = "Invalid FPS."
            return
        start_time = start / self.fps
        duration = length / self.fps
        gif_path = os.path.join(os.path.dirname(__file__), f'gif_{start}_{uuid.uuid4().hex}.gif')
        (
            ffmpeg
            .input(self.video_path, ss=start_time, t=duration)
            .output(
                gif_path,
                vf='fps=10,scale=360:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
                loop=0
            )
            .run(overwrite_output=True)
        )
        self.status_label.text = f"GIF saved as {gif_path}"


def main():
    return GifToolApp('GifTool2', 'org.example.giftool2')
if __name__ == '__main__':
    app = main()
    app.main_loop()