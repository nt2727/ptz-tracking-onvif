import numpy as np


def calculate_bbox_midpoint(bbox):
    x1 = bbox["left"]
    y1 = bbox["top"]
    w = bbox["width"]
    h = bbox["height"]
    x_mid = x1 + w / 2
    y_mid = y1 + h / 2
    return x_mid, y_mid, w, h


def process_detections(image, detection_tensor):
    image_shape = image.value.shape[:2]

    if len(detection_tensor) == 0:
        return {
            "boxes": np.array([]).reshape(0, 4),
            "scores": np.array([]),
            "cls": np.array([]),
            "indices": np.array([]),
            "orig_shape": image_shape,
        }

    res = {
        "boxes": detection_tensor[:, :4],
        "scores": detection_tensor[:, 4],
        "cls": detection_tensor[:, 5],
        "orig_shape": image_shape,
    }
    if detection_tensor.shape[1] >= 7:
        res["indices"] = detection_tensor[:, 6].astype(int)

    return res