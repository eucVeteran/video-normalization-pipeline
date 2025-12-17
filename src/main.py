import subprocess
import json
import os
import sys
import argparse
from pathlib import Path


def get_video_info(file_path):
    """
    Uses ffprobe to extract color metadata from the video stream.
    Returns a dictionary with color_transfer, color_space, and color_primaries.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=color_transfer,color_space,color_primaries,pix_fmt",
        "-of", "json",
        file_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                check=True)
        data = json.loads(result.stdout)
        stream_info = data.get("streams", [])[0]
        return stream_info
    except Exception as e:
        print(f"Error probing file {file_path}: {e}")
        sys.exit(1)


def is_hdr(transfer, color_space, primaries, pix_fmt):
    hdr_like_colors = ("bt2020" in primaries) or ("bt2020" in color_space)
    hdr_like_bitdepth = pix_fmt in {
        "p010le", "p016le",
        "yuv420p10le", "yuv422p10le", "yuv444p10le",
        "yuv420p12le", "yuv422p12le", "yuv444p12le",
    } or ("10le" in pix_fmt) or ("12le" in pix_fmt)

    return (transfer not in {"arib-std-b67", "smpte2084"}) \
        and (hdr_like_colors or hdr_like_bitdepth)


def build_ffmpeg_command(input_path, output_path):
    """
    Generates the correct FFmpeg command based on the input file's
        color characteristics.
    Target: Rec.709 SDR, yuv420p pixel format, h.264 codec.
    Uses 'zscale' filter (zimg library) for high-quality tone mapping.
    """
    info = get_video_info(input_path)
    transfer = info.get("color_transfer", "unknown")
    print(f"Detected Transfer Function: {transfer}")

    color_space = (info.get("color_space") or "").lower()
    primaries = (info.get("color_primaries") or "").lower()
    pix_fmt = (info.get("pix_fmt") or "").lower()
    is_probably_hdr = is_hdr(transfer, color_space, primaries, pix_fmt)

    if transfer == "arib-std-b67":
        print("-> Type: HDR (HLG). Applying HLG to SDR tone mapping (Hable).")
        # HLG Strategy via zscale:
        # 1. zscale: Transfer HLG -> Linear (Linearize)
        # 2. format: Convert to 32-bit float for precision
        # 3. zscale: Primaries BT2020 -> BT709 (Gamut Mapping)
        # 4. tonemap: Hable algorithm (Compress dynamic range)
        # 5. zscale: Transfer Linear -> BT709 (Gamma Correction) & Matrix BT709
        filter_chain = (
            "zscale=t=linear:npl=100,format=gbrpf32le,"
            "zscale=p=bt709,"
            "tonemap=tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
        )

    elif transfer == "smpte2084":
        print("-> Type: HDR (PQ). Applying PQ to SDR tone mapping (Hable).")
        # PQ Strategy via zscale:
        # Similar to HLG, but input transfer is different.
        filter_chain = (
            "format=p010le,"
            "zscale=t=linear:npl=100,format=gbrpf32le,"
            "zscale=p=bt709,"
            "tonemap=tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
        )

    elif is_probably_hdr:
        # Fallback: looks like HDR (BT.2020 and/or 10-bit),
        #   but transfer is missing/unknown.
        # We choose a deterministic fallback tone-map path (PQ-like)
        #   instead of treating it as SDR.
        print("⚠️ Transfer is not HLG/PQ, but stream looks HDR\
            (BT.2020 and/or 10-bit). Using HDR->SDR fallback tonemap.")
        filter_chain = (
            "format=p010le,"
            "zscale=t=linear:npl=100,format=gbrpf32le,"
            "zscale=p=bt709,"
            "tonemap=tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
        )

    else:
        print("-> Type: SDR. Applying normalization only.")
        filter_chain = "colorspace=all=bt709:trc=bt709:format=yuv420p"

    # full ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",               # Overwrite output
        "-i", input_path,   # Input
        "-vf", filter_chain,  # Video Filters
        "-c:v", "libx264",  # Video Codec
        "-preset", "slow",  # Quality preset
        "-crf", "23",       # Constant Rate Factor (Quality)
        "-c:a", "copy",     # Copy audio
        output_path
    ]

    return cmd


def process_single_file(input_path, output_path):
    """Wrapper to process a single file with error handling."""
    if not os.path.exists(input_path):
        print(f"Error: Input {input_path} not found.")
        return

    print(f"Processing: {input_path} -> {output_path}")

    cmd = build_ffmpeg_command(input_path, output_path)

    try:
        subprocess.run(cmd,
                       check=True,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE)
        print(f"✅ Done: {os.path.basename(output_path)}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error encoding {input_path}: {e.stderr.decode()}")


def main():
    parser = argparse.ArgumentParser(description="Normalize video(s) \
                                     to Rec.709 SDR.")
    parser.add_argument("input", help="Input file OR directory")
    parser.add_argument("output", help="Output file OR directory")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Directory Batch Processing
    if input_path.is_dir():
        if not output_path.exists():
            os.makedirs(output_path)

        print(f"📁 Batch mode detected. Scanning {input_path}...")

        supported_ext = {'.mp4', '.mov', '.mkv', '.avi'}
        files = [f for f in input_path.iterdir()
                 if f.suffix.lower() in supported_ext]

        if not files:
            print("No video files found in input directory.")
            return

        for video_file in files:
            # Create output filename: "hdr.mp4" -> "outputs/hdr_normalized.mp4"
            new_filename = video_file.stem + "_normalized" + video_file.suffix
            destination = output_path / new_filename
            process_single_file(str(video_file), str(destination))

    # Single File Processing
    elif input_path.is_file():
        if output_path.parent.name and not output_path.parent.exists():
            os.makedirs(output_path.parent)
        process_single_file(str(input_path), str(output_path))

    else:
        print("Error: Input path is invalid.")
        sys.exit(1)


if __name__ == "__main__":
    main()
