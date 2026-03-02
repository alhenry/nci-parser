from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="nci-parser",
    version="0.4.0",
    author="Albert Henry",
    description="Parse NCI job output files into tabular format",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alhenry/nci-job-parser",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "nci-parser=nci_parser.cli:main",
            "nci-job-parser=nci_parser.jobs_cli:jobs_main",  # legacy alias
        ],
    },
)
