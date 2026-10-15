"""Ті самі запити + валідація відповіді проти openapi.yaml."""


def test_list_events(api, contract):
    response = api.get("/events")
    contract.validate(response)  # валідується весь масив, а не перший елемент


def test_list_seats(api, contract):
    response = api.get("/events/1/seats")
    contract.validate(response)


def test_book_free_seat(api, contract):
    response = api.post("/bookings", json={"event_id": 1, "seat_id": 1})
    contract.validate(response)


def test_book_taken_seat(api, contract):
    api.post("/bookings", json={"event_id": 1, "seat_id": 1})
    response = api.post("/bookings", json={"event_id": 1, "seat_id": 1})
    contract.validate(response)  # лише схема, статус-код не перевіряємо
