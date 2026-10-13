from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from config.test_helpers import PASSWORD, make_member, make_seat, make_student
from seats.models import SeatBooking
from seats.services import (BookingError, allocate_seat, cancel_booking, confirm_booking,
                            reassign_booking, request_seat, seat_counts)


class BookingRuleTests(TestCase):
    def setUp(self):
        self.asha, _ = make_member("asha")
        self.ravi, _ = make_member("ravi")
        self.seat = make_seat("A1")

    def test_book_seat_reserves_it(self):
        booking = request_seat(self.asha, self.seat)
        self.assertEqual(booking.status, SeatBooking.RESERVED)
        self.assertEqual(self.seat.status, "reserved")
        self.assertTrue(self.asha.user.notifications.filter(title="Seat reserved").exists())

    def test_two_students_cannot_book_same_seat(self):
        request_seat(self.asha, self.seat)
        with self.assertRaises(BookingError):
            request_seat(self.ravi, self.seat)
        self.assertEqual(SeatBooking.objects.filter(seat=self.seat, status__in=["reserved", "allocated"]).count(), 1)

    def test_database_constraint_blocks_double_booking(self):
        SeatBooking.objects.create(student=self.asha, seat=self.seat, status="allocated")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SeatBooking.objects.create(student=self.ravi, seat=self.seat, status="reserved")

    def test_database_constraint_one_seat_per_student(self):
        SeatBooking.objects.create(student=self.asha, seat=self.seat, status="reserved")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SeatBooking.objects.create(student=self.asha, seat=make_seat("A2"), status="reserved")

    def test_student_cannot_hold_two_seats(self):
        request_seat(self.asha, self.seat)
        with self.assertRaises(BookingError):
            request_seat(self.asha, make_seat("A2"))

    def test_needs_membership_and_approval(self):
        no_plan = make_student("noplan")
        with self.assertRaises(BookingError):
            request_seat(no_plan, self.seat)
        pending = make_student("pend", approved=False)
        with self.assertRaises(BookingError):
            request_seat(pending, self.seat)

    def test_inactive_seat_cannot_be_booked(self):
        self.seat.is_active = False
        self.seat.save()
        with self.assertRaises(BookingError):
            request_seat(self.asha, self.seat)

    def test_confirm_then_occupied(self):
        booking = request_seat(self.asha, self.seat)
        confirm_booking(booking)
        self.seat = type(self.seat).objects.get(pk=self.seat.pk)
        self.assertEqual(self.seat.status, "occupied")

    def test_cancel_frees_seat_and_keeps_history(self):
        booking = request_seat(self.asha, self.seat)
        cancel_booking(booking)
        self.assertEqual(type(self.seat).objects.get(pk=self.seat.pk).status, "available")
        self.assertEqual(SeatBooking.objects.filter(status="cancelled").count(), 1)
        request_seat(self.ravi, self.seat)  # now free for someone else

    def test_reassign_moves_student_and_keeps_history(self):
        booking = allocate_seat(self.asha, self.seat)
        new_seat = make_seat("B1")
        new_booking = reassign_booking(booking, new_seat)
        self.assertEqual(new_booking.seat, new_seat)
        self.assertEqual(new_booking.status, "allocated")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "ended")

    def test_cannot_reassign_to_taken_seat(self):
        booking = allocate_seat(self.asha, self.seat)
        other = make_seat("B1")
        allocate_seat(self.ravi, other)
        with self.assertRaises(BookingError):
            reassign_booking(booking, other)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "allocated")  # nothing changed

    def test_seat_counts(self):
        make_seat("A2"); make_seat("A3")
        request_seat(self.asha, self.seat)
        allocate_seat(self.ravi, make_seat("A4"))
        self.assertEqual(seat_counts(), {"total": 4, "occupied": 1, "reserved": 1, "available": 2, "inactive": 0})


class SeatViewTests(TestCase):
    def setUp(self):
        self.asha, _ = make_member("asha")
        self.seat = make_seat("A1")
        self.client.login(username="asha", password=PASSWORD)

    def test_seat_map_shows_seats(self):
        self.assertContains(self.client.get(reverse("available_seats")), "A1")

    def test_book_via_view(self):
        response = self.client.post(reverse("book_seat", args=[self.seat.pk]))
        booking = SeatBooking.objects.get()
        self.assertRedirects(response, reverse("booking_confirmation", args=[booking.pk]))

    def test_cannot_cancel_someone_elses_booking(self):
        ravi, _ = make_member("ravi")
        booking = allocate_seat(ravi, self.seat)
        response = self.client.post(reverse("cancel_my_booking", args=[booking.pk]))
        self.assertEqual(response.status_code, 404)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "allocated")

    def test_cancel_requires_post(self):
        booking = request_seat(self.asha, self.seat)
        self.assertEqual(self.client.get(reverse("cancel_my_booking", args=[booking.pk])).status_code, 405)
