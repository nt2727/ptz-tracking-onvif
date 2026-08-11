import os
import sys
import uuid
import time
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../"))

from sdks.novavision.src.base.capsule import Capsule
from sdks.novavision.src.helper.executor import Executor
from sdks.novavision.src.media.image import Image
from sdks.novavision.src.base.application import Application

from capsules.PTZTracking.src.models.PackageModel import (
    PackageModel,
    BoundingBox,
    Detection,
)
from capsules.PTZTracking.src.classes.ONVIFWrapper import ONVIFWrapper
from capsules.PTZTracking.src.classes.PIDController import PIDController
from capsules.PTZTracking.src.utils.response import build_ptz_tracking_response
from capsules.PTZTracking.src.utils.utils import calculate_bbox_midpoint, process_detections


class PTZTrackingAuto(Capsule):
    def __init__(self, request, bootstrap):
        super().__init__(request, bootstrap)
        self.request.model = PackageModel(**(self.request.data))
        self.images = self.request.get_param("inputImage")
        self.input_detections = self.request.get_param("inputDetections")

    @staticmethod
    def bootstrap(config: dict) -> dict:
        app = Application()

        def safe_get(name, default):
            val = app.get_param(config, name)
            return val if val is not None else default

        ip = safe_get("CameraIP", "127.0.0.1")
        port = safe_get("CameraPort", 80)
        username = safe_get("CameraUsername", "admin")
        password = safe_get("CameraPassword", "admin")
        kp = safe_get("PIDKp", 0.2)
        ki = safe_get("PIDKi", 0.0)
        kd = safe_get("PIDKd", 2.0)
        dead_zone = safe_get("DeadZone", 50)
        update_rate = safe_get("UpdateRateLimit", 100)
        movement_type = safe_get("MovementType", "Follow")
        follow_tracker = safe_get("FollowTracker", True)
        flip_x = safe_get("FlipXMovement", False)
        flip_y = safe_get("FlipYMovement", True)
        zoom_if_able = safe_get("ZoomIfAble", False)
        simulate_variable_speed = safe_get("SimulateVariableSpeed", False)
        minimum_camera_speed = safe_get("MinimumCameraSpeed", 0.05)
        default_position_preset = safe_get("DefaultPositionPreset", "")
        idle_seconds = safe_get("MoveToPositionAfterIdleSeconds", 30)

        # AĞDA KAMERA BULMA MANTIĞI (OTOMATİK EXECUTOR FARKI)
        print("[PTZTrackingAuto] Ağda ONVIF kamera aranıyor...")
        devices = ONVIFWrapper.discover_cameras(timeout=5, username=username, password=password)
        if not devices:
            raise ValueError("Ağda hiçbir ONVIF kamera bulunamadı.")

        ip, port, _ = devices[0]
        print(f"[PTZTrackingAuto] Kamera bulundu: {ip}:{port}")

        camera = ONVIFWrapper(ip, port, username, password)
        camera.start_background_loop()
        pid = PIDController(kp, ki, kd)

        return {
            "camera": camera,
            "pid": pid,
            "dead_zone": dead_zone,
            "update_rate": update_rate,
            "movement_type": movement_type,
            "follow_tracker": follow_tracker,
            "flip_x": flip_x,
            "flip_y": flip_y,
            "zoom_if_able": zoom_if_able,
            "simulate_variable_speed": simulate_variable_speed,
            "minimum_camera_speed": minimum_camera_speed,
            "default_position_preset": default_position_preset,
            "idle_seconds": idle_seconds,
            "last_move_time": time.time(),
            "idle_counter": 0,
            "current_tracker_id": None
        }

    def extract_detections(self):
        detection_list = []
        class_label_id = {}
        img_UID = self.input_detections[0]["imgUID"]

        for index, detection in enumerate(self.input_detections):
            bbox = detection["boundingBox"]
            x_mid, y_mid, w, h = calculate_bbox_midpoint(bbox)

            confidence = detection["confidence"]
            class_id = detection["classId"]
            class_label_id[class_id] = detection["classLabel"]

            self.input_detections[index]["index"] = index
            detection_list.append([x_mid, y_mid, w, h, confidence, class_id, index])

        return np.array(detection_list), class_label_id, img_UID

    def create_detection_tensor(self, detection_list):
        return np.array(detection_list, dtype=np.float32)

    def track_with_pid(self, detections, image_shape):
        if len(detections["boxes"]) == 0:
            self.bootstrap["camera"].continuous_move(0, 0, 0, rate_limit_ms=0)
            return []

        # Box formatı [x_mid, y_mid, w, h]
        box = detections["boxes"][0]
        obj_cx, obj_cy, bw, bh = box[0], box[1], box[2], box[3]

        w, h = image_shape[1], image_shape[0]
        frame_cx = w / 2
        frame_cy = h / 2

        error_x = obj_cx - frame_cx
        error_y = obj_cy - frame_cy

        speed_x, speed_y, speed_z = self.bootstrap["pid"].compute(error_x, error_y, 0.0)

        # Flip X/Y
        if self.bootstrap["flip_x"]:
            speed_x = -speed_x
        if self.bootstrap["flip_y"]:
            speed_y = -speed_y

        # Minimum Speed
        min_speed = self.bootstrap["minimum_camera_speed"]
        if abs(speed_x) < min_speed and speed_x != 0:
            speed_x = min_speed * (1 if speed_x > 0 else -1)
        if abs(speed_y) < min_speed and speed_y != 0:
            speed_y = min_speed * (1 if speed_y > 0 else -1)

        # Dead Zone
        if abs(error_x) < self.bootstrap["dead_zone"] and abs(error_y) < self.bootstrap["dead_zone"]:
            speed_x, speed_y = 0, 0

        # Zoom Logic
        if self.bootstrap["zoom_if_able"] and speed_x == 0 and speed_y == 0:
            speed_z = speed_z if speed_z != 0 else 0.2
        else:
            speed_z = 0.0

        self.bootstrap["camera"].continuous_move(
            x=speed_x,
            y=speed_y,
            z=speed_z,
            rate_limit_ms=self.bootstrap["update_rate"],
            simulate_variable_speed=self.bootstrap["simulate_variable_speed"]
        )
        return [detections["boxes"][0]]

    def run(self):
        output_detections = []
        seeking = False
        output_image = self.images

        image = Image.get_frame(img=self.images, redis_db=self.redis_db)
        frame_numpy = image.value if image is not None else None

        if len(self.input_detections) != 0:
            detection_list, class_label_id, img_UID = self.extract_detections()
            detection_tensor = self.create_detection_tensor(detection_list)
            detections = process_detections(image, detection_tensor)

            tracked_boxes = self.track_with_pid(detections, frame_numpy.shape)
            seeking = len(tracked_boxes) > 0

            for box in tracked_boxes:
                output_detections.append(
                    Detection(
                        boundingBox=BoundingBox(
                            left=float(box[0] - box[2] / 2),
                            top=float(box[1] - box[3] / 2),
                            width=float(box[2]),
                            height=float(box[3]),
                        ),
                        confidence=1.0,
                        classId=0,
                        classLabel="Tracked",
                        trackerID=0, # Otomatik modda tracker ID yok
                        imgUID=img_UID,
                        UUID=str(uuid.uuid4()),
                        source="",
                    )
                )
        else:
            self.bootstrap["camera"].continuous_move(0, 0, 0, rate_limit_ms=0)

        packageModel = build_ptz_tracking_response(
            context=self,
            output_detections=output_detections,
            seeking=seeking,
            output_image=output_image
        )
        return packageModel


if "__main__" == __name__:
    Executor(sys.argv[1]).run()