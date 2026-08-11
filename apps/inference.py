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
    PTZTrackingExecutor,
    PTZTrackingAutoExecutor,
    ConfigExecutor,
    InputImage,
    InputDetections,
    Detection,
    ConfigCameraIP,
    ConfigCameraPort,
    ConfigCameraUsername,
    ConfigCameraPassword,
    ConfigPIDKp,
    ConfigPIDKi,
    ConfigPIDKd,
    ConfigDeadZone,
    ConfigUpdateRateLimit,
    ConfigPTZAdvance,
    ConfigPTZAdvanceTrue
)

# NovaVision API Endpoint (Docker'daki FastAPI adresi)
ENDPOINT_URL = "http://127.0.0.1:8000/api"


def inference():
    # 1. Test Görüntüsünü Yükle (resources klasöründen)
    image_path = os.path.join(os.path.dirname(__file__), '../resources/odm_test_frame.png')
    imread = cv2.imread(image_path)

    if imread is None:
        print(f"ERROR: '{image_path}' dosyası bulunamadı. Lütfen resources klasörüne bir test görüntüsü ekleyin!")
        return

    # NovaVision Image objesine dönüştür
    image_obj = Image(name="PTZTestImage", uID="001", mimeType="image/png", encoding="bytes", value=imread,
                      type="Image")
    image_obj = image.encode64(image_obj)
    inputImage = InputImage(value=image_obj)

    # 2. Test için Sahte Bir Detection Oluştur
    # (Çerçevenin sağ üst köşesine bir bounding box koyuyoruz)
    boundingBox = BoundingBox(left=300.0, top=100.0, width=100.0, height=100.0)
    detection1 = Detection(boundingBox=boundingBox, confidence=0.85, classId=0, classLabel="person", trackerID=1)

    inputDetections = InputDetections(value=[detection1])

    # 3. Configurations Oluştur (Flat yapıya uygun)
    ptzConfigs = PTZTrackingConfigs(
        configCameraIP=ConfigCameraIP(value="127.0.0.1"),
        configCameraPort=ConfigCameraPort(value=80),
        configCameraUsername=ConfigCameraUsername(value="admin"),
        configCameraPassword=ConfigCameraPassword(value="admin"),
        configPIDKp=ConfigPIDKp(value=0.2),
        configPIDKi=ConfigPIDKi(value=0.0),
        configPIDKd=ConfigPIDKd(value=2.0),
        configDeadZone=ConfigDeadZone(value=50),
        configUpdateRateLimit=ConfigUpdateRateLimit(value=100)
    )

    ptzInputs = PTZTrackingInputs(inputImage=inputImage, inputDetections=inputDetections)
    ptzRequest = PTZTrackingRequest(inputs=ptzInputs, configs=ptzConfigs)

    # 4. Executor'ü oluştur (Manuel)
    ptzExecutor = PTZTrackingExecutor(value=ptzRequest)
    executor = ConfigExecutor(value=ptzExecutor)
    packageConfigs = PackageConfigs(executor=executor)

    package_model = PackageModel(configs=packageConfigs, name="PTZTracking", mode="continuous")

    request_json = json.loads(package_model.json())

    print("[INFO] API'ye istek gönderiliyor...")
    response = requests.post(ENDPOINT_URL, json=request_json)
    print(response.raise_for_status())
    print(response.json())


if __name__ == "__main__":
    inference()