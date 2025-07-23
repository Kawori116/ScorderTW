from django.core.management.base import BaseCommand
from django.utils import timezone
from app_customer_interface.models import Order

class Command(BaseCommand):
    help = 'Deletes orders not from today'

    def handle(self, *args, **kwargs):
        
        yesterday = timezone.now() - timezone.timedelta(days=1)
        yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)

        Order.objects.filter(timestamp__lte=yesterday_start).delete()

        self.stdout.write(self.style.SUCCESS('Successfully deleted old orders'))
