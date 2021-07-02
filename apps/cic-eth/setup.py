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


aux_requirements = []
f = open('aux_requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    aux_requirements.append(l.rstrip())
f.close()

setup(
    install_requires=requirements,
    extras_require={
        'aux': aux_requirements,
        }
        )
