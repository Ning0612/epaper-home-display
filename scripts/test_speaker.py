"""Hardware test: USB speaker via aplay. Run on Pi: python -m scripts.test_speaker"""
from __future__ import annotations

import subprocess
import sys
import os


def main() -> None:
    sound_dir = "assets/sounds"
    wav_files = [f for f in os.listdir(sound_dir) if f.endswith(".wav")] if os.path.exists(sound_dir) else []

    if not wav_files:
        print("No .wav files found in assets/sounds/ — generating test tone ...")
        _generate_test_tone("/tmp/agent2_test.wav")
        test_file = "/tmp/agent2_test.wav"
    else:
        test_file = os.path.join(sound_dir, wav_files[0])
        print(f"Playing: {test_file}")

    result = subprocess.run(["aplay", test_file], capture_output=True)
    if result.returncode == 0:
        print("PASS")
    else:
        print(f"FAIL: aplay returned {result.returncode}")
        print(result.stderr.decode())
        sys.exit(1)


def _generate_test_tone(path: str) -> None:
    import struct, math, wave
    sample_rate = 44100
    duration = 1
    freq = 440
    samples = [int(32767 * math.sin(2 * math.pi * freq * t / sample_rate)) for t in range(sample_rate * duration)]
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))


if __name__ == "__main__":
    main()
