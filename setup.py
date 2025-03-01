from setuptools import setup, find_packages

setup(
    name="lanchat",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "python-multipart>=0.0.5",
        "zeroconf>=0.38.0",
        "aiofiles>=0.8.0",
        "websockets>=10.0",
        "requests>=2.31.0",  # Add this
        "rich>=13.7.0",      # Add this
        "click>=8.1.7",      # Add this
        "pyperclip>=1.8.2"   # Add this
    ],
    entry_points={
        "console_scripts": [
            "lanchat=main:main",
        ],
    },
    author="Latrell",
    description="A LAN-based chat and file transfer application",
    keywords="chat, file transfer, LAN, network",
    python_requires=">=3.7",
)