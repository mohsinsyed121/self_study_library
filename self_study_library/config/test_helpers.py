"""Small factory functions shared by tests in every app."""
from datetime import date
from decimal import Decimal

from accounts.models import User
from memberships.models import MembershipPlan
from memberships.services import create_and_activate
from seats.models import Seat
from students.models import StudentProfile

PASSWORD = "Str0ng-pass-123"


def make_student(username="asha", approved=True, phone="9876543210"):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password=PASSWORD,
                                    first_name=username.title(), last_name="Test")
    profile = StudentProfile.objects.create(user=user, phone=phone)
    if approved:
        profile.approval_status = StudentProfile.Approval.APPROVED
        profile.save(update_fields=["approval_status"])
    return profile


def make_admin(username="boss"):
    return User.objects.create_user(username=username, email=f"{username}@example.com", password=PASSWORD, is_staff=True)


def make_plan(name="Monthly", days=30, price="1000.00"):
    return MembershipPlan.objects.create(name=name, duration_days=days, price=Decimal(price))


def make_seat(number="A1"):
    return Seat.objects.create(number=number)


def make_member(username="asha", plan=None):
    """An approved student with an ACTIVE membership (and therefore a fee record)."""
    student = make_student(username)
    membership = create_and_activate(student, plan or make_plan(name=f"Plan-{username}"))
    return student, membership
