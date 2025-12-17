# Video Normalization Pipeline
A robust automated pipeline designed to normalize mixed video inputs (SDR, HDR HLG, HDR PQ) into a unified **Rec.709 SDR** standard.

This solution ensures technical consistency (same codec, pixel format, and color space) across all clips, making them ready for artifact-free concatenation in downstream editing workflows.

## 🚀 Quick Start
The project is fully automated using a `Makefile`.

1.  **Prepare Inputs:** Place your video files (e.g., `hdr.mp4`, `sdr.mp4`) into the `inputs/` directory.
2.  **Run Pipeline:** Execute the following command in your terminal:

    ```bash
    make
    ```

    *This command will set up a virtual environment, install dependencies (if any), detect input formats, process the videos, and save the results to `outputs/`.*

3.  **Verify Results:** To run the automated metadata validation script:

    ```bash
    make verify
    ```

4. **Cleaning** To clean up the mess, just use(Be careful, it will clean output directory too):

    ```bash
    make clean
    ```

## 🛠 Technical Approach
### 1. Format Detection Logic
The pipeline uses `ffprobe` to inspect the `color_transfer` metadata of the input stream to reliably distinguish between formats:
- **ARIB STD-B67**: Identified as **HLG** (Hybrid Log-Gamma).
- **SMPTE ST 2084**: Identified as **PQ** (Perceptual Quantizer).
- **BT.709 / Unspecified**: Treated as **SDR**.

### 2. HDR to SDR Tone Mapping Strategy
The core challenge is converting High Dynamic Range (Rec.2020) to Standard Dynamic Range (Rec.709) without losing detail in highlights (clipping) or crushing shadows.

I utilized the **`zscale` filter (zimg library)**, employing the **Hable** tone-mapping algorithm.

**Filter Chain Logic:**
1.  **Linearization:** Convert input (HLG/PQ) to linear light.
2.  **Gamut Mapping:** Convert color primaries from BT.2020 to BT.709.
3.  **Tone Mapping (Hable):** Compress the high dynamic range luminance into the SDR range.
    * *Why Hable?* Unlike simple clipping, the Hable algorithm preserves details in bright areas (e.g., clouds, lights) while maintaining natural contrast.
4.  **Gamma Correction:** Encode the signal back to the BT.709 transfer function.

### 3. Normalization & Concatenation Readiness
FFmpeg's `concat` demuxer requires strict uniformity. To prevent concatenation artifacts, the pipeline enforces the following parameters for **all** outputs (even if the input was already SDR):
- **Pixel Format:** `yuv420p` (8-bit, widely compatible).
- **Color Space/Transfer/Primaries:** Explicitly flagged as `bt709`.
- **Codec:** H.264 (High Profile, CRF 23).

## 📊 Visual Analysis & Verification
### Technical Verification
The `make verify` command ensures that all output files strictly adhere to the target standards:
- `pix_fmt`: yuv420p
- `color_space`: bt709
- `color_transfer`: bt709

### Visual Comparison (Reference vs. Output)
Comparing the generated output (`hdr_normalized.mp4`) with the provided reference (`sdr.mp4`):

1.  **Dynamic Range:** The pipeline successfully prevents clipping. Details in the sky and clouds are preserved and match the exposure of the reference file.
2.  **Color Saturation:** A slight difference in skin tone saturation is observable (the output is slightly less saturated than the reference).
    * *Analysis:* This is a characteristic of the **Hable** tone-mapping operator, which prioritizes luminance preservation in highlights over chrominance saturation in mid-tones.
    * *Decision:* I retained the Hable algorithm because it offers the most robust protection against "blown-out" highlights for unknown/dynamic input sources, which is critical for an automated pipeline where manual color grading is not possible.

## 📂 Project Structure
```text
.
├── inputs/             # Place raw video files here
├── outputs/            # Processed Rec.709 SDR videos appear here
├── src/
│   ├── main.py         # Core logic: Detection and FFMPEG wrapper
│   └── verify.py       # QA script for metadata validation
├── Makefile            # Automation for setup, run, and verify
└── README.md           # Documentation
```

## ⚠️ Note on Stream Selection (v:0)
The pipeline detects metadata and processes only the first video stream (v:0).
If a file contains multiple video streams and v:0 is a preview/aux stream instead of the main video, results may be incorrect.

In practice, v:0 is the main video in ~99% of real-world files, so we keep this assumption to stay fully automated and simple.

## Requirements
- Python 3.8+
- FFmpeg 5.x+ (Must be compiled with --enable-libzimg for zscale support).

Note: The script detects the arib-std-b67 transfer characteristic correctly and applies the appropriate HLG transformation chain.