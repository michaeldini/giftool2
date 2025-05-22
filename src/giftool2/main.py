def create_gif_with_ffmpeg(video_path, gif_path, start_time, duration, video_fps, fps, scale, brightness):
    """
    Encapsulates the ffmpeg logic for creating a slow-motion GIF with palettegen and paletteuse.
    """
    import ffmpeg
    interp_fps = video_fps * 2
    vf_filters = (
        f'minterpolate=fps={interp_fps}:mi_mode=mci,'
        f'setpts=2.0*PTS,'
        f'fps={fps},'
        f'scale={scale}:-1:flags=lanczos'
    )
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
    return gif_path

def main():
    # flask
    from .app import app
    app.run(debug=True)
    
if __name__ == "__main__":
    main()