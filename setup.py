# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='md5s3stash',
    description='content addressable storage in AWS S3',
    long_description=read('README.md'),
    version='0.3.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
    ],
    maintainer="Brian Tingle",
    maintainer_email='brian.tingle.cdlib.org@gmail.com',
    packages=find_packages(),
    #NOTE: 20140926 - the pilbox install failing on travis & new virtualenvs
    # need to point directly at source pilbox-1.0.3.tar.gz so that
    # dumb binary pilbox-1.0.3.linux-x86_64.tar.gz is not the file downloaded
    # setuptools wants source code. Check PyPi to see if fixed...
    dependency_links = [
            'https://pypi.python.org/packages/source/p/pilbox/pilbox-1.0.3.tar.gz#md5=514a99f784a4c06242144a005322fe52#egg=pilbox', 
            'https://github.com/mredar/redis-collections/archive/master.zip#egg=redis-collections',
            ],
    install_requires=['boto', 'basin', 'pilbox', 'python-magic'],
    url='https://github.com/tingletech/md5s3stash',
    py_modules=['md5s3stash','thumbnail'],
    entry_points={
        'console_scripts': [
            'md5s3stash = md5s3stash:main',
        ]
    },
    test_suite='tests',
    tests_require=['mock', 'unittest2', 'redis_collections', 'HTTPretty']
)
