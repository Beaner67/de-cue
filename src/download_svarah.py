"""
download_svarah.py

Extracts the downloaded Svarah audio parquet files from the Hugging Face cache
and saves the genuine .wav files directly into SVARAH_DIR (E:/Yoihenba/Thesis project/DATAS/svarah).
"""

from pathlib import Path
import pyarrow.parquet as pq

from paths_config import SVARAH_DIR


def main():
    out_dir = Path(SVARAH_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Locate the cached parquet files downloaded from Hugging Face
    cache_root = Path.home() / ".cache" / "huggingface" / "hub"
    parquet_files = sorted(cache_root.rglob("*Svarah*/**/*.parquet"))

    if not parquet_files:
        print("No cached Svarah parquet files found in Hugging Face cache.")
        return

    print(f"Found {len(parquet_files)} cached Svarah parquet files.")
    print(f"Exporting WAV files directly to: {out_dir}")

    total_exported = 0

    for p_idx, p_file in enumerate(parquet_files, start=1):
        print(f"\nProcessing parquet file {p_idx}/{len(parquet_files)}: {p_file.name}")
        table = pq.read_table(p_file)
        audio_col = table["audio_filepath"]
        num_rows = len(table)

        for i in range(num_rows):
            item = audio_col[i].as_py()
            if not item or "bytes" not in item or not item["bytes"]:
                continue

            file_name = item.get("path") or f"svarah_{total_exported:05d}.wav"
            # Ensure it ends with .wav
            if not file_name.lower().endswith(".wav"):
                file_name += ".wav"

            # Clean filename if it has directory slashes
            file_name = Path(file_name).name

            target_path = out_dir / file_name
            if not target_path.exists():
                with open(target_path, "wb") as f:
                    f.write(item["bytes"])

            total_exported += 1
            if total_exported % 500 == 0:
                print(f"  Exported {total_exported} WAV files...")

    print(f"\n[DONE] Successfully extracted {total_exported} WAV audio files into {out_dir}!")


if __name__ == "__main__":
    main()
