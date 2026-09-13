# Object detection module (YOLOv8)

Optional monitoring feature: detects the electric pipettes (mounted on the robot arms)
in the recorded overhead-camera video, as an offline analysis of the experimental state.

## License notice

This module depends on [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics),
which is licensed under **AGPL-3.0**. To keep the rest of the platform under the MIT
license, this module is isolated here and is distributed under **AGPL-3.0**. The
platform runs without this module; only the camera-based object detection is disabled.

The full license text is in [`LICENSE`](LICENSE) in this directory (a verbatim copy of
<https://www.gnu.org/licenses/agpl-3.0.txt>) and applies to **everything under
`detection/` only**. The rest of this repository is MIT (code, see the top-level
[`LICENSE`](../LICENSE)) and CC BY 4.0 (documentation and CAD), and imports nothing
from `ultralytics` — verify with:

```bash
grep -rn "ultralytics" src examples   # no matches
```

Because `ultralytics` is imported only by the files in this directory, the AGPL's
copyleft does not reach the rest of the platform. If you redistribute or offer network
access to a modified version of *this module*, AGPL-3.0 §13 requires you to offer the
corresponding source. See also [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

## Purpose and scope

The paper's overhead camera (Logitech C920n) records the automated experiment, and a
YOLOv8 model fine-tuned on images of the electric pipettes detects them in the
recorded frames. In the current setup this detection is run **offline, after the
experiment**, on the saved video file — it is a post-hoc analysis step, not a
component of the live experiment log produced by `src/monitoring/`. `infer_video.py`
writes a per-frame CSV of detections that can be joined to the sensor/process log by
frame index or timestamp, but no such join is performed automatically.

## Dataset

The published model was fine-tuned on 59 still images of the experimental setup,
each annotated with a single bounding box for the class `electric_pipette`
(single-class dataset, 59 boxes total):

- Images: photographed with an iPhone, 4284 px wide, converted from HEIC to JPG.
- Annotation tool: [labelme](https://github.com/wkentaro/labelme) rectangles, one JSON
  file per image (`{stem}.json` next to `{stem}.jpg`).
- Conversion: `prepare_dataset.py` reads the labelme JSON files, converts the
  rectangles to YOLO's normalized `class x_center y_center width height` format, and
  copies the images into a train/val split.
- Split: 80 / 20, seed 42 -> **47 train / 12 val** images.

## Fine-tuning configuration

The distributed configuration (`train.py` defaults) matches the run actually used to
produce the published weights (referred to as `electric_pipette2` in the original
working repository):

| Parameter | Value |
|---|---|
| Base model | `yolov8n.pt` (COCO-pretrained, no transfer from an earlier custom run) |
| Image size | 1280 |
| Batch size | 4 |
| Epochs | 100 (ran to completion) |
| Patience (early stopping) | 50 |
| Optimizer | auto (Ultralytics' automatic optimizer/LR selection) |
| LR schedule | cosine (`cos_lr=True`) |
| Mosaic augmentation | enabled, disabled for the final 10 epochs (`close_mosaic=10`) |
| Device | Apple Silicon MPS |
| Seed | 0, deterministic |

Augmentation defaults that matter for this dataset (Ultralytics defaults, unchanged):
`mosaic=1.0`, `fliplr=0.5`, `hsv_h=0.015`, `hsv_s=0.7`, `hsv_v=0.4`, `scale=0.5`,
`translate=0.1`.

An earlier run (`electric_pipette`, imgsz 640, batch 8, patience 20) was stopped early
after 31 epochs and is superseded by the configuration above; it is not otherwise
documented here.

## Validation metrics

Best epoch on the validation split (epoch 85 of 100):

| Metric | Value |
|---|---|
| Precision | 1.000 |
| Recall | 0.970 |
| mAP50 | 0.995 |
| mAP50-95 | 0.739 |

## Reproduce

1. Install dependencies: `pip install -r detection/requirements.txt`
2. Place your own annotated images in `detection/data/` (labelme JSON files) and
   `detection/data/images_jpg/` (the corresponding JPGs), following the layout
   described above.
3. Build the YOLO-format dataset:
   ```
   python prepare_dataset.py --data-dir data --out dataset --train-ratio 0.8 --seed 42
   ```
4. Copy `data.example.yaml` to `data.yaml` (adjust `path` if needed), then train:
   ```
   python train.py --data data.yaml --model yolov8n.pt --epochs 100 --imgsz 1280 \
       --batch 4 --patience 50 --device auto --name electric_pipette --project runs
   ```
5. Run offline inference on a recorded experiment video:
   ```
   python infer_video.py --model runs/electric_pipette/weights/best.pt \
       --source video.mp4 --conf 0.25 --imgsz 960 --device auto
   ```
   This saves the annotated video/frames plus `detections.csv`
   (`frame, n_detections, max_conf`) under `runs/video_result/`.

`--device auto` lets Ultralytics pick the best available backend; pass `mps`, `cuda`,
`cuda:0`, or `cpu` explicitly if you need to force one.

## Weights and training data

The fine-tuned weights and training images used in the paper are **not** distributed
(they contain laboratory-specific scenes). `weights/` and `dataset/` are gitignored.
To obtain a model:

1. Capture images of your own setup with the overhead camera.
2. Annotate the objects of interest with labelme (or another tool, converting to the
   labelme JSON schema `prepare_dataset.py` expects).
3. Fine-tune a YOLOv8 model on the annotated images using the steps above.
4. Place the resulting weights in `weights/` (gitignored).

If you need the exact weights used in the paper for comparison purposes, contact the
authors.

## Not included: additional video frames

The lab's working copy also holds 20 unannotated frames extracted from an
experiment video (`data/video_frames/`), collected for a planned but never-run third
training pass that would have added video-derived frames to the still-image dataset.
These frames are **not** part of the published model's training set described above
and are not included in this repository.
