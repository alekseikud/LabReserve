from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from accounts.models import User


class Command(BaseCommand):
    help = "Create a user with a role; prompt for the password without showing it."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("email")
        parser.add_argument("--role", choices=User.Role.values, default=User.Role.STUDENT)

    def handle(self, *args, **options):
        user = User(username=options["username"], email=options["email"], role=options["role"])
        password = getpass("Password: ")
        if password != getpass("Password again: "):
            raise CommandError("Passwords do not match.")
        try:
            validate_password(password, user)
            user.set_password(password)
            user.full_clean()
            user.save()
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        except IntegrityError as error:
            raise CommandError("Username or email already exists.") from error
        self.stdout.write(f"Created {user.username} ({user.role}).")
