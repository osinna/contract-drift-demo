"""Поведінка, яку схема не описує."""


def test_book_taken_seat_returns_409(api):
    api.post("/bookings", json={"event_id": 1, "seat_id": 1})
    response = api.post("/bookings", json={"event_id": 1, "seat_id": 1})
    assert response.status_code == 409
