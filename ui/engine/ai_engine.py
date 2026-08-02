import threading

from speech import listen
from router import process
from speech_engine import speak


class AIEngine:

    def __init__(self, ui):

        self.ui = ui
        self.running = False
        self.thread = None

    def start(self):

        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self.loop,
            daemon=True
        )

        self.thread.start()

    def stop(self):

        self.running = False

    def loop(self):

        while self.running:

            self.ui.set_listening()

            command = listen()

            if not command:
                continue

            self.ui.set_thinking()

            running, answer = process(command)

            if answer:

                self.ui.set_speaking()

                speak(answer)

            if running is False:

                self.running = False

                self.ui.close()

                break

            self.ui.set_idle()