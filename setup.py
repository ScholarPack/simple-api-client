import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simple-api-client",
    version="1.0.8",
    author="ScholarPack",
    author_email="dev@scholarpack.com",
    description="A simple API client for connecting to remote services.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ScholarPack/api-client",
    packages=["simple_api_client"],
    classifiers=[
        "Development Status :: 5 - Production/Stable ",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=["cookie-manager", "requests", "werkzeug"],
)
