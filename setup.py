import os
from setuptools import setup, find_packages

this_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_dir, "README.md"), "r") as f:
    long_description = f.read()


# More information on properties: https://packaging.python.org/distributing
setup(
    name="pytest_httpx",
    version=open("pytest_httpx/version.py").readlines()[-1].split()[-1].strip("\"'"),
    author="Colin Bounouar",
    author_email="colin.bounouar.dev@gmail.com",
    maintainer="Colin Bounouar",
    maintainer_email="colin.bounouar.dev@gmail.com",
    url="https://colin-b.github.io/pytest_httpx/",
    description="Send responses to httpx.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    download_url="https://pypi.org/project/pytest-httpx/",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Internet :: WWW/HTTP",
        "Framework :: Pytest",
    ],
    keywords=["pytest", "testing", "mock", "httpx"],
    packages=find_packages(exclude=["tests*"]),
    package_data={"pytest_httpx": ["py.typed"]},
    entry_points={"pytest11": ["pytest_httpx = pytest_httpx"]},
    install_requires=["httpx==0.21.*", "pytest==6.*"],
    extras_require={
        "testing": [
            # Used to run async test functions
            "pytest-asyncio==0.16.*",
            # Used to check coverage
            "pytest-cov==3.*",
        ]
    },
    python_requires=">=3.6",
    project_urls={
        "GitHub": "https://github.com/Colin-b/pytest_httpx",
        "Changelog": "https://github.com/Colin-b/pytest_httpx/blob/master/CHANGELOG.md",
        "Issues": "https://github.com/Colin-b/pytest_httpx/issues",
    },
    platforms=["Windows", "Linux"],
)
