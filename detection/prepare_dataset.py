"""Convert labelme JSON annotations to YOLO format and split into train/val sets.

Reads labelme rectangle annotations from a data directory, converts bounding
boxes to YOLO normalized format (class_id x_center y_center width height),
and creates a train/val split with corresponding image copies.

Expected input layout (see README.md for how the published model's dataset
was organized):
    <data-dir>/
      images_jpg/
        *.jpg           (one image per annotation)
      *.json            (labelme annotation, same stem as the image)

Directory structure created:
    <out>/
      train/
        images/   (JPG copies)
        labels/   (YOLO .txt files)
      val/
        images/
        labels/

Usage:
    python prepare_dataset.py --data-dir data --out dataset --train-ratio 0.8 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

CLASS_MAP: dict[str, int] = {
    "electric_pipette": 0,
}


# ── Conversion Logic ──────────────────────────────────────────────────────


def labelme_to_yolo_bbox(
    points: list[list[float]],
    img_width: int,
    img_height: int,
) -> tuple[float, float, float, float]:
    """Convert labelme rectangle points to YOLO normalized format.

    Labelme stores rectangles as two corner points [[x1,y1],[x2,y2]].
    The points are NOT guaranteed to be top-left and bottom-right,
    so we use min/max to handle any ordering.

    Returns:
        (x_center, y_center, width, height) all normalized to [0, 1].
    """
    x1, y1 = points[0]
    x2, y2 = points[1]

    # Ensure correct min/max regardless of point ordering
    x_min = min(x1, x2)
    x_max = max(x1, x2)
    y_min = min(y1, y2)
    y_max = max(y1, y2)

    # Clamp to image boundaries
    x_min = max(0.0, x_min)
    y_min = max(0.0, y_min)
    x_max = min(float(img_width), x_max)
    y_max = min(float(img_height), y_max)

    # Compute center and dimensions, then normalize
    x_center = (x_min + x_max) / 2.0 / img_width
    y_center = (y_min + y_max) / 2.0 / img_height
    bbox_width = (x_max - x_min) / img_width
    bbox_height = (y_max - y_min) / img_height

    return x_center, y_center, bbox_width, bbox_height


def convert_json_to_yolo(json_path: Path) -> list[str]:
    """Parse a single labelme JSON and return YOLO-format annotation lines.

    Each line: "class_id x_center y_center width height"
    with 6-decimal precision for normalized coordinates.
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    img_width = data["imageWidth"]
    img_height = data["imageHeight"]
    lines: list[str] = []

    for shape in data["shapes"]:
        if shape["shape_type"] != "rectangle":
            print(f"  WARNING: Skipping non-rectangle shape in {json_path.name}")
            continue

        label = shape["label"]
        if label not in CLASS_MAP:
            print(f"  WARNING: Unknown label '{label}' in {json_path.name}, skipping")
            continue

        class_id = CLASS_MAP[label]
        x_c, y_c, w, h = labelme_to_yolo_bbox(shape["points"], img_width, img_height)
        lines.append(f"{class_id} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")

    return lines


# ── Dataset Preparation ───────────────────────────────────────────────────


def prepare_dataset(data_dir: Path, out_dir: Path, train_ratio: float, seed: int) -> None:
    """Main pipeline: convert annotations, split, and organize into out_dir."""
    images_dir = data_dir / "images_jpg"

    # Collect JSON/image pairs from the data directory.
    valid_pairs: list[tuple[Path, Path]] = []

    json_files = sorted(data_dir.glob("*.json"))
    print(f"Found {len(json_files)} annotation files in {data_dir}/")
    for json_path in json_files:
        stem = json_path.stem
        img_path = images_dir / f"{stem}.jpg"
        if not img_path.exists():
            print(f"  WARNING: No matching image for {json_path.name}, skipping")
            continue
        valid_pairs.append((json_path, img_path))

    if not valid_pairs:
        print("ERROR: No valid JSON/image pairs found")
        return

    print(f"Validated {len(valid_pairs)} total JSON/image pairs")

    # Shuffle and split
    random.seed(seed)
    random.shuffle(valid_pairs)

    split_idx = int(len(valid_pairs) * train_ratio)
    train_pairs = valid_pairs[:split_idx]
    val_pairs = valid_pairs[split_idx:]

    print(f"Split: {len(train_pairs)} train / {len(val_pairs)} val")

    # Create output directory structure (clean start)
    if out_dir.exists():
        shutil.rmtree(out_dir)
        print(f"Removed existing {out_dir}")

    for split_name in ("train", "val"):
        (out_dir / split_name / "images").mkdir(parents=True)
        (out_dir / split_name / "labels").mkdir(parents=True)

    # Process each split
    stats = {"train": {"images": 0, "annotations": 0}, "val": {"images": 0, "annotations": 0}}

    for split_name, pairs in [("train", train_pairs), ("val", val_pairs)]:
        for json_path, img_path in pairs:
            stem = json_path.stem

            # Convert annotation
            yolo_lines = convert_json_to_yolo(json_path)
            if not yolo_lines:
                print(f"  WARNING: No valid annotations in {json_path.name}, skipping")
                continue

            # Write YOLO label file
            label_path = out_dir / split_name / "labels" / f"{stem}.txt"
            label_path.write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")

            # Copy image
            dst_img = out_dir / split_name / "images" / f"{stem}.jpg"
            shutil.copy2(img_path, dst_img)

            stats[split_name]["images"] += 1
            stats[split_name]["annotations"] += len(yolo_lines)

    # Summary
    print("\n" + "=" * 50)
    print("Dataset preparation complete")
    print("=" * 50)
    print(f"  Train: {stats['train']['images']} images, {stats['train']['annotations']} annotations")
    print(f"  Val:   {stats['val']['images']} images, {stats['val']['annotations']} annotations")
    print(f"  Output: {out_dir}")

    # Quick sanity check: print first label file content
    first_label = next((out_dir / "train" / "labels").glob("*.txt"), None)
    if first_label:
        print(f"\nSample label ({first_label.name}):")
        print(f"  {first_label.read_text().strip()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=SCRIPT_DIR / "data",
        help="Directory containing labelme *.json files and an images_jpg/ subfolder (default: data)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=SCRIPT_DIR / "dataset",
        help="Output directory for the YOLO-format dataset (default: dataset)",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.80,
        help="Fraction of samples assigned to the training split (default: 0.80)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used to shuffle before splitting (default: 42)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    prepare_dataset(args.data_dir, args.out, args.train_ratio, args.seed)
