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
from capsules.PTZTracking.src.utils.utils import calculate_bbox_midpoint, process_detections, prepare_output_image


class PTZTrackingAuto(Capsule):
    def __init__(self, request, bootstrap):
        super().__init__(request, bootstrap)
        self.request.model = PackageModel(**(self.request.data))
        self.images = self.request.get_param("inputImage")
        images = [images] if isinstance(images, dict) else images
        self.input_detections = self.request.get_param("inputDetections")

    #---------------------------------------------------değişmeyen ayarlar burda olacak

    @staticmethod
    def bootstrap(config: dict) -> dict:
        app = Application()

        def safe_get(name, default):
            val = app.get_param(config, name)
            return val if val is not None else default

        def safe_get_bool(name, default):
            val = app.get_param(config, name)
            if val is None:
                return default
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() == "true"

        kp = safe_get("PIDKp", 0.2)
        ki = safe_get("PIDKi", 0.0)
        kd = safe_get("PIDKd", 2.0)
        dead_zone = safe_get("DeadZone", 50)
        update_rate = safe_get("UpdateRateLimit", 100)
        movement_type = safe_get("MovementType", "Follow")
        follow_tracker = safe_get_bool("FollowTracker", True)
        flip_x = safe_get_bool("FlipXMovement", False)
        flip_y = safe_get_bool("FlipYMovement", True)
        zoom_if_able = safe_get_bool("ZoomIfAble", False)
        simulate_variable_speed = safe_get_bool("SimulateVariableSpeed", False)
        minimum_camera_speed = safe_get("MinimumCameraSpeed", 0.05)
        if simulate_variable_speed:
            # %10'un altındaki aralıklı (pulse-width) sinyaller kameranın
            # hareket etmesi için genellikle yetersiz kalır, bu yüzden
            # simulate_variable_speed açıkken minimum hız en az 0.1'e çekilir.
            minimum_camera_speed = max(minimum_camera_speed, 0.1)
        default_position_preset = safe_get("DefaultPositionPreset", "")
        idle_seconds = safe_get("MoveToPositionAfterIdleSeconds", 0)

        if idle_seconds and not default_position_preset:
            raise ValueError(
                "MoveToPositionAfterIdleSeconds bir değere ayarlandı ancak "
                "DefaultPositionPreset boş. Idle-reset özelliğinin çalışması "
                "için ConfigDefaultPositionPreset girilmelidir."
            )

        # AĞDA KAMERA BULMA MANTIĞI (OTOMATİK EXECUTOR FARKI)
        # Auto executor kimlik bilgisi istemez: WS-Discovery zaten anonim
        # çalışır, bulunan kameraya da boş kullanıcı adı/şifre ile
        # (şifresiz/açık erişim) bağlanılmaya çalışılır. Manuel IP/port/
        # kullanıcı adı/şifre girişi gereken senaryolar için PTZTracking
        # (manuel) executor kullanılmalıdır.
        print("[PTZTrackingAuto] Searching for ONVIF cameras on the network...")
        devices = ONVIFWrapper.discover_cameras(timeout=5)
        if not devices:
            raise ValueError("Ağda hiçbir ONVIF kamera bulunamadı.")

        ip, port, _ = devices[0]
        print(f"[PTZTrackingAuto] Camera found: {ip}:{port}")

        camera = ONVIFWrapper(ip, port, "", "")
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
            "last_detection_time": time.time(),
            "current_tracker_id": None,
            "preset_applied": False,
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
        camera = self.bootstrap["camera"]

        if len(detections["boxes"]) == 0:
            camera.continuous_move(0, 0, 0, rate_limit_ms=0)
            return []

        box = detections["boxes"][0]
        obj_cx, obj_cy, bw, bh = box[0], box[1], box[2], box[3]

        w, h = image_shape[1], image_shape[0]
        frame_cx = w / 2
        frame_cy = h / 2

        error_x = obj_cx - frame_cx
        error_y = obj_cy - frame_cy

        # PIDKp/PIDKi/PIDKd 0-1 aralığında normalize edilmiş hata için
        # tanımlanmıştır (bkz. ConfigPIDKp/Ki/Kd). Ham piksel hatası doğrudan
        # PID'e verilirse çıktı anında -1/1'e saturasyona uğrar ve smooth
        # tracking yerine bang-bang hareket oluşur; bu yüzden PID'e vermeden
        # önce hata kare boyutuna göre normalize edilir. Dead zone kontrolü
        # ise piksel cinsinden kalmaya devam eder (ConfigDeadZone pixel bazlı).
        normalized_error_x = error_x / w if w > 0 else 0.0
        normalized_error_y = error_y / h if h > 0 else 0.0

        speed_x, speed_y, _ = self.bootstrap["pid"].compute(normalized_error_x, normalized_error_y, 0.0)

        if self.bootstrap["flip_x"]:
            speed_x = -speed_x
        if self.bootstrap["flip_y"]:
            speed_y = -speed_y

        min_speed = self.bootstrap["minimum_camera_speed"]
        if abs(speed_x) < min_speed and speed_x != 0:
            speed_x = min_speed * (1 if speed_x > 0 else -1)
        if abs(speed_y) < min_speed and speed_y != 0:
            speed_y = min_speed * (1 if speed_y > 0 else -1)

        half_dead_zone = self.bootstrap["dead_zone"] / 2
        centered = abs(error_x) < half_dead_zone and abs(error_y) < half_dead_zone
        if centered:
            speed_x, speed_y = 0, 0

        speed_z = 0.0
        if self.bootstrap["zoom_if_able"] and centered:
            target_fill_ratio = 0.35
            zoom_dead_zone = 0.05
            current_fill_ratio = bw / w if w > 0 else 0.0
            ratio_error = target_fill_ratio - current_fill_ratio

            if abs(ratio_error) > zoom_dead_zone:
                # Zoom ekseni de PIDKp/Ki/Kd ile yapılandırılan PID'i kullanır
                # (sabit çarpan/clamp yerine), pan/tilt ile tutarlı davranış
                # için. ratio_error zaten 0-1 aralığında normalize (bw/w oranı).
                speed_z = self.bootstrap["pid"].pid_z(ratio_error)
                if abs(speed_z) < min_speed and speed_z != 0:
                    speed_z = min_speed * (1 if speed_z > 0 else -1)
            else:
                speed_z = 0.0

        camera.continuous_move(
            x=speed_x,
            y=speed_y,
            z=speed_z,
            rate_limit_ms=self.bootstrap["update_rate"],
            simulate_variable_speed=self.bootstrap["simulate_variable_speed"]
        )
        return [detections["boxes"][0]]

    def run(self):
        output_detections = []
        camera = self.bootstrap["camera"]
        movement_type = self.bootstrap["movement_type"]
        default_preset = self.bootstrap["default_position_preset"]

        image = Image.get_frame(img=self.images, redis_db=self.redis_db)
        frame_numpy = image.value if image is not None else None
        output_image = prepare_output_image(image, package_uID=self.uID, redis_db=self.redis_db)

        if movement_type == "GoToPreset":
            if default_preset and not self.bootstrap["preset_applied"]:
                camera.go_to_preset(default_preset)
                self.bootstrap["preset_applied"] = True

            packageModel = build_ptz_tracking_response(
                context=self,
                output_detections=[],
                seeking=camera.seeking(),
                output_image=output_image,
                executor_type="PTZTrackingAuto",
            )
            return packageModel

        if len(self.input_detections) != 0:
            self.bootstrap["last_detection_time"] = time.time()
            self.bootstrap["preset_applied"] = False

            detection_list, class_label_id, img_UID = self.extract_detections()
            detection_tensor = self.create_detection_tensor(detection_list)
            detections = process_detections(image, detection_tensor)

            tracked_boxes = self.track_with_pid(detections, frame_numpy.shape)
            seeking = camera.seeking()

            source_detection = self.input_detections[0]

            for box in tracked_boxes:
                output_detections.append(
                    Detection(
                        boundingBox=BoundingBox(
                            left=float(box[0] - box[2] / 2),
                            top=float(box[1] - box[3] / 2),
                            width=float(box[2]),
                            height=float(box[3]),
                        ),
                        confidence=source_detection["confidence"],
                        classId=source_detection["classId"],
                        classLabel=source_detection["classLabel"],
                        trackerID=0, # Otomatik modda tracker ID yok
                        imgUID=img_UID,
                        UUID=str(uuid.uuid4()),
                        source="",
                    )
                )
        else:
            camera.continuous_move(0, 0, 0, rate_limit_ms=0)
            seeking = camera.seeking()

            idle_elapsed = time.time() - self.bootstrap["last_detection_time"]
            if (
                default_preset
                and self.bootstrap["idle_seconds"]
                and idle_elapsed >= self.bootstrap["idle_seconds"]
                and not self.bootstrap["preset_applied"]
            ):
                camera.go_to_preset(default_preset)
                self.bootstrap["preset_applied"] = True
                seeking = camera.seeking()

        packageModel = build_ptz_tracking_response(
            context=self,
            output_detections=output_detections,
            seeking=seeking,
            output_image=output_image,
            executor_type="PTZTrackingAuto",
        )
        return packageModel


if "__main__" == __name__:
    Executor(sys.argv[1]).run()