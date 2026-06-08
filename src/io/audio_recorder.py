import os
import tempfile
import wave
import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QThread, pyqtSignal

class AudioRecorder(QThread):
    """
    Background QThread worker for recording hardware microphone input.
    Records 16kHz mono audio (float32) in a non-blocking stream callback,
    and writes it to a 16-bit WAV file on disk when stopped.
    """
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(str)  # Emits the path of the temporary WAV file
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.device_index = None  # None triggers the system default microphone
        self.sample_rate = 16000  # 16kHz standard sample rate for Whisper
        self.channels = 1         # Mono channel
        self._is_recording = False
        self._audio_data = []

        # Voice Activity Detection (VAD) parameters
        self.speech_threshold = 0.012  # RMS energy to trigger speaking state
        self.silence_threshold = 0.008 # RMS energy to classify as silence
        self.silence_timeout = 1.6     # Seconds of silence to trigger auto-stop
        self.max_recording_time = 20.0 # Maximum time limit in seconds

    def set_device(self, device_index):
        """Sets the active input device index."""
        self.device_index = device_index

    def stop_recording(self):
        """Signals the recording loop to stop."""
        self._is_recording = False

    def run(self):
        self._audio_data = []
        self._is_recording = True

        # VAD State variables
        self.has_spoken = False
        self.silence_frames = 0
        self.total_recorded_frames = 0
        self.max_silence_frames = int(self.silence_timeout * self.sample_rate)
        self.max_recording_frames = int(self.max_recording_time * self.sample_rate)

        self.recording_started.emit()

        def stream_callback(indata, frames, time, status):
            if status:
                print(f"[AudioRecorder] Status del stream: {status}")
            
            self._audio_data.append(indata.copy())
            self.total_recorded_frames += frames

            # Calculate RMS energy of current audio block
            rms = np.sqrt(np.mean(np.square(indata)))

            if not self.has_spoken:
                # Detect voice starting
                if rms > self.speech_threshold:
                    self.has_spoken = True
                    self.silence_frames = 0
                    print(f"[AudioRecorder] Voz detectada (RMS: {rms:.4f})")
            else:
                # Voice has started, detect silence
                if rms < self.silence_threshold:
                    self.silence_frames += frames
                    if self.silence_frames >= self.max_silence_frames:
                        print(f"[AudioRecorder] Silencio detectado por {self.silence_frames / self.sample_rate:.1f}s. Parando grabación.")
                        self._is_recording = False
                else:
                    self.silence_frames = 0

            # Absolute maximum recording time limit fallback
            if self.total_recorded_frames >= self.max_recording_frames:
                print("[AudioRecorder] Tiempo máximo de grabación alcanzado. Parando.")
                self._is_recording = False

        try:
            # Query device info if a specific index was selected, or use default input device info
            target_device = self.device_index
            if target_device is None:
                try:
                    target_device = sd.default.device[0]
                except Exception:
                    pass

            channels_to_use = 1
            if target_device is not None and target_device >= 0:
                try:
                    device_info = sd.query_devices(target_device, 'input')
                    self.sample_rate = int(device_info.get('default_samplerate', 16000))
                    max_ch = int(device_info.get('max_input_channels', 1))
                    if max_ch > 0:
                        channels_to_use = min(2, max_ch)
                except Exception as e:
                    print(f"[AudioRecorder] Error consultando el dispositivo {target_device}: {e}")

            # Open and run the input stream
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=channels_to_use,
                device=self.device_index,
                callback=stream_callback,
                dtype='float32'
            ):
                while self._is_recording:
                    self.msleep(100)  # Brief sleep intervals

            # Save recorded frames to a WAV file
            if self._audio_data:
                # Concatenate all blocks to a single numpy array
                audio_np = np.concatenate(self._audio_data, axis=0)

                # Convert to mono if it has multiple channels
                if audio_np.ndim > 1 and audio_np.shape[1] > 1:
                    print(f"[AudioRecorder] Mezclando {audio_np.shape[1]} canales de audio a mono...")
                    audio_np = np.mean(audio_np, axis=1, keepdims=True)

                # Convert float32 [-1.0, 1.0] samples to 16-bit PCM integer samples
                audio_int16 = (audio_np * 32767.0).astype(np.int16)

                # Write WAV file to temporary directory
                temp_dir = tempfile.gettempdir()
                temp_wav_path = os.path.join(temp_dir, "lia_voice_recording.wav")

                with wave.open(temp_wav_path, "wb") as wf:
                    wf.setnchannels(1)  # Output is now always mono
                    wf.setsampwidth(2)  # 2 bytes per sample (16-bit)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(audio_int16.tobytes())

                print(f"[AudioRecorder] Grabación guardada exitosamente en: {temp_wav_path}")
                self.recording_stopped.emit(temp_wav_path)
            else:
                self.error_occurred.emit("No se recibieron datos de audio del micrófono.")

        except Exception as e:
            print(f"[AudioRecorder] Excepción durante la grabación: {e}")
            self.error_occurred.emit(str(e))
