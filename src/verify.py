import subprocess
import json
import sys
import os
from glob import glob


def get_metadata(file_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=pix_fmt,color_space,color_primaries,color_transfer",
        "-of", "json",
        file_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    return json.loads(result.stdout)["streams"][0]


def check_file(file_path):
    # filename only to keep output readable
    print(f"🔍 Verifying: {os.path.basename(file_path)}...", end=" ")

    try:
        data = get_metadata(file_path)
    except Exception as e:
        print(f"❌ ERROR: Could not read metadata. {e}")
        return False

    # expected Rec.709 SDR video characteristics
    expected = {
        "pix_fmt": "yuv420p",
        "color_space": "bt709",
        "color_primaries": "bt709",
        "color_transfer": "bt709"
    }

    errors = []
    for key, expected_value in expected.items():
        actual_value = data.get(key, "unknown")
        if actual_value != expected_value:
            errors.append(
                f"{key}: expected '{expected_value}', got '{actual_value}'"
            )

    if not errors:
        print("✅ PASS")
        return True
    else:
        print("❌ FAIL")
        for err in errors:
            print(f"   - {err}")
        return False


def main():
    files = glob("outputs/*_normalized.mp4")
    if not files:
        print("No output files found to verify.")
        sys.exit(1)

    all_passed = True
    for file_path in files:
        if not check_file(file_path):
            all_passed = False

    if all_passed:
        print("\n✨ All files match Rec.709 SDR standards!")
        sys.exit(0)
    else:
        print("\n⚠️ Some files failed verification.")
        sys.exit(1)


if __name__ == "__main__":
    main()
