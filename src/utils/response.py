from sdks.novavision.src.helper.package import PackageHelper
from capsules.PTZTracking.src.models.PackageModel import (
    PackageModel,
    PackageConfigs,
    PTZTrackingResponse,
    PTZTrackingAutoResponse,
    PTZTrackingExecutor,
    PTZTrackingAutoExecutor,
    ConfigExecutor,
    PTZTrackingOutputs,
    OutputDetections,
    OutputSeeking,
    OutputImage,
)


def build_ptz_tracking_response(
    context,
    output_detections,
    seeking,
    output_image,
    executor_type="PTZTracking",
):
    outputDetections = OutputDetections(value=output_detections)
    outputSeeking = OutputSeeking(value=seeking)
    outputImage = OutputImage(value=output_image)

    ptzOutputs = PTZTrackingOutputs(
        outputDetections=outputDetections,
        outputSeeking=outputSeeking,
        outputImage=outputImage
    )

    is_auto = executor_type == "PTZTrackingAuto"
    response_class = PTZTrackingAutoResponse if is_auto else PTZTrackingResponse
    ptzResponse = response_class(outputs=ptzOutputs)
    executor_class = PTZTrackingAutoExecutor if is_auto else PTZTrackingExecutor
    ptzExecutor = executor_class(value=ptzResponse)

    executor = ConfigExecutor(value=ptzExecutor)
    packageConfigs = PackageConfigs(executor=executor)

    package = PackageHelper(packageModel=PackageModel, packageConfigs=packageConfigs)
    packageModel = package.build_model(context)
    return packageModel
