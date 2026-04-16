import datetime
from typing import Tuple, Dict, Any
from sqlalchemy.orm import Session
from ..infrastructure.models import AccountModel, AccessLogModel
from ..infrastructure.hardware.interfaces import LedIndicator, Buzzer, DoorRelay

def log_access(db: Session, account_id: str, event_type: str, reason: str = None) -> None:
    log_entry = AccessLogModel(
        account_id=account_id,
        event_type=event_type,
        reason=reason,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(log_entry)
    db.commit()

def grant_access(db: Session, account: AccountModel, green_led: LedIndicator, buzzer: Buzzer, relay: DoorRelay) -> None:
    # Action Sequence:
    # 1. Emits 1 positive Beep.
    buzzer.beep(times=1, duration=0.2)
    # 2. Activate Green LED.
    green_led.on()
    
    try:
        # 3. Trigger Relay
        relay.trigger(seconds=5.0)
    finally:
        green_led.off()
        
    # Decrement credits
    account.credits -= 1
    db.commit()
    
    # Log Access
    log_access(db, account.account_id, "grant")


def deny_access(db: Session, account_id: str, reason: str, red_led: LedIndicator, buzzer: Buzzer) -> None:
    if reason == "Out of Credits":
        buzzer.beep(times=3, duration=0.2)
    else:
        buzzer.beep(times=1, duration=0.5) # Different error beep
        
    red_led.on()
    # Keep door locked (do nothing)
    # Usually we might wait a bit so the LED stays on
    import time
    time.sleep(1.0)
    red_led.off()

    # Log denial
    log_access(db, account_id, "deny", reason)


def process_swipe(
    card_id: str,
    db: Session,
    green_led: LedIndicator,
    red_led: LedIndicator,
    buzzer: Buzzer,
    relay: DoorRelay
) -> Dict[str, Any]:
    
    account = db.query(AccountModel).filter(AccountModel.account_id == card_id).first()
    
    if not account:
        deny_access(db, card_id, "Not Found", red_led, buzzer)
        return {"status": "denied", "reason": "Not Found"}
        
    if account.status != "active":
        deny_access(db, card_id, "Invalid Status", red_led, buzzer)
        return {"status": "denied", "reason": "Invalid Status"}
        
    if account.expiration_date < datetime.datetime.utcnow():
        deny_access(db, card_id, "Expired", red_led, buzzer)
        return {"status": "denied", "reason": "Expired"}
        
    if account.credits <= 0:
        deny_access(db, card_id, "Out of Credits", red_led, buzzer)
        return {"status": "denied", "reason": "Out of Credits"}
        
    # All validations passed
    grant_access(db, account, green_led, buzzer, relay)
    return {"status": "granted"}
