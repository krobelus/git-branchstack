from pathlib import Path
from setuptools import setup

import gitbranchless

HERE = Path(__file__).resolve().parent

setup(
    name="git-branchless",
    version=gitbranchless.__version__,
    packages=["gitbranchless"],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "git-branchless = gitbranchless.main:main",
        ],
    },
    scripts=["git-branchless-pick"],
    author="Johannes Altmanninger",
    author_email="aclopte@gmail.com",
    description="Efficiently manage Git branches without leaving your local branch",
    long_description=(HERE / "README.md").read_text(),
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="git branch-workflow pull-request patch-stack",
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
        "Bug Tracker": "https://github.com/krobelus/git-branchless/issues/",
        "Source Code": "https://git.sr.ht/~krobelus/git-branchless/",
        "Documentation": "https://git.sr.ht/~krobelus/git-branchless/",
    },
    dependency_links=[
        "git+https://github.com/mystor/git-revise.git@e27bc1631f5da6041c2fa7e3d1f5a9fecfb3ef57"
    ],
)
