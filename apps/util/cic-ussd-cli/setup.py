# standard imports
from setuptools import setup


requirements = []
with open('requirements.txt', 'r') as requirements_file:
   for requirement in requirements_file:
       requirements.append(requirement.rstrip())


setup(
    install_requires=requirements,
)
