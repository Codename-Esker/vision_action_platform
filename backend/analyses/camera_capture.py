import subprocess
from pathlib import Path

from django.conf import settings


CAPTURE_SECONDS = 8


def capture_camera_video(camera_id: str, output_path: Path) -> None:
    url = settings.CAMERA_SOURCES.get(camera_id)
    if not url:
        raise ValueError("서버에 등록되지 않은 카메라입니다.")

    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-use_wallclock_as_timestamps", "1",
        "-i", url,
        "-t", str(CAPTURE_SECONDS),
        "-an",
        "-vf", "fps=15,scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    try:
        captured = subprocess.run(command, capture_output=True, timeout=20)
    except subprocess.TimeoutExpired:
        raise ValueError("카메라 연결 또는 촬영 시간이 초과됐습니다.") from None

    if captured.returncode != 0:
        raise ValueError("카메라 영상을 수집하지 못했습니다. 연결 상태를 확인해 주세요.")

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(output_path),
        ],
        capture_output=True, text=True, timeout=5,
    )
    if probe.returncode != 0:
        raise ValueError("촬영된 영상의 길이를 확인하지 못했습니다.")

    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        raise ValueError("촬영된 영상에 유효한 재생 시간이 없습니다.") from None

    if duration < CAPTURE_SECONDS - 0.5:
        raise ValueError(f"카메라 영상이 {duration:.1f}초에서 중단됐습니다.")
