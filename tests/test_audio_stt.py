import os
import numpy as np
from unittest.mock import MagicMock, patch
import pytest

from src.io.audio_recorder import AudioRecorder
from src.services.whisper_local import TranscriptionWorker

@patch("sounddevice.InputStream")
@patch("wave.open")
def test_audio_recorder_lifecycle(mock_wave_open, mock_input_stream):
    """
    Tests that AudioRecorder sets up the sounddevice input stream,
    safely stops, and writes the captured buffer as a WAV file.
    """
    recorder = AudioRecorder()
    recorder.device_index = 0
    recorder.sample_rate = 16000

    # Tracks signals
    signals_fired = {"started": False, "stopped": False}

    def on_started():
        signals_fired["started"] = True
        # Stop recording immediately to prevent looping
        recorder.stop_recording()

    recorder.recording_started.connect(on_started)
    recorder.recording_stopped.connect(lambda path: signals_fired.update({"stopped": True}))

    # Mock InputStream to trigger the stream callback upon instantiation
    def mock_input_stream_init(*args, **kwargs):
        callback = kwargs.get('callback')
        if callback:
            # Simulate receiving one block of audio
            callback(np.zeros((320, 1), dtype=np.float32), 320, None, None)
        # Return a mock context manager
        mock_cm = MagicMock()
        return mock_cm

    mock_input_stream.side_effect = mock_input_stream_init

    # Mock thread sleeps and query devices to run synchronously in test
    with patch("PyQt6.QtCore.QThread.msleep"), patch("sounddevice.query_devices") as mock_query:
        mock_query.return_value = {"default_samplerate": 16000}
        recorder.run()

    # Validate lifecycle signaling and wave writing
    assert signals_fired["started"] is True
    assert signals_fired["stopped"] is True
    mock_input_stream.assert_called_once()
    mock_wave_open.assert_called_once()


@patch("sounddevice.InputStream")
@patch("wave.open")
def test_audio_recorder_downmix(mock_wave_open, mock_input_stream):
    """
    Tests that AudioRecorder converts multichannel (stereo) input data to mono.
    """
    recorder = AudioRecorder()
    recorder.device_index = 0
    recorder.sample_rate = 16000

    # Mock InputStream to simulate receiving a stereo block
    def mock_input_stream_init(*args, **kwargs):
        callback = kwargs.get('callback')
        if callback:
            # Simulate receiving one block of stereo audio (320 frames, 2 channels)
            stereo_block = np.ones((320, 2), dtype=np.float32)
            # Left channel = 1.0, Right channel = -1.0 -> mean should be 0.0
            stereo_block[:, 0] = 1.0
            stereo_block[:, 1] = -1.0
            callback(stereo_block, 320, None, None)
        return MagicMock()

    mock_input_stream.side_effect = mock_input_stream_init

    # We mock wave.open to capture the bytes written
    mock_wf = MagicMock()
    mock_wave_open.return_value.__enter__.return_value = mock_wf

    with patch("PyQt6.QtCore.QThread.msleep"), \
         patch("sounddevice.query_devices") as mock_query, \
         patch("sounddevice.default.device", (0, 0)):
        mock_query.return_value = {"default_samplerate": 16000, "max_input_channels": 2}
        
        # Connect signal to stop recording after first callback execution
        recorder.recording_started.connect(recorder.stop_recording)
        recorder.run()

    # The mock wave.open context manager should have been called
    mock_wave_open.assert_called_once()
    
    # Verify we configured the WAV file to be MONO
    mock_wf.setnchannels.assert_called_once_with(1)
    
    # Retrieve the raw PCM bytes passed to writeframes
    called_args = mock_wf.writeframes.call_args[0][0]
    written_data = np.frombuffer(called_args, dtype=np.int16)
    assert len(written_data) == 320
    assert np.all(written_data == 0)


@patch("src.services.whisper_local.get_whisper_model")
def test_transcription_worker_execution(mock_get_model):
    """
    Tests that TranscriptionWorker resolves the WhisperModel,
    processes the audio segments, joins them, and emits transcription_completed.
    """
    # Create mock segments returned by faster-whisper
    mock_segment = MagicMock()
    mock_segment.text = "Hola LIA, abre la calculadora."
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], MagicMock())
    mock_get_model.return_value = mock_model

    worker = TranscriptionWorker("dummy_audio_path.wav")
    
    # Signal tracker
    received_text = []
    worker.transcription_completed.connect(received_text.append)

    # Mock file system check to bypass file existence check
    with patch("os.path.exists", return_value=True):
        worker.run()

    # Assert model was called and text segments were processed/joined
    assert len(received_text) == 1
    assert received_text[0] == "Hola LIA, abre la calculadora."
    mock_model.transcribe.assert_called_once_with("dummy_audio_path.wav", beam_size=3, language="es")
