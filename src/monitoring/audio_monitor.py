import sounddevice as sd
import numpy as np
import queue
import threading

class AudioMonitor:
    def __init__(self, samplerate=16000, blocksize=1024, energy_threshold=0.02):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.energy_threshold = energy_threshold
        self.q = queue.Queue()
        self.noise_detected = False
        self.running = False

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.q.put(indata.copy())

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor)
        self.thread.start()
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            blocksize=self.blocksize,
            callback=self._audio_callback
        )
        self.stream.start()

    def stop(self):
        self.running = False
        self.stream.stop()
        self.stream.close()
        self.thread.join()

    def _monitor(self):
        while self.running:
            try:
                block = self.q.get(timeout=1)
                energy = np.sqrt(np.mean(block**2))
                self.noise_detected = energy > self.energy_threshold
            except queue.Empty:
                continue

    def is_noise(self):
        return self.noise_detected

# Example usage:
if __name__ == "__main__":
    audio_monitor = AudioMonitor()
    audio_monitor.start()
    print("Listening for noise/talking... Press Ctrl+C to stop.")
    try:
        while True:
            if audio_monitor.is_noise():
                print("Noise/Talking detected!")
    except KeyboardInterrupt:
        audio_monitor.stop()
        print("Stopped.")
