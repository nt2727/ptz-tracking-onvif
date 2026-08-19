# PTZ Tracking (ONVIF)

PID-based object tracking for ONVIF-compatible PTZ (Pan-Tilt-Zoom) cameras. The package receives detections from an upstream object detector or tracker and moves the camera to keep the selected target near the centre of the frame.

## Executors

Two executors share the same data model and tracking logic:

- `PTZTracking` connects directly to a camera using its IP address, port, username, and password. Use this when the camera address is known.
- `PTZTrackingAuto` discovers ONVIF cameras on the local network through WS-Discovery and connects to the first available device. Discovery requires multicast access and may not work across NAT, separate subnets, or on cameras that hide their ONVIF service.

## Movement modes

- `Follow` selects a detection (by default, the one with the highest confidence) and continuously tracks it with PID control. When tracker following is enabled, it follows the configured `trackerID`.
- `GoToPreset` moves the camera to the preconfigured `DefaultPositionPreset` without using detections.

In `Follow` mode, the camera returns to `DefaultPositionPreset` if no detection is received for `MoveToPositionAfterIdleSeconds`.

## Installation

The project depends on the NovaVision SDK, which is maintained separately.

```bash
pip install git+https://github.com/novavision-ai/sdk.git
pip install -e .
```

For local SDK development, install the SDK from its local checkout instead:

```bash
pip install -e ../sdk
pip install -e .
```

## Configuration notes

- Always use real camera credentials in production; never rely on sample or default credentials.
- The camera must support the ONVIF operations used by this package, including `ContinuousMove` and `GotoPreset`.
- Enable ONVIF in the camera settings if required by the manufacturer, and use the camera's documented ONVIF port.

## Project layout

```
ptz-tracking-onvif/
|-- src/
|   |-- classes/
|   |   |-- ONVIFWrapper.py       # ONVIF camera connection and PTZ commands
|   |   `-- PIDController.py      # PID-based pan, tilt, and zoom control
|   |-- executors/
|   |   |-- PTZTracking.py        # Direct camera connection executor
|   |   `-- PTZTrackingAuto.py    # WS-Discovery camera connection executor
|   |-- models/
|   |   `-- PackageModel.py       # Input, output, and configuration models
|   `-- utils/
|       |-- response.py           # Tracking response construction helpers
|       `-- utils.py              # Detection processing and geometry helpers
|-- setup.py                      # Package metadata and dependencies
|-- requirement.txt               # Development dependency list
|-- README.md                     # Project documentation
`-- LICENSE
```

The distributable Python packages are:

- `novavision.cap.ptz_tracking_onvif`
- `novavision.cap.ptz_tracking_onvif.classes`
- `novavision.cap.ptz_tracking_onvif.executors`
- `novavision.cap.ptz_tracking_onvif.models`
- `novavision.cap.ptz_tracking_onvif.utils`
