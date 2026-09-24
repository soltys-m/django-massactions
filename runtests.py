#!/usr/bin/env python
"""Run the test suite without pytest: python runtests.py [massactions.tests.test_views ...]"""
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'massactions.tests.settings')
    django.setup()
    failures = get_runner(settings)(verbosity=1).run_tests(sys.argv[1:] or ['massactions.tests'])
    sys.exit(bool(failures))
