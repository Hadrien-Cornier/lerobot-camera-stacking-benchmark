"""Draw the README figures as SVG files, in a light and a dark version.

Run from anywhere:

    python docs/figures/make_figures.py

No dependencies. Every number below comes from the result files named next to it.
"""

from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "light": dict(
        bg="#fcfcfb", panel="#f3f2ee", ink="#0b0b0b", ink2="#52514e", muted="#898781",
        grid="#e1e0d9", axis="#c3c2b7", border="#e1e0d9", on_color="#0b0b0b",
        cam=["#2a78d6", "#eb6834", "#1baf7a"], stack="#4a3aa7", sep="#898781",
    ),
    "dark": dict(
        bg="#1a1a19", panel="#242423", ink="#ffffff", ink2="#c3c2b7", muted="#898781",
        grid="#2c2c2a", axis="#383835", border="#383835", on_color="#0b0b0b",
        cam=["#3987e5", "#d95926", "#199e70"], stack="#9085e9", sep="#898781",
    ),
}

CAMS = ["top", "left wrist", "right wrist"]


# ---------------------------------------------------------------- helpers


def text(x, y, s, size=14, fill="ink", weight=400, anchor="start", extra=""):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}" fill="{{{fill}}}" {extra}>{escape(s)}</text>'
    )


def rect(x, y, w, h, fill="none", stroke="none", rx=4, sw=1, extra=""):
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'
    )


def arrow(x1, y1, x2, y2, color="{muted}", sw=1.5, extra=""):
    """Straight arrow with a small open head."""
    import math

    a = math.atan2(y2 - y1, x2 - x1)
    h = 7
    p1 = (x2 - h * math.cos(a - 0.45), y2 - h * math.sin(a - 0.45))
    p2 = (x2 - h * math.cos(a + 0.45), y2 - h * math.sin(a + 0.45))
    return (
        f'<g stroke="{color}" stroke-width="{sw}" fill="none" stroke-linecap="round" '
        f'stroke-linejoin="round" {extra}>'
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
        f'<polyline points="{p1[0]:.1f},{p1[1]:.1f} {x2:.1f},{y2:.1f} {p2[0]:.1f},{p2[1]:.1f}"/></g>'
    )


def bar_h(x, y, w, h, fill, r=4):
    """Horizontal bar: square at the baseline, rounded data end."""
    w = max(w, r + 1)
    return (
        f'<path d="M{x:.1f},{y:.1f} H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} '
        f'V{y + h - r:.1f} Q{x + w:.1f},{y + h:.1f} {x + w - r:.1f},{y + h:.1f} H{x:.1f} Z" fill="{fill}"/>'
    )


def page(w, h, body, theme, style="", title="", desc=""):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-labelledby="t d" font-family="{FONT}">'
        f"<title id=\"t\">{escape(title)}</title><desc id=\"d\">{escape(desc)}</desc>"
        f"<style>{style}</style>"
        + rect(0.5, 0.5, w - 1, h - 1, fill="{bg}", stroke="{border}", rx=12)
        + body
        + "</svg>\n"
    )
    t = THEMES[theme]
    for k, v in t.items():
        if isinstance(v, list):
            for i, c in enumerate(v):
                svg = svg.replace("{" + f"{k}{i}" + "}", c)
        else:
            svg = svg.replace("{" + k + "}", v)
    return svg


def save(name, make):
    for theme in THEMES:
        suffix = "" if theme == "light" else "-dark"
        (OUT / f"{name}{suffix}.svg").write_text(make(theme))


def header(title, subtitle, y=40):
    return text(32, y, title, 20, weight=650) + text(32, y + 24, subtitle, 14, fill="ink2")


def cam_legend(x, y):
    out = []
    for i, c in enumerate(CAMS):
        out.append(rect(x, y - 10, 12, 12, fill=f"{{cam{i}}}", rx=3))
        out.append(text(x + 18, y, c, 13, fill="ink2"))
        x += 34 + len(c) * 6.6
    return "".join(out)


# ---------------------------------------------------------------- 1. animation

# Measured CPU time per frame, StreamingLeRobotDataset, 8 shards, cache 100
# (results/round2/summary.md, "CPU ms/frame": SEP_S8_c100_seq 5.5, STACK_S8_c100 2.9;
# fps 181.5 and 342.2).
SEP_MS, STACK_MS = 5.5, 2.9
SIM_MS = 11.0  # simulated time shown in one loop
LOOP_S = 10.0  # real seconds per loop
RUN_PCT = 88.0  # share of the loop that plays; the rest holds the end state
EPS = 0.02


def pct(t_ms):
    return min(t_ms, SIM_MS) / SIM_MS * RUN_PCT


class Anim:
    """Collect CSS keyframes. Each animated element gets its own class."""

    def __init__(self):
        self.rules = []
        self.n = 0

    def _name(self):
        self.n += 1
        return f"a{self.n}"

    def steps(self, changes, init, prop, fmt):
        """Hard switches of one CSS property at the given times (ms)."""
        name = self._name()
        pts = [(0.0, init)]
        cur = init
        for t, v in sorted(changes):
            p = pct(t)
            if p <= 0:
                pts = [(0.0, v)]
            else:
                pts += [(p - EPS, cur), (p, v)]
            cur = v
        pts.append((100.0, cur))
        body = " ".join(f"{p:.3f}% {{ {prop}: {fmt(v)}; }}" for p, v in pts)
        self.rules.append(
            f"@keyframes {name} {{ {body} }} .{name} {{ animation: {name} {LOOP_S}s linear infinite; }}"
        )
        return name

    def show(self, windows):
        """Opacity 1 inside the windows [(t0, t1)], 0 elsewhere. t1=None means until loop end."""
        ch = []
        for t0, t1 in windows:
            ch.append((t0, 1))
            if t1 is not None:
                ch.append((t1, 0))
        return self.steps(ch, 0, "opacity", str)

    def reveal(self, t0, t1):
        """Grow from the left between t0 and t1, then stay."""
        name = self._name()
        a, b = pct(t0), pct(t1)
        self.rules.append(
            f"@keyframes {name} {{ 0%, {a:.3f}% {{ transform: scaleX(0); }} {b:.3f}%, 100% {{ transform: scaleX(1); }} }} "
            f".{name} {{ transform-box: fill-box; transform-origin: 0 50%; "
            f"animation: {name} {LOOP_S}s linear infinite; }}"
        )
        return name

    def move_x(self, dx):
        name = self._name()
        self.rules.append(
            f"@keyframes {name} {{ 0% {{ transform: translateX(0px); }} {RUN_PCT}%, 100% {{ transform: translateX({dx}px); }} }} "
            f".{name} {{ animation: {name} {LOOP_S}s linear infinite; }}"
        )
        return name

    def css(self):
        return (
            " ".join(self.rules)
            + " @media (prefers-reduced-motion: reduce) { * { animation-delay: -8.9s !important;"
            " animation-play-state: paused !important; } }"
        )


def loading(theme):
    W, H = 960, 612
    A = Anim()
    o = [header(
        "How StreamingLeRobotDataset makes one training frame",
        "Now, and what we tested. Slowed down about 800x. Times are measured CPU time per frame.",
    )]

    # Decode schedule, in ms. Now: cameras one after another. Stacked: one call per frame.
    part = SEP_MS / 3
    sep_blocks = []  # (t0, t1, cam, frame)
    t, f = 0.0, 0
    while t < SIM_MS - 1e-9:
        for c in range(3):
            sep_blocks.append((t, t + part, c, f))
            t += part
        f += 1
    stack_blocks = []
    t, f = 0.0, 0
    while t < SIM_MS - 1e-9:
        stack_blocks.append((t, min(t + STACK_MS, SIM_MS), f))
        t += STACK_MS
        f += 1

    X_FILE, X_DEC, X_SHELF, WBOX = 32, 312, 612, 212
    ROW_H, ROW_GAP = 30, 8
    TALL = 3 * ROW_H + 2 * ROW_GAP

    def lane_head(y, label, rate):
        return (
            text(32, y, label, 16, weight=650)
            + text(928, y, rate, 16, weight=650, anchor="end")
            + text(X_FILE, y + 26, "File on the Hub", 13, fill="muted")
            + text(X_DEC, y + 26, "Decoder (TorchCodec)", 13, fill="muted")
            + text(X_SHELF, y + 26, "Finished frames", 13, fill="muted")
        )

    def shelf_icon(x, y, fills):
        """One finished frame: 3 camera images and the joint state row. fills: list of (cam, class)."""
        s = [rect(x, y + k * 34, 48, 30, fill="none", stroke="{axis}", rx=4, extra='stroke-dasharray="3 3"')
             for k in range(3)]
        for k, cls in fills:
            s.append(f'<g class="{cls}">' + rect(x, y + k * 34, 48, 30, fill=f"{{cam{k}}}", rx=4) + "</g>")
        return "".join(s)

    # ---- lane 1: now
    y = 108
    o.append(lane_head(y, "Now: one MP4 per camera", "182 frames/s"))
    top = y + 40
    for k in range(3):
        ry = top + k * (ROW_H + ROW_GAP)
        win = [(b[0], b[1]) for b in sep_blocks if b[2] == k]
        hl = A.show(win)
        o.append(rect(X_FILE, ry, WBOX, ROW_H, fill="{panel}", stroke="{border}"))
        o.append(f'<g class="{hl}">' + rect(X_FILE, ry, WBOX, ROW_H, fill=f"{{cam{k}}}", stroke=f"{{cam{k}}}",
                                             sw=2, extra='fill-opacity="0.16"') + "</g>")
        o.append(rect(X_FILE + 10, ry + 9, 12, 12, fill=f"{{cam{k}}}", rx=3))
        o.append(text(X_FILE + 30, ry + 20, f"{CAMS[k]} / file-000.mp4", 13))
        o.append(arrow(X_FILE + WBOX + 8, ry + 15, X_DEC - 8, ry + 15, color="{axis}"))
        o.append(f'<g class="{hl}">' + arrow(X_FILE + WBOX + 8, ry + 15, X_DEC - 8, ry + 15,
                                             color=f"{{cam{k}}}", sw=2) + "</g>")
        o.append(rect(X_DEC, ry, WBOX, ROW_H, fill="{panel}", stroke="{border}"))
        o.append(f'<g class="{hl}">' + rect(X_DEC, ry, WBOX, ROW_H, fill=f"{{cam{k}}}", stroke=f"{{cam{k}}}",
                                             sw=2, extra='fill-opacity="0.16"') + "</g>")
        o.append(text(X_DEC + 12, ry + 20, f"decode {CAMS[k]}", 13))
        o.append(arrow(X_DEC + WBOX + 8, ry + 15, X_SHELF - 12, ry + 15, color="{axis}"))
    n_frames_sep = sep_blocks[-1][3] + 1
    for fi in range(n_frames_sep):
        x = X_SHELF + fi * 66
        start = min(b[0] for b in sep_blocks if b[3] == fi)
        outline = A.show([(start, None)])
        fills = [(b[2], A.show([(b[1], None)])) for b in sep_blocks if b[3] == fi]
        o.append(f'<g class="{outline}">' + shelf_icon(x, top, fills) + "</g>")

    # ---- lane 2: stacked
    y = 300
    o.append(lane_head(y, "Tested: the 3 views stacked in one MP4", "342 frames/s"))
    top = y + 40
    busy = A.show([(0, SIM_MS)])
    o.append(rect(X_FILE, top, WBOX, TALL, fill="{panel}", stroke="{border}"))
    o.append(f'<g class="{busy}">' + rect(X_FILE, top, WBOX, TALL, fill="{stack}", stroke="{stack}", sw=2,
                                          extra='fill-opacity="0.10"') + "</g>")
    o.append(text(X_FILE + 12, top + 20, "stacked / file-000.mp4", 13))
    for k in range(3):
        by = top + 30 + k * 23
        o.append(rect(X_FILE + 12, by, WBOX - 24, 19, fill=f"{{cam{k}}}", rx=3))
        o.append(text(X_FILE + 20, by + 14, CAMS[k], 12, fill="on_color", weight=600))
    o.append(arrow(X_FILE + WBOX + 8, top + TALL / 2, X_DEC - 8, top + TALL / 2, color="{axis}"))
    o.append(f'<g class="{busy}">' + arrow(X_FILE + WBOX + 8, top + TALL / 2, X_DEC - 8, top + TALL / 2,
                                           color="{stack}", sw=2) + "</g>")
    o.append(rect(X_DEC, top, WBOX, TALL, fill="{panel}", stroke="{border}"))
    o.append(f'<g class="{busy}">' + rect(X_DEC, top, WBOX, TALL, fill="{stack}", stroke="{stack}", sw=2,
                                          extra='fill-opacity="0.10"') + "</g>")
    o.append(text(X_DEC + 12, top + 44, "1 decode call per frame", 13, weight=600))
    o.append(text(X_DEC + 12, top + 66, "then cut the tall image", 13, fill="ink2"))
    o.append(text(X_DEC + 12, top + 84, "into 3 camera images", 13, fill="ink2"))
    for k in range(3):
        ry = top + k * (ROW_H + ROW_GAP)
        o.append(arrow(X_DEC + WBOX + 8, top + TALL / 2, X_SHELF - 12, ry + 15, color="{axis}"))
    for b in stack_blocks:
        x = X_SHELF + b[2] * 66
        outline = A.show([(b[0], None)])
        cls = A.show([(b[1], None)]) if b[1] < SIM_MS - 1e-9 or abs(b[1] - b[0] - STACK_MS) < 1e-9 else None
        fills = [(k, cls) for k in range(3)] if cls else []
        o.append(f'<g class="{outline}">' + shelf_icon(x, top, fills) + "</g>")

    # ---- timeline
    X0, X1 = 150, 916
    px = (X1 - X0) / SIM_MS
    ty = 484
    o.append(text(32, ty - 16, "Timeline (CPU time)", 14, weight=650))
    hold = A.show([(SIM_MS, None)])
    done_stack = sum(1 for b in stack_blocks if abs(b[1] - b[0] - STACK_MS) < 1e-9)
    frac = (SIM_MS - done_stack * STACK_MS) / STACK_MS
    o.append(f'<g class="{hold}">' + text(
        928, ty - 16,
        f"Same {SIM_MS:g} ms: separate files finish {n_frames_sep} frames, stacked finishes "
        f"{done_stack + frac:.1f}.", 14, weight=650, anchor="end") + "</g>")
    rows = [("Now", ty), ("Stacked", ty + 34)]
    for label, ry in rows:
        o.append(text(32, ry + 17, label, 13, fill="ink2"))
        o.append(rect(X0, ry, X1 - X0, 24, fill="{panel}", rx=4))
    for t0, t1, c, _ in sep_blocks:
        cls = A.reveal(t0, t1)
        o.append(f'<g class="{cls}">' + rect(X0 + t0 * px + 1, ty, (t1 - t0) * px - 2, 24,
                                             fill=f"{{cam{c}}}", rx=4) + "</g>")
    for t0, t1, fi in stack_blocks:
        cls = A.reveal(t0, t1)
        w = (t1 - t0) * px - 2
        g = "".join(rect(X0 + t0 * px + 1, ty + 34 + k * 8, w, 8, fill=f"{{cam{k}}}", rx=0) for k in range(3))
        o.append(f'<g class="{cls}">' + g + "</g>")
    for t0, t1, c, _ in sep_blocks:
        o.append(text(X0 + t0 * px + 8, ty + 16, f"call {c + 1}", 12, fill="on_color", weight=600,
                      extra=f'class="{A.show([(t1, None)])}"'))
    for t0, t1, _ in stack_blocks:
        if abs(t1 - t0 - STACK_MS) < 1e-9:
            o.append(text(X0 + t0 * px + 8, ty + 34 + 16, "call 1", 12, fill="on_color", weight=600,
                          extra=f'class="{A.show([(t1, None)])}"'))
    ax = ty + 70
    o.append(f'<line x1="{X0}" y1="{ax}" x2="{X1}" y2="{ax}" stroke="{{axis}}"/>')
    for ms in range(int(SIM_MS) + 1):
        x = X0 + ms * px
        o.append(f'<line x1="{x:.1f}" y1="{ax}" x2="{x:.1f}" y2="{ax + 5}" stroke="{{axis}}"/>')
        o.append(text(x, ax + 19, f"{ms} ms" if ms in (0, int(SIM_MS)) else str(ms), 12, fill="muted",
                      anchor="middle"))
    ph = A.move_x((X1 - X0))
    o.append(f'<g class="{ph}"><line x1="{X0}" y1="{ty - 6}" x2="{X0}" y2="{ax}" stroke="{{ink}}" '
             f'stroke-width="2" stroke-linecap="round"/></g>')
    o.append(text(32, H - 18, "Network is not drawn: in streaming, one 5 MB download holds about 1,700 frames. "
                  "The 5.5 ms is split into 3 equal parts for the picture.", 12.5, fill="muted"))
    return page(W, H, "".join(o), theme, A.css(),
                title="How StreamingLeRobotDataset makes one training frame, now and stacked",
                desc="Now, each frame needs 3 files and 3 decode calls, one after another: 5.5 ms of CPU. "
                     "Stacked, one file and one decode call, then a cut into 3 images: 2.9 ms. "
                     "In 11 ms, separate files finish 2 frames and stacked finishes 3.8.")


# ---------------------------------------------------------------- 2. layouts


def layouts(theme):
    W, H = 960, 560
    o = [header("What we tested: 5 ways to store the same 3 cameras",
                "The same frames in every layout. Each square is one frame. Its color is the camera.")]
    o.append(cam_legend(650, 40))
    S, G = 12, 3  # square size, gap

    def frames(x, y, n, cams, tall=False):
        s = []
        for i in range(n):
            if tall:
                for k in range(3):
                    s.append(rect(x + i * (S + G), y + k * S, S, S - 1, fill=f"{{cam{k}}}", rx=1))
            else:
                s.append(rect(x + i * (S + G), y, S, S, fill=f"{{cam{cams}}}", rx=2))
        return "".join(s)

    def file_box(x, y, w, h):
        return rect(x, y, w, h, fill="{panel}", stroke="{axis}", rx=5)

    rows = [
        ("SEP", "One MP4 per camera. This is LeRobot v3 today.", "A frame needs 3 files and 3 decoders."),
        ("STACK", "The 3 views stacked into one tall video.", "A frame needs 1 file and 1 decoder."),
        ("BIG", "Like SEP, but each file is 3x longer.", "Tests fewer files, without stacking."),
        ("MULTI", "One MP4 with 3 video tracks, copied from SEP.", "1 file, but still 3 decoders."),
        ("Equal size", "STACK and MULTI cut at keyframes", "to the same size in bytes as SEP files."),
    ]
    DX, TX = 170, 612
    for i, (name, l1, l2) in enumerate(rows):
        y = 100 + i * 88
        if i:
            o.append(f'<line x1="32" y1="{y - 12}" x2="928" y2="{y - 12}" stroke="{{grid}}"/>')
        o.append(text(32, y + 38, name, 16, weight=650))
        o.append(text(TX, y + 30, l1, 14))
        o.append(text(TX, y + 50, l2, 14, fill="ink2"))
        if name == "SEP":
            for k in range(3):
                o.append(file_box(DX, y + k * 22, 138, 19) + frames(DX + 4, y + k * 22 + 3.5, 9, k))
        elif name == "STACK":
            o.append(file_box(DX, y + 4, 138, 50) + frames(DX + 4, y + 10, 9, None, tall=True))
        elif name == "BIG":
            for k in range(3):
                o.append(file_box(DX, y + k * 22, 408, 19) + frames(DX + 4, y + k * 22 + 3.5, 27, k))
                for e in (1, 2):
                    xs = DX + 4 + e * 9 * (S + G) - 2
                    o.append(f'<line x1="{xs}" y1="{y + k * 22 + 2}" x2="{xs}" y2="{y + k * 22 + 17}" '
                             f'stroke="{{ink2}}" stroke-width="1.5"/>')
        elif name == "MULTI":
            o.append(file_box(DX, y, 138, 66))
            for k in range(3):
                o.append(frames(DX + 4, y + 6 + k * 20, 9, k))
            o.append(text(DX + 150, y + 38, "3 tracks, 1 file", 12, fill="muted"))
        else:
            for j in range(3):
                x = DX + j * 60
                o.append(file_box(x, y + 4, 52, 50) + frames(x + 4, y + 10, 3, None, tall=True))
            o.append(text(DX + 186, y + 34, "STACK, cut into", 12, fill="muted"))
            o.append(text(DX + 186, y + 50, "3 SEP-size files", 12, fill="muted"))
    o.append(text(DX + 416, 100 + 2 * 88 + 72, "3 SEP files joined", 12, fill="muted", anchor="end"))
    o.append(text(32, H - 18, "All layouts use LeRobot's default AV1 settings. Details and file sizes: METHOD.md.",
                  12.5, fill="muted"))
    return page(W, H, "".join(o), theme, title="The 5 file layouts we tested",
                desc="SEP: one file per camera. STACK: the 3 views in one tall video. BIG: SEP with files 3x "
                     "longer. MULTI: one file with 3 video tracks. Equal size: STACK and MULTI cut to SEP's file size.")


# ---------------------------------------------------------------- 3. read modes


def read_modes(theme):
    W, H = 960, 372
    o = [header("What we tested: 3 ways training reads the videos",
                "Each strip is one video file. Each square is one frame.")]
    PW, PX = 288, [32, 336, 640]
    top = 96
    S, G, N = 13, 3, 17
    panels = [
        ("Streaming", "StreamingLeRobotDataset",
         ["Reads each file forward.", "One 5 MB download feeds", "about 1,700 frames."],
         "Stacked: 1.9x faster"),
        ("Random access", "LeRobotDataset[i]",
         ["Jumps to any frame.", "Each jump can need a new", "network request."],
         "1 reader: the same. 8 readers: 1.5x"),
        ("Whole episodes", "PR #3917",
         ["Downloads a whole episode in", "one request per file. Keeps", "32 episodes in RAM."],
         "Stacked: 1.4x to 1.5x faster"),
    ]
    for i, (name, code, lines, result) in enumerate(panels):
        x = PX[i]
        o.append(rect(x, top, PW, 256, fill="{panel}", rx=10))
        o.append(text(x + 16, top + 28, name, 16, weight=650))
        o.append(text(x + 16, top + 48, code, 13, fill="muted",
                      extra="font-family=\"ui-monospace, SFMono-Regular, Menlo, monospace\""))
        sy = top + 84
        sx = x + (PW - (N * (S + G) - G)) / 2
        hot = set()
        if i == 1:
            hot = {2, 9, 14}
        if i == 2:
            hot = set(range(5, 11))
        for j in range(N):
            fill = "{stack}" if j in hot else "{axis}"
            o.append(rect(sx + j * (S + G), sy, S, S, fill=fill, rx=2))
        if i == 0:
            o.append(arrow(sx, sy + 26, sx + N * (S + G) - G, sy + 26, color="{stack}", sw=2))
            o.append(f'<path d="M{sx},{sy - 6} v-5 H{sx + 11 * (S + G) - G} v5" fill="none" stroke="{{ink2}}"/>')
            o.append(text(sx + (11 * (S + G)) / 2, sy - 16, "one download", 12, fill="ink2", anchor="middle"))
        if i == 1:
            prev = sx - 6
            for j in sorted(hot):
                cx = sx + j * (S + G) + S / 2
                o.append(f'<path d="M{prev:.1f},{sy - 4} Q{(prev + cx) / 2:.1f},{sy - 30} {cx:.1f},{sy - 4}" '
                         f'fill="none" stroke="{{stack}}" stroke-width="2" stroke-linecap="round"/>')
                prev = cx
        if i == 2:
            ex0 = sx + 5 * (S + G)
            ex1 = sx + 11 * (S + G) - G
            o.append(f'<path d="M{ex0},{sy - 6} v-5 H{ex1} v5" fill="none" stroke="{{ink2}}"/>')
            o.append(text((ex0 + ex1) / 2, sy - 16, "one episode", 12, fill="ink2", anchor="middle"))
            o.append(arrow((ex0 + ex1) / 2, sy + S + 4, (ex0 + ex1) / 2, sy + S + 22, color="{stack}", sw=2))
            o.append(rect(ex0 - 30, sy + S + 26, ex1 - ex0 + 60, 20, fill="{bg}", stroke="{axis}", rx=4))
            o.append(text((ex0 + ex1) / 2, sy + S + 40, "RAM pool", 12, fill="ink2", anchor="middle"))
        for k, line in enumerate(lines):
            o.append(text(x + 16, top + 164 + k * 20, line, 14, fill="ink2"))
        o.append(f'<line x1="{x + 16}" y1="{top + 216}" x2="{x + PW - 16}" y2="{top + 216}" stroke="{{grid}}"/>')
        o.append(text(x + 16, top + 240, result, 14, weight=650))
    return page(W, H, "".join(o), theme, title="The 3 read patterns we tested",
                desc="Streaming reads each file forward. Random access jumps to any frame. PR #3917 downloads "
                     "whole episodes into a RAM pool.")


# ---------------------------------------------------------------- 4. decoder cache


def cache(theme):
    W, H = 960, 420
    o = [header("Why separate files collapse when the decoder cache is too small",
                "Each worker keeps a cache of open video decoders. A file not in the cache must be opened "
                "again over the network.")]
    SLOT, GAP, N = 34, 6, 12
    X0 = 32
    # results/round2/summary.md: SEP_S8_c12_seq 4.6 fps, hit 0.506, open 143 ms;
    # STACK_S8_c12 308.3 fps, hit 1.000.
    rows = [
        ("Separate files: 8 shards x 3 cameras = 24 files in use", 24, False, "hit rate 0.5", "4.6 frames/s"),
        ("Stacked: 8 shards x 1 file = 8 files in use", 8, True, "hit rate 1.0", "308 frames/s"),
    ]
    for r, (label, n, stacked, hit, fps) in enumerate(rows):
        y = 118 + r * 124
        o.append(text(X0, y, label, 15, weight=650))
        by = y + 16
        o.append(rect(X0 - 6, by - 6, N * (SLOT + GAP) - GAP + 12, SLOT + 12, fill="none", stroke="{ink2}",
                      rx=8, sw=1.5))
        o.append(text(X0, by + SLOT + 26, "cache: 12 open decoders", 12, fill="muted"))

        def chip(x, yy, j, size=SLOT, dashed=False):
            if stacked:
                h = (size - 4) / 3
                return "".join(rect(x + 2, yy + 2 + k * h, size - 4, h - 1, fill=f"{{cam{k}}}", rx=1)
                               for k in range(3))
            extra = 'fill-opacity="0.35"' if dashed else ""
            return rect(x + 3, yy + 3, size - 6, size - 6, fill=f"{{cam{j % 3}}}", rx=4, extra=extra)

        for j in range(N):
            x = X0 + j * (SLOT + GAP)
            if j < min(n, N):
                o.append(chip(x, by, j))
            else:
                o.append(rect(x + 3, by + 3, SLOT - 6, SLOT - 6, fill="none", stroke="{axis}", rx=4,
                              extra='stroke-dasharray="3 3"'))
        ox = X0 + N * (SLOT + GAP) + 24
        if n > N:
            o.append(arrow(ox + 150, by + SLOT + 8, ox - 18, by + SLOT + 8, color="{ink2}", sw=1.5))
            for j in range(n - N):
                cx = ox + (j % 6) * 26
                cy = by - 4 + (j // 6) * 22
                o.append(rect(cx, cy, 20, 18, fill=f"{{cam{j % 3}}}", rx=3, extra='fill-opacity="0.4"'))
            o.append(text(ox, by + SLOT + 30, "12 more: evicted and reopened,", 12, fill="ink2"))
            o.append(text(ox, by + SLOT + 46, "about 143 ms each", 12, fill="ink2"))
        else:
            o.append(text(ox, by + 22, "All files fit.", 13, fill="ink2"))
        o.append(text(928, by + 10, fps, 22, weight=650, anchor="end"))
        o.append(text(928, by + 32, hit, 13, fill="ink2", anchor="end"))
    o.append(f'<line x1="32" y1="{H - 62}" x2="928" y2="{H - 62}" stroke="{{grid}}"/>')
    o.append(text(32, H - 40, "Real training: lerobot-train uses shards = num_workers, and the default cache holds "
                  "100 decoders.", 13, fill="ink2"))
    o.append(text(32, H - 20, "So separate files overflow at about 34 workers. Stacked overflows at about 100. "
                  "The test above (cache 12) has the same hit rate as 64 workers.", 13, fill="ink2"))
    return page(W, H, "".join(o), theme, title="Decoder cache overflow",
                desc="With 24 files in use and a cache of 12, separate files hit the cache half the time and "
                     "make 4.6 frames/s. Stacked uses 8 files, all fit, 308 frames/s.")


# ---------------------------------------------------------------- 5. results


# (label, unit, separate mean, ci, stacked mean, ci, verdict). Sources: README table,
# results/round2/summary.md (streaming, 8 readers) and results/round3/summary.md (#3917, equal size).
RESULTS = [
    ("Streaming, 1 process", "frames/s", 182, 30, 342, 17, "1.9x"),
    ("Streaming, cache too small", "frames/s", 4.6, 1.5, 308, 81, "67x"),
    ("Whole episodes (#3917), 1 process", "samples/s", 138, 80, 212, 38, "1.5x"),
    ("Whole episodes (#3917), 8 processes", "samples/s", 1320, 240, 1900, 521, "1.4x"),
    ("Random access, 1 reader, same file size", "samples/s", 7.7, 5.1, 7.3, 3.4, "same"),
    ("Random access, 8 readers", "samples/s, 1 run", 73, None, 108, None, "1.5x"),
]


def fmt(v):
    return f"{v:g}" if v < 100 else f"{v:,.0f}"


def results(theme):
    W = 960
    RH = 70
    top = 112
    H = top + RH * len(RESULTS) + 44
    o = [header("Results: stacked vs separate files",
                "Mean of 3 runs. Whiskers show the 95% interval. Each row has its own scale.")]
    lx = 640
    o.append(rect(lx, 30, 12, 12, fill="{sep}", rx=3) + text(lx + 18, 40, "Separate files", 13, fill="ink2"))
    o.append(rect(lx + 130, 30, 12, 12, fill="{stack}", rx=3) + text(lx + 148, 40, "Stacked", 13, fill="ink2"))
    o.append(text(928, top - 12, "Stacked is", 12, fill="muted", anchor="end"))
    BX0, BX1 = 372, 770
    for i, (label, unit, sm, sc, km, kc, verdict) in enumerate(RESULTS):
        y = top + i * RH
        o.append(f'<line x1="32" y1="{y}" x2="928" y2="{y}" stroke="{{grid}}"/>')
        o.append(text(32, y + 30, label, 14, weight=600))
        o.append(text(32, y + 50, unit, 13, fill="muted"))
        vmax = max(sm + (sc or 0), km + (kc or 0))
        sx = (BX1 - BX0) / vmax
        o.append(f'<line x1="{BX0}" y1="{y + 12}" x2="{BX0}" y2="{y + 58}" stroke="{{axis}}"/>')
        for j, (m, c, col) in enumerate([(sm, sc, "{sep}"), (km, kc, "{stack}")]):
            by = y + 14 + j * 22
            o.append(bar_h(BX0, by, m * sx, 18, col))
            end = BX0 + m * sx
            if c:
                a, b = BX0 + max(m - c, 0) * sx, BX0 + (m + c) * sx
                o.append(f'<g stroke="{{ink2}}" stroke-width="1.5"><line x1="{a:.1f}" y1="{by + 9}" '
                         f'x2="{b:.1f}" y2="{by + 9}"/><line x1="{a:.1f}" y1="{by + 4}" x2="{a:.1f}" '
                         f'y2="{by + 14}"/><line x1="{b:.1f}" y1="{by + 4}" x2="{b:.1f}" y2="{by + 14}"/></g>')
                end = max(end, b)
            lab = fmt(m) + (f" ± {fmt(c)}" if c else "")
            o.append(text(end + 8, by + 14, lab, 12.5, fill="ink2"))
        o.append(text(928, y + 42, verdict, 18, weight=700, anchor="end"))
    o.append(f'<line x1="32" y1="{top + RH * len(RESULTS)}" x2="928" y2="{top + RH * len(RESULTS)}" '
             f'stroke="{{grid}}"/>')
    o.append(text(32, H - 18, "Hugging Face Jobs, cpu-upgrade (8 CPUs), reads over hf://. Dataset: "
                  "lerobot/abc_130k_v3_train, 3 cameras.", 12.5, fill="muted"))
    return page(W, H, "".join(o), theme, title="Results: stacked vs separate files",
                desc="; ".join(f"{r[0]}: separate {fmt(r[2])}, stacked {fmt(r[4])} {r[1]} ({r[6]})"
                               for r in RESULTS))


# ---------------------------------------------------------------- 6. camera views


def views(theme):
    import base64
    import json

    vd = OUT / "views"
    info = json.loads((vd / "views.json").read_text())

    def img(name, x, y, w, h):
        data = base64.b64encode((vd / name).read_bytes()).decode()
        return (f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="none" '
                f'href="data:image/jpeg;base64,{data}"/>')

    S, GAP = 180, 20
    W, top = 960, 124
    H = top + 3 * S + 2 * GAP + 78
    bw, bh = info["size_before"]
    aw, ah = info["size_after"]
    o = [header("What the camera views look like, before and after",
                f"One real frame (number {info['frame']:,}), decoded from the public test videos.")]
    # before
    LX = 32
    o.append(text(LX, top - 16, "Before: 3 files, 3 decoders", 15, weight=650))
    for k, cam in enumerate(CAMS):
        y = top + k * (S + GAP)
        o.append(img(f"before_{cam.replace(' ', '_')}.jpg", LX, y, S, S))
        o.append(rect(LX, y, S, S, fill="none", stroke=f"{{cam{k}}}", rx=0, sw=3))
        o.append(rect(LX + S + 14, y + S / 2 - 22, 12, 12, fill=f"{{cam{k}}}", rx=3))
        o.append(text(LX + S + 32, y + S / 2 - 12, cam, 14, weight=600))
        o.append(text(LX + S + 14, y + S / 2 + 8, "its own MP4 file", 13, fill="ink2"))
        o.append(text(LX + S + 14, y + S / 2 + 26, f"{bw} x {bh} pixels", 13, fill="muted"))
    # arrow
    mid = top + (3 * S + 2 * GAP) / 2
    o.append(arrow(372, mid, 452, mid, color="{ink2}", sw=2))
    o.append(text(412, mid - 30, "re-encode,", 13, fill="ink2", anchor="middle"))
    o.append(text(412, mid - 13, "stack", 13, fill="ink2", anchor="middle"))
    # after
    RX = 476
    th = 3 * S + 2 * GAP
    o.append(text(RX, top - 16, "After: 1 file, 1 decoder", 15, weight=650))
    o.append(img("after_stacked.jpg", RX, top, S, th))
    o.append(rect(RX, top, S, th, fill="none", stroke="{stack}", rx=0, sw=3))
    third = th / 3
    ps = info["psnr_db"]
    for k, cam in enumerate(CAMS):
        y0 = top + k * third
        if k:
            o.append(f'<line x1="{RX - 8}" y1="{y0:.1f}" x2="{RX + S + 8}" y2="{y0:.1f}" stroke="{{ink}}" '
                     f'stroke-width="1.5" stroke-dasharray="5 4"/>')
        bx = RX + S + 16
        o.append(f'<path d="M{bx},{y0 + 6:.1f} h6 V{y0 + third - 6:.1f} h-6" fill="none" stroke="{{cam{k}}}" '
                 f'stroke-width="2.5"/>')
        cy = y0 + third / 2
        o.append(text(bx + 18, cy - 12, cam, 14, weight=600))
        o.append(text(bx + 18, cy + 8, f"rows {k * bh} to {(k + 1) * bh - 1}", 13, fill="ink2"))
        o.append(text(bx + 18, cy + 26, f"{ps[cam.replace(' ', '_')]} dB vs before (PSNR)", 13, fill="muted"))
    o.append(text(RX, top + th + 24, f"{aw} x {ah} pixels. The reader cuts it at the dashed lines.",
                  13, fill="ink2"))
    o.append(text(32, H - 18, "The black bands are in the source dataset (lerobot/abc_130k_v3_train). "
                  "Frames shown at 180 px; the videos are 224 px wide.", 12.5, fill="muted"))
    return page(W, H, "".join(o), theme, title="Camera views before and after stacking",
                desc="Before: 3 separate 224 x 224 images (top, left wrist, right wrist), one file each. "
                     "After: one 224 x 672 image with the 3 views stacked, which the reader cuts back into 3.")


if __name__ == "__main__":
    save("loading", loading)
    save("layouts", layouts)
    save("read-modes", read_modes)
    save("cache", cache)
    save("results", results)
    save("views", views)
    print("wrote", sorted(p.name for p in OUT.glob("*.svg")))
