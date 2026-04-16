import asyncio
from fastapi import FastAPI
from app.infrastructure.database import init_db, SessionLocal
from app.api.endpoints import router as endpoints_router
from app.api.auth import router as auth_router
from app.infrastructure.hardware.gpio_impl import (
    get_green_led, get_red_led, get_buzzer, get_door_relay, get_rfid_reader
)
from app.domain.workflows import process_swipe
from app.core.config import settings

# Database Init
init_db()

app = FastAPI(title="RPi RFID Door Access API")

app.include_router(auth_router)
app.include_router(endpoints_router)

reader = get_rfid_reader()
green_led = get_green_led()
red_led = get_red_led()
buzzer = get_buzzer()
relay = get_door_relay()

async def rfid_polling_task():
    verbose = settings.VERBOSE
    if verbose:
        print("[RFID] Polling started — waiting for cards...")

    idle_ticks = 0
    while True:
        try:
            if reader and hasattr(reader, 'read_card'):
                card_id = reader.read_card()
                if card_id:
                    if verbose:
                        print(f"[RFID] Card detected: {card_id}")
                    with SessionLocal() as db:
                        result = process_swipe(
                            card_id=card_id,
                            db=db,
                            green_led=green_led,
                            red_led=red_led,
                            buzzer=buzzer,
                            relay=relay,
                            verbose=verbose,
                        )
                    if verbose:
                        print(f"[RFID] Result: {result}")
                    idle_ticks = 0
                else:
                    if verbose:
                        idle_ticks += 1
                        if idle_ticks % 20 == 0:
                            print("[RFID] No card — still polling...")
            else:
                if verbose:
                    idle_ticks += 1
                    if idle_ticks % 20 == 0:
                        print("[RFID] Reader unavailable — still waiting...")

            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[RFID] Error in polling loop: {e}")
            await asyncio.sleep(2.0)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(rfid_polling_task())
