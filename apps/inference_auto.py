import os
import sys
import requests
import cv2
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from sdks.novavision.src.media.image import Image as image
from sdks.novavision.src.base.model import Image, BoundingBox
from capsules.PTZTracking.src.models.PackageModel import (
    PackageModel,
    PTZTrackingInputs,
    PTZTrackingConfigs,
    PTZTrackingRequest,
    PTZTrackingAutoExecutor,  # <-- Farklı Executor
    ConfigExecutor,
    InputImage,
    InputDetections,
    Detection,
    ConfigPTZAdvance,
    ConfigPTZAdvanceTrue
)

ENDPOINT_URL = "http://127.0.0.1:8000/api"


def inference_auto():
    # ... (Görüntü yükleme ve Detection oluşturma kısmı inference.py ile aynıdır) ...
    image_path = os.path.join(os.path.dirname(__file__), '../resources/odm_test_frame.png')
    imread = cv2.imread(image_path)
    # ... (image encode işlemi ve detection oluşturma)

    # 3. Configurations Oluştur (Auto için IP'ye gerek yok, WS-Discovery yapacak)
    config_advance = ConfigPTZAdvanceTrue(
        configCameraUsername=ConfigCameraUsername(value="admin"),
        configCameraPassword=ConfigCameraPassword(value="admin")
    )

    ptzConfigs = PTZTrackingConfigs(configPTZAdvance=ConfigPTZAdvance(value=config_advance))
    ptzInputs = PTZTrackingInputs(inputImage=inputImage, inputDetections=inputDetections)
    ptzRequest = PTZTrackingRequest(inputs=ptzInputs, configs=ptzConfigs)

    # 4. Executor'ü oluştur (Otomatik)
    ptzAutoExecutor = PTZTrackingAutoExecutor(value=ptzRequest)  # <-- Auto kullanıldı!
    executor = ConfigExecutor(value=ptzAutoExecutor)
    packageConfigs = PackageConfigs(executor=executor)

    package_model = PackageModel(configs=packageConfigs, name="PTZTracking", mode="continuous")

    request_json = json.loads(package_model.json())
    response = requests.post(ENDPOINT_URL, json=request_json)
    print(response.raise_for_status())
    print(response.json())


if __name__ == "__main__":
    inference_auto()