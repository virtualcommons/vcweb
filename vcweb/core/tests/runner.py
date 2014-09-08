import logging
from django.conf import settings
from django.test.runner import DiscoverRunner


class VcwebTestRunner(DiscoverRunner):

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        logging.disable(settings.DISABLED_TEST_LOGLEVEL)
        return super(VcwebTestRunner, self).run_tests(test_labels, extra_tests, **kwargs)
