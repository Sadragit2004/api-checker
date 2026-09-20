from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):

    def get_by_natural_key(self, mobile_number):
        return self.get(
            **{
                f"{self.model.USERNAME_FIELD}__iexact": mobile_number,
            }
        )

    def create_user(self, mobile_number, password=None, **extra_fields):
        if not mobile_number:
            raise ValueError("Mobile number is required.")

        user = self.model(
            mobile_number=mobile_number,
            **extra_fields,
        )

        if password:
            user.set_password(password)

        user.save(
            using=self._db,
        )

        return user

    def create_superuser(self, mobile_number, password=None, **extra_fields):
        extra_fields.setdefault(
            "is_staff",
            True,
        )

        extra_fields.setdefault(
            "is_superuser",
            True,
        )

        extra_fields.setdefault(
            "is_active",
            True,
        )

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "Superuser must have is_staff=True."
            )

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "Superuser must have is_superuser=True."
            )

        return self.create_user(
            mobile_number=mobile_number,
            password=password,
            **extra_fields,
        )