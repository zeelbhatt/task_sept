from .depthai_adapter import DepthAISensor

def GetDepthai(
    model: str = "oak-d-pro",
    *,
    allow_mock_on_no_device: bool = True,
    mock_source = 0,  # 0 = default webcam; 'synthetic' for generated frames
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
):
    """
    Unified factory: tries real OAK via depthai, but can fall back to webcam/synthetic.
    """
    sensor = DepthAISensor(
        model=model,
        output_dir="recordings",
        allow_mock_on_no_device=allow_mock_on_no_device,
        mock_source=mock_source,
        width=width,
        height=height,
        fps=fps,
    )
    sensor.initialize()
    return sensor
