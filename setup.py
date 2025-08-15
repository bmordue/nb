from setuptools import setup, find_packages

setup(
    name="nb",
    version="1.0.0",
    description="News aggregation and processing application",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.7",
    install_requires=[
        "beautifulsoup4==4.9.3",
        "requests==2.32.0",
        "datadog==0.45.0",
        "rollbar==0.16.3",
        "schedule==0.6.0",
    ],
    entry_points={
        "console_scripts": [
            "nb=app:main",
        ],
    },
)