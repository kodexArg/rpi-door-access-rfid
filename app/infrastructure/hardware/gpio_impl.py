import time
from gpiozero import LED, Buzzer as GpioBuzzer, OutputDevice
from app.infrastructure.hardware.interfaces import LedIndicator, Buzzer, DoorRelay, RFIDReader
from app.core.config import settings

class GpioLedIndicator(LedIndicator):
    def __init__(self, pin: int):
        self.led = LED(pin)

    def on(self):
        self.led.on()

    def off(self):
        self.led.off()

class GpioBuzzerImpl(Buzzer):
    def __init__(self, pin: int):
        self.buzzer = GpioBuzzer(pin)

    def beep(self, times: int = 1, duration: float = 0.2):
        for _ in range(times):
            self.buzzer.on()
            time.sleep(duration)
            self.buzzer.off()
            time.sleep(duration)

class GpioDoorRelay(DoorRelay):
    def __init__(self, pin: int):
        # Using OutputDevice for Relay. Active high or low depends on the relay module.
        # Most 5V relay modules are active low.
        self.relay = OutputDevice(pin, active_high=False, initial_value=False)

    def trigger(self, seconds: float = 5.0):
        self.relay.on()
        time.sleep(seconds)
        self.relay.off()

class Mfrc522RFIDReader(RFIDReader):
    def __init__(self):
        try:
            from mfrc522 import SimpleMFRC522
            import RPi.GPIO as GPIO
            # mfrc522 resets via pin 22 usually, but we want to make sure it matches SPI
            # The library manages its own pins, but we can set it up
            self.reader = SimpleMFRC522()
        except ImportError:
            self.reader = None
            print("MFRC522 or RPi.GPIO not installed. Using mock reader fallback.")
        except RuntimeError:
            self.reader = None
            print("Not running on a Raspberry Pi. Using mock reader fallback.")

    def read_card(self) -> str | None:
        if self.reader is None:
            return None
        try:
            id, text = self.reader.read_no_block()
            if id is not None:
                return str(id)
            return None
        except Exception as e:
            print(f"Error reading card: {e}")
            return None
        finally:
            # We don't cleanup here as we might poll continuously
            pass

# Dependency Injection Containers for Production
def get_green_led() -> LedIndicator:
    return GpioLedIndicator(settings.LED_GREEN_PIN)

def get_red_led() -> LedIndicator:
    return GpioLedIndicator(settings.LED_RED_PIN)

def get_buzzer() -> Buzzer:
    return GpioBuzzerImpl(settings.BUZZER_PIN)

def get_door_relay() -> DoorRelay:
    return GpioDoorRelay(settings.RELAY_PIN)

def get_rfid_reader() -> RFIDReader:
    return Mfrc522RFIDReader()
