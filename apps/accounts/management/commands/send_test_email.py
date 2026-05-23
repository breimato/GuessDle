from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email to verify SMTP configuration in production."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="Email address to send the test message to")

    def handle(self, *args, **options):
        recipient = options["recipient"]
        if not settings.EMAIL_HOST_USER or not settings.DEFAULT_FROM_EMAIL:
            raise CommandError(
                "Email is not configured. Set EMAIL_HOST_USER and DEFAULT_FROM_EMAIL in the environment."
            )

        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
        self.stdout.write(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

        send_mail(
            subject="GuessDle – correo de prueba",
            message="Si recibes este mensaje, el envío de correo está configurado correctamente.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Test email sent to {recipient}"))
