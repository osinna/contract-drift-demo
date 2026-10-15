"""Тести «як пишуть зазвичай»: статус-код і наявність кількох полів."""


def test_list_events(api):
    response = api.get("/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) > 0
    assert "id" in events[0]


def test_list_seats(api):
    response = api.get("/events/1/seats")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_book_free_seat(api):
    response = api.post("/bookings", json={"event_id": 1, "seat_id": 1})
    assert response.status_code == 200
    assert "id" in response.json()
