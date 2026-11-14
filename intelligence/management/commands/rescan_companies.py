"""
Re-scan every active business that has a website URL and print what changed.

    python manage.py rescan_companies
    python manage.py rescan_companies --business <uuid>

Schedule it (cron on Linux/macOS, Task Scheduler on Windows) for periodic checks.
It is the only "monitoring" this project does: there is no always-on watcher.
"""

from django.core.management.base import BaseCommand

from businesses.models import BusinessProfile
from intelligence.models import CompanyScan
from intelligence.services.scan_service import scan_steps


class Command(BaseCommand):
    help = "Re-scan company websites and create alerts for changes since the last scan."

    def add_arguments(self, parser):
        parser.add_argument("--business", help="Only this business id")

    def handle(self, *args, **options):
        businesses = BusinessProfile.objects.active().exclude(website_url="")
        if options["business"]:
            businesses = businesses.filter(pk=options["business"])
        if not businesses:
            self.stdout.write("No active businesses with a website URL.")
            return
        for business in businesses:
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"{business.name}: {business.website_url}")
            )
            scan = CompanyScan.objects.create(business=business, url=business.website_url)
            for step in scan_steps(scan):
                self.stdout.write(f"  [{step['step']}] {step['message']}")
