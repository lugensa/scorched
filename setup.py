from __future__ import unicode_literals
import os
from setuptools import setup, find_packages

version = '0.11.0'

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()


setup(name='scorched',
      version=version,
      description="solr search orm like query builder",
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
                  'Environment :: Console',
                  'Environment :: Web Environment',
                  'Intended Audience :: Developers',
                  'License :: OSI Approved :: MIT License',
                  'Operating System :: MacOS :: MacOS X',
                  'Operating System :: Microsoft :: Windows',
                  'Operating System :: POSIX',
                  'Programming Language :: Python :: 2',
                  'Programming Language :: Python :: 2.7',
                  'Programming Language :: Python :: 3',
                  'Programming Language :: Python :: 3.4',
      ],
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
          "pytz",
      ],
      extras_require={
          'test': ["nose", "coverage", "mock", ],
      },
      test_suite='scorched.tests',
      setup_requires=["setuptools_git"],
      )
