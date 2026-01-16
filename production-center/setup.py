from setuptools import setup, find_packages
from cadastra_core._version import __version__

VERSION = __version__
DESCRIPTION = "Proprietary data integration and manipulation package made by Cadastra"

# Setting up
setup(
    name="cadastra_core",
    version=VERSION,
    author="Daniel Mendel",
    author_email="dmendel@cadastra.com",
    description=DESCRIPTION,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "google-analytics-data",
        "pandas",
        "loguru",
        "google-cloud-secret-manager",
        "google-auth",
        "google-api-python-client",
        "retry",
        "pandas_gbq",
        "google-cloud-bigquery",
        "requests",
        "rtbhouse-sdk==12.0.1",
        "protobuf",
        "google-ads-searchads360",
        "PyYAML",
        "pendulum",
        "google-ads",
        "bingads",
    ],
)
