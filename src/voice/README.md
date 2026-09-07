# `src/voice` — voice input

`speech_service.py` transcribes a WAV recording (bytes) to text so that experimental
conditions can be dictated when both hands are occupied. The text is then passed to
the AI agent exactly like typed input.

```python
from src.voice.speech_service import transcribe_audio
text = transcribe_audio(wav_bytes)
```

In the GUI the recording comes from the `streamlit-mic-recorder` button.

## Backends

Selected with the `SPEECH_BACKEND` constant at the top of the file:

| Backend | Model | Package | Notes |
|---|---|---|---|
| `faster-whisper` (default) | `whisper-large-v3-turbo` (CTranslate2 build `deepdml/faster-whisper-large-v3-turbo-ct2`) | `faster-whisper` | Used in the paper. GPU → float16, CPU → int8. |
| `openai-whisper` | `small` | `openai-whisper` | Reference implementation, slower |
| `kotoba-whisper` | `kotoba-tech/kotoba-whisper-v2.0` | `transformers`, `torch` | Japanese-specialised |

Models are downloaded from Hugging Face on first use and cached by Streamlit
(`st.cache_resource`) for the session. Transcription language is fixed to Japanese
(`language="ja"`); change it in the `_transcribe_*` functions for other languages.

## Requirements

- `ffmpeg` on PATH (audio decoding). `winget install ffmpeg`, `brew install ffmpeg`,
  or `apt install ffmpeg`. Without it `transcribe_audio` raises a clear error and the
  GUI hides the microphone.
- No API key is needed; everything runs locally.
