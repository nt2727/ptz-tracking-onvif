import numpy as np
 
from sdks.novavision.src.base.logger import LoggerManager
from sdks.novavision.src.media.image import Image

logger = LoggerManager()


def prepare_output_image(image, package_uID, redis_db):
    """
    PTZTracking / PTZTrackingAuto çıktısına konacak resmi hazırlar.

    ÖNEMLİ: Buraya `self.images` (girdinin HAM/çözülmemiş hali) değil,
    `Image.get_frame(...)` ile zaten base64/bytes'tan çözülüp numpy
    array'e dönüştürülmüş `image` nesnesi verilmelidir.

    `Image.get_frame`, kendisine verilen dict'i yerinde (in-place)
    günceller ve "value"/"shape_key" alanlarına Redis'ten gelen HAM
    (henüz decode edilmemiş) bytes'ı yazar. Bu yüzden çözümden sonra
    orijinal `self.images` sözlüğü artık decode edilmemiş ham veri
    içerir; bunu doğrudan çıktıya koymak OutputImage modelinin
    (Union[List[Image], Image]) validasyonunu başarısız kılar
    ("6 validation errors for Image" hatasının kaynağı budur).

    Bu fonksiyon, zaten çözülmüş `image` nesnesini IpCamera üreticisinin
    kullandığı yöntemle (Image.set_frame) yeniden encode edip Redis'e
    yazar ve çıktıyı her zaman bir liste olarak döndürür.
    """
    if image is None:
        logger.warning(
            "SDKs (PTZTracking) - inputImage çözülemedi (Image.get_frame "
            "None döndürdü); outputImage boş liste olarak gönderiliyor."
        )
        return []

    output_frame = Image.set_frame(img=image, package_uID=package_uID, redis_db=redis_db)
    return [output_frame]

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