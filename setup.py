#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='django-massactions',
    description='Django app for bulk actions in the object lists.',
    long_description=open('README.md').read(),
    author='MS Code',
    maintainer='MS Code',
    url='https://github.com/soltys-m/django-massactions',
    packages=find_packages(),
    include_package_data=True,
    install_requires=('django>=3.2', 'pycryptodome'),
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Framework :: Django',
        'License :: OSI Approved :: BSD License',
        'Development Status :: 3 - Alpha'
    ],
    license='BSD License',
    keywords="django massaction bulk action",
)