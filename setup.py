from setuptools import setup, find_packages

setup(
    name='eventdispatch',
    version='0.0.6',
    author='Ben Sfard',
    author_email='bsfard@gmail.com',
    url='https://github.com/bsfard/event-dispatch',
    packages=find_packages(),

    install_requires=[
        'wrapt==1.16.0',
    ]
)
