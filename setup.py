# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='md5s3stash',
    description='content addressable storage in AWS S3',
    long_description=read('README.md'),
    version='0.2.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
    ],
    maintainer="Brian Tingle",
    maintainer_email='brian.tingle.cdlib.org@gmail.com',
    packages=find_packages(),
    install_requires=['boto', 'basin', 'pilbox'],
    url='https://github.com/tingletech/md5s3stash',
    py_modules=['md5s3stash','thumbnail'],
    entry_points={
        'console_scripts': [
            'md5s3stash = md5s3stash:main',
            'thumbnail_server = thumbnail:main',
        ]
    },
    # test_suite='test',
)
