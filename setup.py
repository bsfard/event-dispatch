from setuptools import setup, find_packages

setup(
    name='eventdispatch',
    version='0.0.4',
    author='Ben Sfard',
    author_email='bsfard@gmail.com',
    url='https://github.com/bsfard/event-dispatch',
    packages=find_packages(),

    install_requires=[
        'wrapt==1.15.0',
    ]
)
