# Object detection module (YOLOv8)

Optional monitoring feature: detects the robot arms and electric pipettes in the
overhead camera image and records the experimental state.

## License notice

This module depends on [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics),
which is licensed under **AGPL-3.0**. To keep the rest of the platform under the MIT
license, this module is isolated here and is distributed under **AGPL-3.0**. The
platform runs without this module; only the camera-based object detection is disabled.

## Weights and training data

The fine-tuned weights and training images used in the paper are **not** distributed
(they contain laboratory-specific scenes). To reproduce:

1. Capture images of your own setup with the overhead camera.
2. Annotate the robot arms and pipettes (e.g., with a YOLO-format annotation tool).
3. Fine-tune a YOLOv8 model on the annotated images.
4. Place the resulting weights in `weights/` (gitignored).

<!-- TODO: import the detection code and the fine-tuning configuration used in the paper. -->
