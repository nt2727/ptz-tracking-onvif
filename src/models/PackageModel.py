from pydantic import Field, validator
from typing import List, Optional, Union, Literal

from sdks.novavision.src.base.model import Package, Configs, Outputs, Inputs, \
    Response, Request, Output, Input, Config, Detection, BoundingBox, Image, Images  # <-- Images eklendi


class InputImage(Input):
    name: Literal["inputImage"] = "inputImage"
    value: Images  # <-- Images olarak değiştir
    type: Literal["Images"] = "Images"  # <-- Literal yap
    field: Literal["img"] = "img"  # <-- field eklendi (opsiyonel ama şartnameye uygun)
    class Config:
        title = "Image"


class CustomDetection(Detection):
    imgUID: Optional[str] = None
    trackerID: Optional[Union[List, int]] = None
    UUID: Optional[str] = ""
    source: Optional[str] = ""


class InputDetections(Input):
    name: Literal["inputDetections"] = "inputDetections"
    value: List[CustomDetection]
    type: Literal["list"] = "list"
    class Config:
        title = "Detections"


class OutputImage(Output):
    name: Literal["outputImage"] = "outputImage"
    value: Images  # <-- Images olarak değiştir
    type: Literal["Images"] = "Images"  # <-- Literal yap
    field: Literal["img"] = "img"  # <-- field eklendi
    class Config:
        title = "Image"


class OutputDetections(Output):
    name: Literal["outputDetections"] = "outputDetections"
    value: list
    type: Literal["list"] = "list"
    class Config:
        title = "Detections"


class OutputSeeking(Output):
    name: Literal["outputSeeking"] = "outputSeeking"
    value: bool
    type: Literal["boolean"] = "boolean"
    class Config:
        title = "Seeking Status"


# ==========================================
# 1. PTZ Tracking Executor Configurations
# ==========================================
class ConfigCameraIP(Config):
    name: Literal["CameraIP"] = "CameraIP"
    value: str = Field(default="127.0.0.1")
    type: Literal["string"] = "string"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Camera IP Address"
        json_schema_extra = {"shortDescription": "ONVIF Camera IP"}

class ConfigCameraPort(Config):
    name: Literal["CameraPort"] = "CameraPort"
    value: int = Field(default=80, ge=1, le=65535)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Camera Port"
        json_schema_extra = {"shortDescription": "ONVIF Port"}

class ConfigCameraUsername(Config):
    name: Literal["CameraUsername"] = "CameraUsername"
    value: str = Field(default="admin")
    type: Literal["string"] = "string"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Camera Username"
        json_schema_extra = {"shortDescription": "ONVIF Username"}

class ConfigCameraPassword(Config):
    name: Literal["CameraPassword"] = "CameraPassword"
    value: str = Field(default="admin")
    type: Literal["string"] = "string"
    field: Literal["password"] = "password"
    class Config:
        title = "Camera Password"
        json_schema_extra = {"shortDescription": "ONVIF Password"}

class ConfigPIDKp(Config):
    name: Literal["PIDKp"] = "PIDKp"
    value: float = Field(default=0.2, ge=0, le=1)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Kp"
        json_schema_extra = {"shortDescription": "PID Proportional Gain"}

class ConfigPIDKi(Config):
    name: Literal["PIDKi"] = "PIDKi"
    value: float = Field(default=0.0, ge=0, le=1)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Ki"
        json_schema_extra = {"shortDescription": "PID Integral Gain"}

class ConfigPIDKd(Config):
    name: Literal["PIDKd"] = "PIDKd"
    value: float = Field(default=2.0, ge=0, le=10)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Kd"
        json_schema_extra = {"shortDescription": "PID Derivative Gain"}

class ConfigDeadZone(Config):
    name: Literal["DeadZone"] = "DeadZone"
    value: int = Field(default=50, ge=0, le=500)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Dead Zone (pixels)"
        json_schema_extra = {"shortDescription": "Dead Zone"}

class ConfigUpdateRateLimit(Config):
    name: Literal["UpdateRateLimit"] = "UpdateRateLimit"
    value: int = Field(default=100, ge=10, le=1000)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Update Rate Limit (ms)"
        json_schema_extra = {"shortDescription": "Rate Limit ms"}

class ConfigMovementType(Config):
    name: Literal["MovementType"] = "MovementType"
    value: Literal["Follow", "GoToPreset"] = "Follow"
    type: Literal["string"] = "string"
    field: Literal["option"] = "option"
    class Config:
        title = "Movement Type"
        json_schema_extra = {"shortDescription": "Follow or Go To Preset"}

class ConfigFollowTracker(Config):
    name: Literal["FollowTracker"] = "FollowTracker"
    value: bool = True
    type: Literal["boolean"] = "boolean"
    field: Literal["option"] = "option"
    class Config:
        title = "Follow Tracker"
        json_schema_extra = {"shortDescription": "Lock onto tracker ID"}

class ConfigFlipXMovement(Config):
    name: Literal["FlipXMovement"] = "FlipXMovement"
    value: bool = False
    type: Literal["boolean"] = "boolean"
    field: Literal["option"] = "option"
    class Config:
        title = "Flip X Movement"
        json_schema_extra = {"shortDescription": "Invert horizontal movement"}

class ConfigFlipYMovement(Config):
    name: Literal["FlipYMovement"] = "FlipYMovement"
    value: bool = True
    type: Literal["boolean"] = "boolean"
    field: Literal["option"] = "option"
    class Config:
        title = "Flip Y Movement"
        json_schema_extra = {"shortDescription": "Invert vertical movement"}

class ConfigZoomIfAble(Config):
    name: Literal["ZoomIfAble"] = "ZoomIfAble"
    value: bool = False
    type: Literal["boolean"] = "boolean"
    field: Literal["option"] = "option"
    class Config:
        title = "Zoom If Able"
        json_schema_extra = {"shortDescription": "Auto-zoom to fill frame"}

class ConfigSimulateVariableSpeed(Config):
    name: Literal["SimulateVariableSpeed"] = "SimulateVariableSpeed"
    value: bool = False
    type: Literal["boolean"] = "boolean"
    field: Literal["option"] = "option"
    class Config:
        title = "Simulate Variable Speed"
        json_schema_extra = {"shortDescription": "Pulse-width simulation"}

class ConfigMinimumCameraSpeed(Config):
    name: Literal["MinimumCameraSpeed"] = "MinimumCameraSpeed"
    value: float = Field(default=0.05, ge=0, le=1)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Minimum Camera Speed"
        json_schema_extra = {"shortDescription": "Min speed threshold (0-1)"}

class ConfigDefaultPositionPreset(Config):
    name: Literal["DefaultPositionPreset"] = "DefaultPositionPreset"
    value: str = Field(default="")
    type: Literal["string"] = "string"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Default Position Preset"
        json_schema_extra = {"shortDescription": "Home preset name"}

class ConfigMoveToPositionAfterIdleSeconds(Config):
    name: Literal["MoveToPositionAfterIdleSeconds"] = "MoveToPositionAfterIdleSeconds"
    value: int = Field(default=30, ge=0)
    type: Literal["number"] = "number"
    field: Literal["textInput"] = "textInput"
    class Config:
        title = "Idle Reset Time (seconds)"
        json_schema_extra = {"shortDescription": "Auto-reset after idle seconds"}


# ==========================================
# 2. ConfigPTZAdvance Toggle Structure
# ==========================================
class ConfigPTZAdvanceTrue(Config):
    name: Literal["True"] = "True"
    value: Literal["True"] = "True"
    type: Literal["bool"] = "bool"
    field: Literal["option"] = "option"
    configCameraIP: ConfigCameraIP
    configCameraPort: ConfigCameraPort
    configCameraUsername: ConfigCameraUsername
    configCameraPassword: ConfigCameraPassword
    configPIDKp: ConfigPIDKp
    configPIDKi: ConfigPIDKi
    configPIDKd: ConfigPIDKd
    configDeadZone: ConfigDeadZone
    configUpdateRateLimit: ConfigUpdateRateLimit
    configMovementType: ConfigMovementType
    configFollowTracker: ConfigFollowTracker
    configFlipXMovement: ConfigFlipXMovement
    configFlipYMovement: ConfigFlipYMovement
    configZoomIfAble: ConfigZoomIfAble
    configSimulateVariableSpeed: ConfigSimulateVariableSpeed
    configMinimumCameraSpeed: ConfigMinimumCameraSpeed
    configDefaultPositionPreset: ConfigDefaultPositionPreset
    configMoveToPositionAfterIdleSeconds: ConfigMoveToPositionAfterIdleSeconds
    class Config:
        title = "Enable Advanced Settings"

class ConfigPTZAdvanceFalse(Config):
    name: Literal["False"] = "False"
    value: Literal["False"] = "False"
    type: Literal["bool"] = "bool"
    field: Literal["option"] = "option"
    class Config:
        title = "Disable Advanced Settings"

class ConfigPTZAdvance(Config):
    name: Literal["ConfigPTZAdvance"] = "ConfigPTZAdvance"
    value: Union[ConfigPTZAdvanceTrue, ConfigPTZAdvanceFalse]
    type: Literal["object"] = "object"
    field: Literal["dependentDropdownlist"] = "dependentDropdownlist"
    restart: Literal[True] = True
    class Config:
        title = "Advance"
        json_schema_extra = {"shortDescription": "Advanced Settings"}


class PTZTrackingConfigs(Configs):
    configPTZAdvance: ConfigPTZAdvance


class PTZTrackingInputs(Inputs):
    inputImage: InputImage
    inputDetections: InputDetections


class PTZTrackingOutputs(Outputs):
    outputDetections: OutputDetections
    outputSeeking: OutputSeeking
    outputImage: OutputImage


class PTZTrackingRequest(Request):
    inputs: Optional[PTZTrackingInputs] = None
    configs: PTZTrackingConfigs
    class Config:
        json_schema_extra = {"target": "configs"}


class PTZTrackingResponse(Response):
    outputs: PTZTrackingOutputs


class PTZTrackingExecutor(Config):
    name: Literal["PTZTracking"] = "PTZTracking"
    value: Union[PTZTrackingRequest, PTZTrackingResponse]
    type: Literal["object"] = "object"
    field: Literal["option"] = "option"
    class Config:
        title = "PTZTracking"
        json_schema_extra = {"target": {"value": 0}}

class PTZTrackingAutoExecutor(Config):
    name: Literal["PTZTrackingAuto"] = "PTZTrackingAuto"
    value: Union[PTZTrackingRequest, PTZTrackingResponse]
    type: Literal["object"] = "object"
    field: Literal["option"] = "option"
    class Config:
        title = "PTZTrackingAuto"
        json_schema_extra = {"target": {"value": 0}}

class ConfigExecutor(Config):
    name: Literal["ConfigExecutor"] = "ConfigExecutor"
    value: Union[PTZTrackingExecutor, PTZTrackingAutoExecutor]
    type: Literal["executor"] = "executor"
    field: Literal["dependentDropdownlist"] = "dependentDropdownlist"
    class Config:
        title = "Task"
        
# ==========================================
# 3. Global Package Configuration
# ==========================================
class PackageConfigs(Configs):
    executor: ConfigExecutor

class PackageModel(Package):
    configs: PackageConfigs
    type: Literal["capsule"] = "capsule"
    name: Literal["PTZTracking"] = "PTZTracking"