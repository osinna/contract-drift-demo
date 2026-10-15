"""Сервіс бронювання квитків для демо «Контракт бреше».

Контракт — у openapi.yaml (написаний руками). Автогенерація OpenAPI вимкнена.
Прапорець DRIFT вмикає чотири навмисні розходження з контрактом.
Прапорець RAW_ERRORS повертає помилки фреймворку в стандартному вигляді FastAPI.
"""

import copy
import os

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictInt
from starlette.exceptions import HTTPException

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

# --- Дані (фіксовані, в памʼяті) -------------------------------------------

EVENTS = [
    {"id": 1, "title": "QA Conference 2027", "venue": "Kyiv, Main Hall",
     "starts_at": "2027-03-20T10:00:00Z"},
    {"id": 2, "title": "API Testing Meetup", "venue": "Lviv, Room 42",
     "starts_at": "2027-04-15T18:30:00Z"},
]

PRICES = {1: 1500.0, 2: 1000.0, 3: 500.0}  # ціна за рядом


def initial_seats():
    seats, seat_id = {}, 1
    for event in EVENTS:
        seats[event["id"]] = []
        for row in (1, 2, 3):
            for number in (1, 2, 3, 4):
                seats[event["id"]].append({
                    "id": seat_id, "row": row, "number": number,
                    "price": PRICES[row], "available": True,
                })
                seat_id += 1
    return seats


state = {
    "drift": os.getenv("DRIFT") == "1",
    "raw_errors": os.getenv("RAW_ERRORS") == "1",
    "seats": initial_seats(),
    "bookings": [],
}


def error(status, code, message, headers=None):
    return JSONResponse(status_code=status, content={"error": code, "message": message},
                        headers=headers)


@app.exception_handler(RequestValidationError)
async def bad_request(request: Request, exc: RequestValidationError):
    if state["raw_errors"]:
        return await request_validation_exception_handler(request, exc)  # 422 як у FastAPI
    # Замість недокументованого 422 від FastAPI — задокументований 400.
    return error(400, "BAD_REQUEST", "Request is invalid")


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if state["raw_errors"]:
        return await http_exception_handler(request, exc)  # {"detail": ...} як у FastAPI
    # Помилки фреймворку (битий JSON, 404, 405) — теж у форматі Error з контракту.
    return error(exc.status_code, "HTTP_ERROR", str(exc.detail), exc.headers)


# --- Контракт ---------------------------------------------------------------

@app.get("/events")
def list_events():
    events = copy.deepcopy(EVENTS)
    if state["drift"]:
        events[1]["venue"] = None  # дрейф 3: venue null у події 2
    return events


@app.get("/events/{event_id}/seats")
def list_seats(event_id: int):
    if event_id not in state["seats"]:
        return error(404, "EVENT_NOT_FOUND", f"Event {event_id} not found")
    seats = copy.deepcopy(state["seats"][event_id])
    if state["drift"]:
        for seat in seats:
            seat["row"] = str(seat["row"])  # дрейф 1: row рядком
    return seats


class BookingIn(BaseModel):
    event_id: StrictInt
    seat_id: StrictInt


@app.post("/bookings")
def create_booking(body: BookingIn):
    seats = state["seats"].get(body.event_id)
    if seats is None:
        return error(404, "EVENT_NOT_FOUND", f"Event {body.event_id} not found")
    seat = next((s for s in seats if s["id"] == body.seat_id), None)
    if seat is None:
        return error(404, "SEAT_NOT_FOUND", f"Seat {body.seat_id} not found")

    if not seat["available"]:
        message = f"Seat {body.seat_id} is already booked"
        if state["drift"]:
            # дрейф 4: помилка з кодом 200 замість 409
            return {"error": "SEAT_TAKEN", "message": message}
        return error(409, "SEAT_TAKEN", message)

    seat["available"] = False
    booking = {
        "id": len(state["bookings"]) + 1,
        "event_id": body.event_id,
        "seat_id": body.seat_id,
        # дрейф 2: статус поза enum
        "status": "PENDING_PAYMENT" if state["drift"] else "CONFIRMED",
    }
    state["bookings"].append(booking)
    return booking


# --- Службові ендпоінти (НЕ в контракті) ------------------------------------

class FlagIn(BaseModel):
    enabled: bool


@app.post("/_admin/drift")
def set_drift(body: FlagIn):
    state["drift"] = body.enabled
    return {"drift": state["drift"]}


@app.post("/_admin/raw-errors")
def set_raw_errors(body: FlagIn):
    state["raw_errors"] = body.enabled
    return {"raw_errors": state["raw_errors"]}


@app.post("/_admin/reset")
def reset():
    state["seats"] = initial_seats()
    state["bookings"] = []
    return get_state()


@app.get("/_admin/state")
def get_state():
    return {"drift": state["drift"], "raw_errors": state["raw_errors"]}
