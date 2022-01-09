from pathlib import Path
from setuptools import setup

import gitbranchstack

HERE = Path(__file__).resolve().parent

setup(
    name="git-branchstack",
    version=gitbranchstack.__version__,
    packages=["gitbranchstack"],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "git-branchstack = gitbranchstack.main:main",
        ],
    },
    scripts=["git-branchstack-pick"],
    author="Johannes Altmanninger",
    author_email="aclopte@gmail.com",
    description="Efficiently manage Git branches without leaving your local branch",
    long_description=(HERE / "README.md").read_text(),
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="git branch-workflow pull-request patch-stack",
    url="https://github.com/krobelus/git-branchstack/",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Environment :: Console",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Version Control :: Git",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    project_urls={
        "Bug Tracker": "https://github.com/krobelus/git-branchstack/issues/",
        "Source Code": "https://github.com/krobelus/git-branchstack/",
        "Documentation": "https://git.sr.ht/~krobelus/git-branchstack/",
    },
    install_requires=[
        "git-revise==0.7.0",
    ],
)
