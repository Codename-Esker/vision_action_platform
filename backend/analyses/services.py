from pathlib import Path

import requests
from django.conf import settings


def request_video_prediction(video):
    url = f"{settings.FASTAPI_BASE_URL.rstrip('/')}/predict/video"

    with video.open("rb") as stream:
        files = {"file": (Path(video.name).name, stream, "video/mp4")}
        response = requests.post(url, files=files, timeout=(5, 180))

    response.raise_for_status()
    return response.json()
