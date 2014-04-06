
from setuptools import setup, find_packages

setup(name='juju-slayer',
      version="0.1.0",
      classifiers=[
          'Intended Audience :: Developers',
          'Programming Language :: Python',
          'Operating System :: OS Independent'],
      author='Kapil Thangavelu',
      author_email='kapil.foss@gmail.com',
      description="Softlayer integration with juju",
      long_description=open("README.rst").read(),
      url='https://github.com/kapilt/juju-softlayer',
      license='BSD',
      packages=find_packages(),
      install_requires=["PyYAML", "requests", "SoftLayer"],
      entry_points={
          "console_scripts": [
              'juju-sl = juju_slayer.cli:main']},
      )
