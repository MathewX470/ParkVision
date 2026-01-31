from fastapi import FastAPI
import json

app = FastAPI()

@app.get("/parking/status")
def parking_status():
    with open("parking_slots.json") as f:
        slots = json.load(f)
    return {
        "total_slots": len(slots),
        "free": 5,
        "occupied": 10
    }