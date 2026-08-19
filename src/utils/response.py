from sdks.novavision.src.helper.package import PackageHelper
from capsules.PTZTracking.src.models.PackageModel import (
    PackageModel,
    PackageConfigs,
    PTZTrackingResponse,
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

    ptzResponse = PTZTrackingResponse(outputs=ptzOutputs)
    executor_class = (
        PTZTrackingAutoExecutor
        if executor_type == "PTZTrackingAuto"
        else PTZTrackingExecutor
    )
    ptzExecutor = executor_class(value=ptzResponse)

    executor = ConfigExecutor(value=ptzExecutor)
    packageConfigs = PackageConfigs(executor=executor)

    package = PackageHelper(packageModel=PackageModel, packageConfigs=packageConfigs)
    packageModel = package.build_model(context)
    return packageModel
