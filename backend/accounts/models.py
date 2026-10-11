from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        MANAGER = "manager", "Laboratory manager"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STUDENT)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=["student", "manager", "admin"]),
                name="user_valid_role",
            )
        ]
