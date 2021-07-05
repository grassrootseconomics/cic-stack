from setuptools import setup
import configparser
import os

requirements = []
f = open('requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    requirements.append(l.rstrip())
f.close()


setup(
    install_requires=requirements,
        )
