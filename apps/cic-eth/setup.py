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

admin_requirements = []
f = open('admin_requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    admin_requirements.append(l.rstrip())
f.close()



tools_requirements = []
f = open('tools_requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    tools_requirements.append(l.rstrip())
f.close()


services_requirements = []
f = open('services_requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    services_requirements.append(l.rstrip())
f.close()

setup(
    install_requires=requirements,
    extras_require = {
        'tools': tools_requirements,
        'admin_api': admin_requirements,
        'services': services_requirements,
        }
    )
