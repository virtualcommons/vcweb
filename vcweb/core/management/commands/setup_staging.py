from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from vcweb.core.utils import confirm

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup staging environment, changes all emails to a mailinator.com address'
    DEFAULT_STAGING_EMAIL = 'vcweb@mailinator.com'

    def add_arguments(self, parser):
        parser.add_argument('--email', dest='email', required=False, default=self.DEFAULT_STAGING_EMAIL,
                            help='Update ALL users with this email address. Default is vcweb@mailinator.com')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options.get('email')
        if confirm("Change all emails to {}? (y/n) ".format(email)):
            User.objects.update(email=email)
