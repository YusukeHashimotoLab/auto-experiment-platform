"""Fine-tune YOLOv8 for electric-pipette detection.

Trains from a pretrained YOLOv8 checkpoint (default: yolov8n.pt) on a
dataset prepared by prepare_dataset.py. The default hyperparameters match
the configuration used for the published model (run "electric_pipette2"
in the paper's working repository): imgsz 1280, batch 4, 100 epochs,
patience 50, cosine LR schedule, mosaic augmentation disabled for the
final 10 epochs (close_mosaic).

Usage:
    python train.py
    python train.py --data data.yaml --model yolov8n.pt --epochs 100 \
        --imgsz 1280 --batch 4 --patience 50 --device auto \
        --name electric_pipette --project runs
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

SCRIPT_DIR = Path(__file__).resolve().parent


def train(
    data_yaml: Path,
    model_weights: str,
    epochs: int,
    imgsz: int,
    batch: int,
    patience: int,
    device: str | None,
    project: Path,
    name: str,
) -> None:
    """Fine-tune a YOLOv8 model on the given dataset."""
    print(f"Base model: {model_weights}")
    model = YOLO(model_weights)

    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        patience=patience,
        project=str(project),
        name=name,
        cos_lr=True,
        close_mosaic=10,
    )

    save_dir = Path(results.save_dir)
    print("\n" + "=" * 50)
    print("Training complete")
    print("=" * 50)
    print(f"  Results saved to: {save_dir}")
    print(f"  Best weights:     {save_dir / 'weights' / 'best.pt'}")
    print(f"  Last weights:     {save_dir / 'weights' / 'last.pt'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--data",
        type=Path,
        default=SCRIPT_DIR / "data.yaml",
        help="Path to the Ultralytics dataset config (default: data.yaml; see data.example.yaml)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        help="Base checkpoint to fine-tune from: an Ultralytics pretrained name "
        "(auto-downloaded) or a path to local weights (default: yolov8n.pt)",
    )
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs (default: 100)")
    parser.add_argument("--imgsz", type=int, default=1280, help="Training image size (default: 1280)")
    parser.add_argument("--batch", type=int, default=4, help="Batch size (default: 4)")
    parser.add_argument(
        "--patience", type=int, default=50, help="Epochs to wait for no observable improvement before early stopping (default: 50)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Device to train on: 'auto' lets Ultralytics choose, or specify 'mps', 'cuda', 'cuda:0', 'cpu', etc. (default: auto)",
    )
    parser.add_argument(
        "--project", type=Path, default=SCRIPT_DIR / "runs", help="Directory under which run folders are created (default: runs)"
    )
    parser.add_argument("--name", type=str, default="electric_pipette", help="Run name (default: electric_pipette)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    # "auto" means let Ultralytics pick the best available device (mps/cuda/cpu).
    device = None if args.device == "auto" else args.device
    train(
        data_yaml=args.data,
        model_weights=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        device=device,
        project=args.project,
        name=args.name,
    )
