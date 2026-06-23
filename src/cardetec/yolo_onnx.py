from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .tracker import Detection


DEFAULT_COCO_LABELS = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]


class YoloOnnxDetector:
    def __init__(
        self,
        model_path: str,
        input_size: int = 640,
        score_threshold: float = 0.25,
        confidence_threshold: float = 0.25,
        nms_threshold: float = 0.45,
        labels: list[str] | None = None,
        allowed_classes: list[str] | None = None,
    ) -> None:
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Model ONNX tidak ditemukan: {model_file}")

        self.input_size = input_size
        self.score_threshold = score_threshold
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.labels = labels or DEFAULT_COCO_LABELS
        self.allowed_classes = set(allowed_classes or [])
        self.net = cv2.dnn.readNetFromONNX(str(model_file))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    def predict(self, frame: np.ndarray) -> list[Detection]:
        blob, scale, pad_x, pad_y = self._make_blob(frame)
        self.net.setInput(blob)
        outputs = self.net.forward()
        return self._decode_outputs(frame.shape, outputs, scale, pad_x, pad_y)

    def _make_blob(self, frame: np.ndarray) -> tuple[np.ndarray, float, int, int]:
        height, width = frame.shape[:2]
        scale = min(self.input_size / width, self.input_size / height)
        new_width = int(round(width * scale))
        new_height = int(round(height * scale))
        resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

        canvas = np.full((self.input_size, self.input_size, 3), 114, dtype=np.uint8)
        pad_x = (self.input_size - new_width) // 2
        pad_y = (self.input_size - new_height) // 2
        canvas[pad_y : pad_y + new_height, pad_x : pad_x + new_width] = resized

        blob = cv2.dnn.blobFromImage(canvas, scalefactor=1.0 / 255.0, swapRB=True, crop=False)
        return blob, scale, pad_x, pad_y

    def _decode_outputs(
        self,
        frame_shape: tuple[int, ...],
        outputs: np.ndarray,
        scale: float,
        pad_x: int,
        pad_y: int,
    ) -> list[Detection]:
        height, width = frame_shape[:2]
        predictions = np.squeeze(outputs)
        if predictions.ndim != 2:
            raise ValueError(f"Format output model tidak dikenali: {predictions.shape}")

        if predictions.shape[0] < predictions.shape[1]:
            predictions = predictions.T

        boxes_xywh: list[list[int]] = []
        confidences: list[float] = []
        class_ids: list[int] = []
        labels: list[str] = []

        expected_with_objectness = len(self.labels) + 5
        for row in predictions:
            if row.size < 6:
                continue

            cx, cy, bw, bh = row[:4]
            if row.size == expected_with_objectness:
                objectness = float(row[4])
                class_scores = row[5:]
                class_id = int(np.argmax(class_scores))
                class_score = float(class_scores[class_id])
                confidence = objectness * class_score
            else:
                class_scores = row[4:]
                class_id = int(np.argmax(class_scores))
                class_score = float(class_scores[class_id])
                confidence = class_score

            if class_score < self.score_threshold or confidence < self.confidence_threshold:
                continue

            label = self.labels[class_id] if class_id < len(self.labels) else str(class_id)
            if self.allowed_classes and label not in self.allowed_classes:
                continue

            x1 = int((cx - (bw / 2) - pad_x) / scale)
            y1 = int((cy - (bh / 2) - pad_y) / scale)
            x2 = int((cx + (bw / 2) - pad_x) / scale)
            y2 = int((cy + (bh / 2) - pad_y) / scale)

            x1 = max(0, min(width - 1, x1))
            y1 = max(0, min(height - 1, y1))
            x2 = max(0, min(width - 1, x2))
            y2 = max(0, min(height - 1, y2))

            if x2 <= x1 or y2 <= y1:
                continue

            boxes_xywh.append([x1, y1, x2 - x1, y2 - y1])
            confidences.append(confidence)
            class_ids.append(class_id)
            labels.append(label)

        indices = cv2.dnn.NMSBoxes(
            bboxes=boxes_xywh,
            scores=confidences,
            score_threshold=self.confidence_threshold,
            nms_threshold=self.nms_threshold,
        )

        if len(indices) == 0:
            return []

        detections: list[Detection] = []
        for idx in np.array(indices).reshape(-1):
            x, y, w, h = boxes_xywh[int(idx)]
            detections.append(
                Detection(
                    box=(x, y, x + w, y + h),
                    confidence=confidences[int(idx)],
                    class_id=class_ids[int(idx)],
                    label=labels[int(idx)],
                )
            )
        return detections
