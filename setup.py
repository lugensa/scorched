from __future__ import unicode_literals
import os
from setuptools import setup, find_packages

version = '0.7'

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()


setup(name='scorched',
      version=version,
      description="solr search orm like query builder",
      long_description=README + '\n\n' + CHANGES,
      classifiers=[],
      keywords='solr tow sunburnt offspring',
      author='(Josip Delic) Lugensa GmbH',
      author_email='info@lugensa.com',
      url='http://www.lugensa.com',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "setuptools",
          "requests",
          "nose",
          "coverage",
          "mock",
          "pytz",
      ],
      test_suite='scorched.tests',
      setup_requires=["setuptools_git"],
      )
