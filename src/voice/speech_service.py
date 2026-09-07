"""
Speech Service - 音声文字起こし（複数バックエンド対応）

バックエンド切り替え:
  SPEECH_BACKEND = "openai-whisper"    # 従来のOpenAI Whisper (small)
  SPEECH_BACKEND = "faster-whisper"    # Faster-Whisper + large-v3-turbo (推奨)
  SPEECH_BACKEND = "kotoba-whisper"    # Kotoba-Whisper v2.0 (日本語特化)
"""
import tempfile
import os
import sys
import shutil
import logging
import streamlit as st

logger = logging.getLogger(__name__)

# ==========================================
# バックエンド選択（ここを変更して切り替え）
# ==========================================
SPEECH_BACKEND = "faster-whisper"


def _check_ffmpeg():
    """ffmpegの存在を確認し、なければインストール手順を案内"""
    if shutil.which("ffmpeg"):
        return True

    install_hints = {
        "win32":  "winget install ffmpeg  または  choco install ffmpeg",
        "darwin": "brew install ffmpeg",
        "linux":  "sudo apt install ffmpeg  または  sudo dnf install ffmpeg",
    }
    platform = sys.platform
    hint = install_hints.get(platform, install_hints["linux"])
    logger.warning(
        f"ffmpegが見つかりません。音声入力を使用するにはffmpegをインストールしてください:\n  {hint}"
    )
    return False


FFMPEG_AVAILABLE = _check_ffmpeg()

# ==========================================
# バックエンド別の依存チェック
# ==========================================
WHISPER_AVAILABLE = False

if SPEECH_BACKEND == "openai-whisper":
    try:
        import whisper
        WHISPER_AVAILABLE = True
    except ImportError:
        logger.warning("openai-whisper がインストールされていません: pip install openai-whisper")

elif SPEECH_BACKEND == "faster-whisper":
    try:
        from faster_whisper import WhisperModel
        WHISPER_AVAILABLE = True
    except ImportError:
        logger.warning("faster-whisper がインストールされていません: pip install faster-whisper")

elif SPEECH_BACKEND == "kotoba-whisper":
    try:
        import torch
        from transformers import pipeline as hf_pipeline
        WHISPER_AVAILABLE = True
    except ImportError:
        logger.warning("transformers/torch がインストールされていません: pip install transformers torch")

else:
    logger.error(f"不明なバックエンド: {SPEECH_BACKEND}")

# ==========================================
# モデルロード（キャッシュ付き）
# ==========================================

@st.cache_resource
def _load_openai_whisper(model_name="small"):
    import whisper
    return whisper.load_model(model_name)


@st.cache_resource
def _load_faster_whisper():
    from faster_whisper import WhisperModel
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    return WhisperModel(
        "deepdml/faster-whisper-large-v3-turbo-ct2",
        device=device,
        compute_type=compute_type,
    )


@st.cache_resource
def _load_kotoba_whisper():
    import torch
    from transformers import pipeline as hf_pipeline
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if device == "cuda" else torch.float32
    return hf_pipeline(
        "automatic-speech-recognition",
        model="kotoba-tech/kotoba-whisper-v2.0",
        torch_dtype=torch_dtype,
        device=device,
    )


def load_whisper_model():
    """現在のバックエンドに応じたモデルをロード"""
    if not WHISPER_AVAILABLE:
        raise ImportError(f"{SPEECH_BACKEND} がインストールされていません")
    if SPEECH_BACKEND == "openai-whisper":
        return _load_openai_whisper()
    elif SPEECH_BACKEND == "faster-whisper":
        return _load_faster_whisper()
    elif SPEECH_BACKEND == "kotoba-whisper":
        return _load_kotoba_whisper()


# ==========================================
# 文字起こし
# ==========================================

def _transcribe_openai_whisper(audio_bytes: bytes) -> str:
    model = load_whisper_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        result = model.transcribe(tmp_path, language="ja", fp16=False)
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)


def _transcribe_faster_whisper(audio_bytes: bytes) -> str:
    model = load_whisper_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        segments, _info = model.transcribe(tmp_path, language="ja", beam_size=5)
        return "".join(seg.text for seg in segments).strip()
    finally:
        os.unlink(tmp_path)


def _transcribe_kotoba_whisper(audio_bytes: bytes) -> str:
    pipe = load_whisper_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        result = pipe(tmp_path)
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)


_TRANSCRIBE_FN = {
    "openai-whisper": _transcribe_openai_whisper,
    "faster-whisper": _transcribe_faster_whisper,
    "kotoba-whisper": _transcribe_kotoba_whisper,
}


def transcribe_audio(audio_bytes: bytes) -> str:
    """WAV音声バイトを文字起こし（選択中のバックエンドを使用）"""
    if not FFMPEG_AVAILABLE:
        raise RuntimeError(
            "ffmpegがインストールされていません。"
            "音声入力を使用するにはffmpegをPATHに追加してください。"
        )
    return _TRANSCRIBE_FN[SPEECH_BACKEND](audio_bytes)
