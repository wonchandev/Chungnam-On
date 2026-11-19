"""음성 파일 서버 변환 + 긴 음성 분할 인식.

업로드된 음성(webm/ogg/m4a/mp3/wav/aac/3gp 등)을 ffmpeg 로 16kHz 모노 PCM 으로 바꾼 뒤,
Google 동기 인식 한도(1분)보다 짧은 조각으로 나눠 병렬 인식한다. 조각 경계는 가장 조용한 지점으로 잡는다.

ffmpeg 는 settings.FFMPEG_BINARY → PATH 의 ffmpeg → imageio-ffmpeg 내장 바이너리 순서로 찾는다.
"""
import logging
import os
import shutil
import subprocess
import tempfile
from array import array
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings

from apps.core.exceptions import ServiceError

from . import google

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
BYTES_PER_SECOND = SAMPLE_RATE * 2  # 16bit 모노
CHUNK_SECONDS = 55  # Google 동기 인식 한도(60초)보다 여유 있게
CUT_SEARCH_SECONDS = 5  # 조각 끝 5초 안에서 가장 조용한 곳을 찾아 자른다
FRAME_SECONDS = 0.1
CONVERT_TIMEOUT = 60
MAX_WORKERS = 4


class AudioDecodeError(Exception):
    """서버가 이 음성 파일을 해석하지 못함"""


def max_seconds() -> int:
    return int(getattr(settings, "VOICE_MAX_SECONDS", 300))


def max_upload_bytes() -> int:
    return int(getattr(settings, "VOICE_MAX_UPLOAD_MB", 25)) * 1024 * 1024


def ffmpeg_path() -> str | None:
    configured = getattr(settings, "FFMPEG_BINARY", "")
    if configured:
        return configured
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def to_pcm(data: bytes, limit_seconds: int) -> bytes:
    """음성 파일 → 16kHz 모노 s16le PCM. limit_seconds 보다 길면 audio_too_long.

    m4a 처럼 메타데이터가 파일 끝에 있는 형식은 파이프로 읽을 수 없어 임시 파일을 쓴다.
    """
    binary = ffmpeg_path()
    if not binary:
        raise AudioDecodeError("ffmpeg not available")
    fd, path = tempfile.mkstemp(suffix=".audio")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        # 한도 + 1초까지만 디코드해서, 아주 긴 파일도 변환 시간이 늘어나지 않게 한다.
        cmd = [binary, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", path, "-t", str(limit_seconds + 1),
               "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-acodec", "pcm_s16le", "pipe:1"]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=CONVERT_TIMEOUT, check=False)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise AudioDecodeError(type(e).__name__) from e
    finally:
        os.unlink(path)
    if proc.returncode != 0 or not proc.stdout:
        raise AudioDecodeError(proc.stderr.decode(errors="replace")[-300:])
    pcm = proc.stdout[: len(proc.stdout) - len(proc.stdout) % 2]
    if len(pcm) > limit_seconds * BYTES_PER_SECOND:
        raise ServiceError("audio_too_long", f"{limit_seconds // 60}분 이하의 음성만 번역할 수 있습니다.", 413)
    return pcm


def _quietest_cut(samples: array, start: int, end: int) -> int:
    """samples[start:end] 안에서 에너지가 가장 낮은 프레임의 시작 위치"""
    frame = int(SAMPLE_RATE * FRAME_SECONDS)
    best, best_energy = end, None
    for pos in range(start, end - frame + 1, frame):
        energy = sum(abs(s) for s in samples[pos:pos + frame])
        if best_energy is None or energy < best_energy:
            best, best_energy = pos, energy
    return best


def split_pcm(pcm: bytes, chunk_seconds: int = CHUNK_SECONDS) -> list[bytes]:
    samples = array("h")
    samples.frombytes(pcm)
    limit = chunk_seconds * SAMPLE_RATE
    search = CUT_SEARCH_SECONDS * SAMPLE_RATE
    chunks, start = [], 0
    while len(samples) - start > limit:
        cut = _quietest_cut(samples, start + limit - search, start + limit)
        chunks.append(samples[start:cut].tobytes())
        start = cut
    chunks.append(samples[start:].tobytes())
    return chunks


def transcribe(data: bytes, lang: str, encoding: str) -> tuple[str, float | None]:
    """음성 → (텍스트, 길이 초). 서버 변환이 불가능하면 기존처럼 클라이언트가 알려준 encoding 으로 그대로 보낸다."""
    try:
        pcm = to_pcm(data, max_seconds())
    except AudioDecodeError as e:
        logger.warning("audio conversion skipped: %s", e)
        if len(data) > google.MAX_INLINE_AUDIO:
            raise ServiceError("unsupported_audio", "음성 파일 형식을 해석할 수 없습니다.", 400) from e
        return google.speech_to_text(data, lang, encoding), None

    chunks = split_pcm(pcm)
    if len(chunks) == 1:
        texts = [google.speech_to_text(chunks[0], lang, "LINEAR16")]
    else:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            texts = list(pool.map(lambda c: google.speech_to_text(c, lang, "LINEAR16"), chunks))
    transcript = " ".join(t for t in texts if t)
    return transcript, round(len(pcm) / BYTES_PER_SECOND, 1)
