"""Run offline object detection on a recorded video (or image) and save results.

This is the offline analysis step described in the paper: the overhead
camera recording of an automated experiment is processed after the fact
with a fine-tuned YOLOv8 model. It is NOT integrated into the live
experiment log.

In addition to Ultralytics' own annotated-video/image output, this script
writes a per-frame CSV (`<run dir>/detections.csv`) with columns
`frame, n_detections, max_conf` so detections can be joined to sensor logs
by frame index / time (frame_index / fps -> elapsed seconds).

Usage:
    python infer_video.py --model weights/best.pt --source video.mp4
    python infer_video.py --model runs/electric_pipette/weights/best.pt \
        --source video.mp4 --conf 0.25 --imgsz 960 --device auto \
        --project runs --name video_result
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ultralytics import YOLO

SCRIPT_DIR = Path(__file__).resolve().parent


def find_latest_best_model(project: Path) -> Path:
    """Find the most recently created best.pt under project/*/weights/."""
    candidates = sorted(project.glob("*/weights/best.pt"))
    if not candidates:
        raise FileNotFoundError(f"No best.pt found in {project}/*/weights/")
    return candidates[-1]


def infer_video(
    model_path: Path,
    source: Path,
    conf: float,
    imgsz: int,
    device: str | None,
    project: Path,
    name: str,
) -> None:
    print(f"Model:  {model_path}")
    print(f"Source: {source}")

    model = YOLO(str(model_path))

    results = model.predict(
        source=str(source),
        save=True,
        project=str(project),
        name=name,
        conf=conf,
        imgsz=imgsz,
        device=device,
    )

    save_dir = Path(results[0].save_dir) if results else project / name

    # Per-frame CSV for joining detections to sensor logs by frame index / time.
    csv_path = save_dir / "detections.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "n_detections", "max_conf"])
        for frame_idx, r in enumerate(results):
            n_det = len(r.boxes)
            max_conf = float(r.boxes.conf.max()) if n_det > 0 else 0.0
            writer.writerow([frame_idx, n_det, f"{max_conf:.4f}"])

    # Summary
    total_detections = sum(len(r.boxes) for r in results)
    frames_with_detections = sum(1 for r in results if len(r.boxes) > 0)
    total_frames = len(results)

    print("\nResults:")
    print(f"  Total frames: {total_frames}")
    if total_frames > 0:
        print(f"  Frames with detections: {frames_with_detections} ({frames_with_detections / total_frames * 100:.1f}%)")
    print(f"  Total detections: {total_detections}")
    print(f"  Per-frame CSV: {csv_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--model",
        type=Path,
        default=None,
        help="Path to trained weights (e.g. weights/best.pt). "
        "If omitted, the most recent runs/*/weights/best.pt is used.",
    )
    parser.add_argument("--source", type=Path, required=True, help="Path to the input video or image")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25)")
    parser.add_argument("--imgsz", type=int, default=960, help="Inference image size (default: 960)")
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Device to run inference on: 'auto' lets Ultralytics choose, or specify 'mps', 'cuda', 'cuda:0', 'cpu', etc. (default: auto)",
    )
    parser.add_argument(
        "--project", type=Path, default=SCRIPT_DIR / "runs", help="Directory under which run folders are created (default: runs)"
    )
    parser.add_argument("--name", type=str, default="video_result", help="Run name (default: video_result)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    model_path = args.model if args.model else find_latest_best_model(args.project)
    device = None if args.device == "auto" else args.device

    infer_video(
        model_path=model_path,
        source=args.source,
        conf=args.conf,
        imgsz=args.imgsz,
        device=device,
        project=args.project,
        name=args.name,
    )
