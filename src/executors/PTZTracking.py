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


class PTZTracking(Capsule):
    def __init__(self, request, bootstrap):
        super().__init__(request, bootstrap)
        self.request.model = PackageModel(**(self.request.data))
        self.images = self.request.get_param("inputImage")
        self.input_detections = self.request.get_param("inputDetections")

    @staticmethod
    def bootstrap(config: dict) -> dict:
        app = Application()
        advance = app.get_param(config, "ConfigPTZAdvance")

        # Default değerler
        ip, port, username, password = "127.0.0.1", 80, "admin", "admin"
        kp, ki, kd = 0.2, 0.0, 2.0
        dead_zone, update_rate = 50, 100
        movement_type = "Follow"
        follow_tracker = True
        flip_x, flip_y = False, True
        zoom_if_able = False
        simulate_variable_speed = False
        minimum_camera_speed = 0.05
        default_position_preset = ""
        idle_seconds = 30

        if advance == "True":
            # Güvenli get_param kullanımı (Claude'un önerdiği yapı)
            if app.get_param(config, "CameraIP"):
                ip = app.get_param(config, "CameraIP")
            if app.get_param(config, "CameraPort"):
                port = app.get_param(config, "CameraPort")
            if app.get_param(config, "CameraUsername"):
                username = app.get_param(config, "CameraUsername")
            if app.get_param(config, "CameraPassword"):
                password = app.get_param(config, "CameraPassword")
            if app.get_param(config, "PIDKp"):
                kp = app.get_param(config, "PIDKp")
            if app.get_param(config, "PIDKi"):
                ki = app.get_param(config, "PIDKi")
            if app.get_param(config, "PIDKd"):
                kd = app.get_param(config, "PIDKd")
            if app.get_param(config, "DeadZone"):
                dead_zone = app.get_param(config, "DeadZone")
            if app.get_param(config, "UpdateRateLimit"):
                update_rate = app.get_param(config, "UpdateRateLimit")
            if app.get_param(config, "MovementType"):
                movement_type = app.get_param(config, "MovementType")
            if app.get_param(config, "FollowTracker"):
                follow_tracker = app.get_param(config, "FollowTracker")
            if app.get_param(config, "FlipXMovement"):
                flip_x = app.get_param(config, "FlipXMovement")
            if app.get_param(config, "FlipYMovement"):
                flip_y = app.get_param(config, "FlipYMovement")
            if app.get_param(config, "ZoomIfAble"):
                zoom_if_able = app.get_param(config, "ZoomIfAble")
            if app.get_param(config, "SimulateVariableSpeed"):
                simulate_variable_speed = app.get_param(config, "SimulateVariableSpeed")
            if app.get_param(config, "MinimumCameraSpeed"):
                minimum_camera_speed = app.get_param(config, "MinimumCameraSpeed")
            if app.get_param(config, "DefaultPositionPreset"):
                default_position_preset = app.get_param(config, "DefaultPositionPreset")
            if app.get_param(config, "MoveToPositionAfterIdleSeconds"):
                idle_seconds = app.get_param(config, "MoveToPositionAfterIdleSeconds")

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

        # Zoom if able (örnek: sadece hata sıfırsa zoom yap)
        if self.bootstrap["zoom_if_able"] and speed_x == 0 and speed_y == 0:
            speed_z = 0.2  # sabit bir yakınlaştırma hızı
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
                        trackerID=0,
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