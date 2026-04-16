import asyncio
from fastapi import FastAPI
from .infrastructure.database import init_db, SessionLocal
from .api.endpoints import router
from .infrastructure.hardware.gpio_impl import (
    get_green_led, get_red_led, get_buzzer, get_door_relay, get_rfid_reader
)
from .domain.workflows import process_swipe

# Database Init
init_db()

app = FastAPI(title="RPi RFID Door Access API")

app.include_router(router)

# Hardware setup (Will fallback to mock or None if not on RPi as per gpio_impl logic)
# This loop simulates the background reading of the RFID scanner

reader = get_rfid_reader()
green_led = get_green_led()
red_led = get_red_led()
buzzer = get_buzzer()
relay = get_door_relay()

async def rfid_polling_task():
    """Background task to poll RFID reader."""
    while True:
        try:
            if reader and hasattr(reader, 'read_card'):
                card_id = reader.read_card()
                if card_id:
                    # Valid card picked up
                    with SessionLocal() as db:
                        process_swipe(
                            card_id=card_id,
                            db=db,
                            green_led=green_led,
                            red_led=red_led,
                            buzzer=buzzer,
                            relay=relay
                        )
            
            # Wait a bit before next poll to free CPU
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error in RFID loop: {e}")
            await asyncio.sleep(2.0)

@app.on_event("startup")
async def startup_event():
    # Start the RFID polling task in the background
    asyncio.create_task(rfid_polling_task())

