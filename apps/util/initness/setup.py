from setuptools import setup

f = open('requirements.txt', 'r')
requirements = f.read()
f.close()

setup(
        name='initness',
        version='0.0.1a1',
        install_requires=requirements,
        packages=[
            'initness',
            'initness.runnable',
            ],
        include_package_data=True,
        entry_points = {
            'console_scripts': [
                'cic-init-server=initness.runnable.server:main',
            ],
            },
        )
