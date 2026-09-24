#!/usr/bin/env python
from setuptools import setup, find_packages

from massactions import VERSION

setup(
    name='django-massactions',
    version=VERSION,
    description='Mass (bulk) actions for Django list views: selection, confirmation modals, delete and field update.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Michal Šoltys @ MS Code',
    maintainer='MS Code',
    url='https://github.com/soltys-m/django-massactions',
    packages=find_packages(exclude=['massactions.tests', 'massactions.tests.*']),
    include_package_data=True,
    python_requires='>=3.8',
    install_requires=[
        'django>=3.2',
        'django-crispy-forms>=1.14',
        'crispy-bootstrap5',
        'django-bootstrap-modal-forms>=2.2',
        'pycryptodome',
    ],
    extras_require={
        'filters': ['django-filter'],
    },
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.2',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Development Status :: 3 - Alpha',
    ],
    license='GPLv2',
    keywords='django massaction bulk action list selection modal',
)
