import cv2
import numpy as np
from pathlib import Path

def open_video(path: str):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")
    return cap

def get_props(cap: cv2.VideoCapture):
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    return fps, w, h, n

def read_frame_or_black(cap: cv2.VideoCapture, w: int, h: int):
    ok, frame = cap.read()
    if not ok or frame is None:
        return None
    if frame.shape[1] != w or frame.shape[0] != h:
        frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
    return frame

def make_collage_3_side_by_side(
    video1_path: str,
    video2_path: str,
    video3_path: str,
    output_path: str,
    target_height: int | None = None,
    pad_px: int = 0,
    pad_color_bgr: tuple[int, int, int] = (0, 0, 0),
    force_fps: float | None = None,
    codec: str = "mp4v",
):
    p1, p2, p3 = Path(video1_path), Path(video2_path), Path(video3_path)
    if not p1.exists() or not p2.exists() or not p3.exists():
        raise FileNotFoundError("One or more input videos do not exist.")

    cap1 = open_video(p1)
    cap2 = open_video(p2)
    cap3 = open_video(p3)

    fps1, w1, h1, n1 = get_props(cap1)
    fps2, w2, h2, n2 = get_props(cap2)
    fps3, w3, h3, n3 = get_props(cap3)

    # Choose a reasonable fps (prefer forced, else min fps to reduce drift)
    out_fps = float(force_fps) if force_fps is not None else float(min(fps1, fps2, fps3))
    if out_fps <= 0:
        out_fps = 30.0

    # Target height for all panels
    if target_height is None:
        target_height = int(min(h1, h2, h3))
    target_height = int(max(1, target_height))

    # Compute widths preserving aspect ratio
    def scaled_w(w, h, th):
        return int(round((w / max(1, h)) * th))

    sw1 = scaled_w(w1, h1, target_height)
    sw2 = scaled_w(w2, h2, target_height)
    sw3 = scaled_w(w3, h3, target_height)

    out_w = sw1 + sw2 + sw3 + pad_px * 2
    out_h = target_height

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(str(out_path), fourcc, out_fps, (out_w, out_h))
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter. Try codec='avc1' or a different output extension.")

    # Render for as long as at least one video still has frames
    done1 = done2 = done3 = False
    frames_written = 0

    while True:
        f1 = None if done1 else read_frame_or_black(cap1, sw1, target_height)
        f2 = None if done2 else read_frame_or_black(cap2, sw2, target_height)
        f3 = None if done3 else read_frame_or_black(cap3, sw3, target_height)

        if f1 is None:
            done1 = True
            f1 = np.full((target_height, sw1, 3), pad_color_bgr, dtype=np.uint8)
        if f2 is None:
            done2 = True
            f2 = np.full((target_height, sw2, 3), pad_color_bgr, dtype=np.uint8)
        if f3 is None:
            done3 = True
            f3 = np.full((target_height, sw3, 3), pad_color_bgr, dtype=np.uint8)

        if done1 and done2 and done3:
            break

        if pad_px > 0:
            pad = np.full((target_height, pad_px, 3), pad_color_bgr, dtype=np.uint8)
            row = np.hstack([f1, pad, f2, pad, f3])
        else:
            row = np.hstack([f1, f2, f3])

        writer.write(row)
        frames_written += 1

    cap1.release()
    cap2.release()
    cap3.release()
    writer.release()

    print("✅ Collage complete!")
    print(f"Output: {out_path}")
    print(f"Frames written: {frames_written}")
    print(f"Resolution: {out_w}x{out_h} @ {out_fps:.3f} fps")
    print(f"Inputs frame counts: {n1}, {n2}, {n3}")

if __name__ == "__main__":
    make_collage_3_side_by_side(
        video1_path="videos/game02/game02_ai.mp4", # Change each of these paths to your local locations of choice
        video2_path="videos/game02/game02_ai_heatvision.mp4",
        video3_path="videos/game02/game02_ai_line.mp4",
        output_path="gamevision.mp4",
        target_height=None,   # or set e.g. 720
        pad_px=12,            # set 0 for no separator
        pad_color_bgr=(0, 0, 0),
        force_fps=None,       # or set e.g. 30
        codec="mp4v",
    )
