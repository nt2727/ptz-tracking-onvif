import os
import sys
import time
import requests
import cv2
import json

# Import'ları düzeltildi (Yeni klasör yapısına göre)
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from sdks.novavision.src.media.image import Image as image
from sdks.novavision.src.base.model import Image, BoundingBox
from capsules.PTZTracking.src.models.PackageModel import (
    PackageModel,
    PTZTrackingInputs,
    PTZTrackingConfigs,
    PTZTrackingRequest,
    PTZTrackingExecutor,
    ConfigExecutor,
    InputImage,
    InputDetections,
    Detection,
    ConfigPTZAdvance,
    ConfigPTZAdvanceTrue
)

ENDPOINT_URL = "http://127.0.0.1:8000/api"


def simulation_loop():
    # Test videosunu yükle
    video_path = os.path.join(os.path.dirname(__file__), '../resources/test_video.mp4')
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"ERROR: '{video_path}' bulunamadı!")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Simülasyon için sahte bir detection hareketi
    box_x = 100
    direction = 5

    print("[INFO] PID Simülasyonu başlatılıyor. Çıkmak için CTRL+C.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Video bitince başa sar
                continue

            # Sahte detection'ı sağa-sola kaydır
            box_x += direction
            if box_x > frame_width - 100 or box_x < 0:
                direction *= -1

            # NovaVision isteği oluştur
            image_obj = Image(name="SimImg", uID="001", mimeType="image/png", encoding="bytes", value=frame,
                              type="Image")
            image_obj = image.encode64(image_obj)
            inputImage = InputImage(value=image_obj)

            boundingBox = BoundingBox(left=box_x, top=100.0, width=100.0, height=100.0)
            detection1 = Detection(boundingBox=boundingBox, confidence=0.85, classId=0, classLabel="sim", trackerID=1)
            inputDetections = InputDetections(value=[detection1])

            config_advance = ConfigPTZAdvanceTrue(
                configCameraIP=ConfigCameraIP(value="127.0.0.1"),
                configCameraPort=ConfigCameraPort(value=80),
                configCameraUsername=ConfigCameraUsername(value="admin"),
                configCameraPassword=ConfigCameraPassword(value="admin")
            )

            ptzConfigs = PTZTrackingConfigs(configPTZAdvance=ConfigPTZAdvance(value=config_advance))
            ptzInputs = PTZTrackingInputs(inputImage=inputImage, inputDetections=inputDetections)
            ptzRequest = PTZTrackingRequest(inputs=ptzInputs, configs=ptzConfigs)

            ptzExecutor = PTZTrackingExecutor(value=ptzRequest)
            executor = ConfigExecutor(value=ptzExecutor)
            packageConfigs = PackageConfigs(executor=executor)
            package_model = PackageModel(configs=packageConfigs, name="PTZTracking", mode="continuous")

            # API'ye gönder
            response = requests.post(ENDPOINT_URL, json=json.loads(package_model.json()))
            print(f"[SIM] Box X: {box_x}, Response: {response.json()}")

            time.sleep(0.1)  # 10 FPS

    except KeyboardInterrupt:
        print("\n[INFO] Simülasyon durduruldu.")
    finally:
        cap.release()


if __name__ == "__main__":
    simulation_loop()