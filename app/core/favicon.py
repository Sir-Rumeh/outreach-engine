import os
import zlib
import struct

def create_png_data(size: int = 32) -> bytes:
    """Generates valid 32x32 RGBA PNG icon matching Outreach Engine branding."""
    width = size
    height = size
    center = (size - 1) / 2.0
    r_outer = size * 0.35
    r_inner = size * 0.22
    corner_r = size * 0.25

    pixels = []
    for y in range(height):
        row = [0]  # filter byte 0 (None)
        for x in range(width):
            # Squircle rounded rect check
            dx = max(0.0, abs(x - center) - (size * 0.5 - corner_r))
            dy = max(0.0, abs(y - center) - (size * 0.5 - corner_r))
            if dx * dx + dy * dy > corner_r * corner_r:
                row.extend([0, 0, 0, 0])
                continue

            cdx = x - center
            cdy = y - center
            dist_center = (cdx * cdx + cdy * cdy) ** 0.5

            # Jet / Arrow inside check
            nx = x / float(size)
            ny = y / float(size)
            in_arrow = False
            if 0.38 <= nx <= 0.68 and 0.30 <= ny <= 0.70:
                slope = (ny - 0.5) / 0.20
                max_x = 0.68 - abs(slope) * 0.26
                min_x = 0.40 + (1.0 - abs(slope)) * 0.06
                if min_x <= nx <= max_x:
                    in_arrow = True

            if in_arrow:
                # Bright accent / white
                row.extend([255, 255, 255, 255])
            elif r_inner <= dist_center <= r_outer:
                # White 'O' ring
                row.extend([255, 255, 255, 255])
            else:
                # Royal blue gradient (#2563EB to #1D4ED8)
                factor = (x + y) / float(width + height)
                r_col = int(37 * (1.0 - factor) + 29 * factor)
                g_col = int(99 * (1.0 - factor) + 78 * factor)
                b_col = int(235 * (1.0 - factor) + 216 * factor)
                row.extend([r_col, g_col, b_col, 255])
        pixels.append(bytes(row))

    raw_data = b"".join(pixels)
    compressed = zlib.compress(raw_data, level=9)

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    png_header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    idat = chunk(b"IDAT", compressed)
    iend = chunk(b"IEND", b"")
    return png_header + ihdr + idat + iend


def create_ico_data(png_bytes: bytes) -> bytes:
    """Wraps PNG byte stream into standard Windows .ico container."""
    # ICO Header: Reserved (0), Type (1 = ICO), Image Count (1)
    header = struct.pack("<HHH", 0, 1, 1)
    # Entry: Width, Height, Colors, Reserved, Planes, BPP, Size, Offset
    entry = struct.pack("<BBBBHHII", 32, 32, 0, 0, 1, 32, len(png_bytes), 22)
    return header + entry + png_bytes


def ensure_favicon_assets(static_dir: str):
    """Ensures favicon.ico and favicon.png exist in static_dir."""
    try:
        os.makedirs(static_dir, exist_ok=True)
        ico_path = os.path.join(static_dir, "favicon.ico")
        png_path = os.path.join(static_dir, "favicon.png")

        if not os.path.exists(ico_path) or not os.path.exists(png_path):
            png_bytes = create_png_data(32)
            ico_bytes = create_ico_data(png_bytes)

            if not os.path.exists(ico_path):
                with open(ico_path, "wb") as f:
                    f.write(ico_bytes)

            if not os.path.exists(png_path):
                with open(png_path, "wb") as f:
                    f.write(png_bytes)
    except Exception as e:
        # Graceful fallback; app won't crash if filesystem permissions restrict writing
        print(f"Favicon asset generation notice: {e}")

