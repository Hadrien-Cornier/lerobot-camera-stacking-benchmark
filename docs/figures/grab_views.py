"""Decode one real frame from the public test videos, for the "camera views" figure.

It reads the same frame from the 3 separate files (SEP) and from the stacked file (STACK)
over hf://. It reads only a few MB. Needs: av, pillow, numpy, huggingface_hub.

    python docs/figures/grab_views.py
    python docs/figures/make_figures.py
"""

import json
from pathlib import Path

import av
import numpy as np
from huggingface_hub import HfFileSystem
from PIL import Image

REPO = "datasets/hadriencornier/lerobot-camera-stacking-benchmark"
REVISION = "b4a3426ab4b1105ecd2caf2e747019af898a6e5d"
BASE = f"{REPO}@{REVISION}/variants/20260925T025221Z/ckpt_full"
FRAME = 1500  # frame index inside group g000
CAMS = ["top", "left_wrist", "right_wrist"]
OUT = Path(__file__).resolve().parent / "views"


def decode(fs, path, index):
    with fs.open(path, "rb", block_size=256 * 1024) as f, av.open(f) as c:
        s = c.streams.video[0]
        target = int(index / s.average_rate / s.time_base)
        c.seek(target, stream=s, backward=True)
        for frame in c.decode(s):
            if frame.pts >= target:
                return frame.to_image()
    raise RuntimeError(f"frame {index} not found in {path}")


def main():
    OUT.mkdir(exist_ok=True)
    fs = HfFileSystem()
    info = {"frame": FRAME, "revision": REVISION, "psnr_db": {}}
    stacked = decode(fs, f"{BASE}/STACK/ckpt_full_g000.mp4", FRAME)
    st = np.asarray(stacked.convert("RGB"), dtype=np.float64)
    h = st.shape[0] // 3
    for k, cam in enumerate(CAMS):
        img = decode(fs, f"{BASE}/SEP/ckpt_full_g000__{cam}.mp4", FRAME)
        img.save(OUT / f"before_{cam}.png")
        img.save(OUT / f"before_{cam}.jpg", quality=92)
        b = np.asarray(img.convert("RGB"), dtype=np.float64)
        mse = ((st[k * h:(k + 1) * h] - b) ** 2).mean()
        info["psnr_db"][cam] = round(10 * np.log10(255**2 / mse), 1)
    stacked.save(OUT / "after_stacked.png")
    stacked.save(OUT / "after_stacked.jpg", quality=92)
    info["size_before"] = list(img.size)
    info["size_after"] = list(stacked.size)
    (OUT / "views.json").write_text(json.dumps(info, indent=1) + "\n")
    print(info)


if __name__ == "__main__":
    main()
