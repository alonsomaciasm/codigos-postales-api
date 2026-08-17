from setuptools import setup, find_packages

setup(
    name="mx-postal-client",
    version="1.0.0",
    description="SDK Cliente Oficial en Python para consumir la API de Códigos Postales de México",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="API Códigos Postales Team",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0"
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
