"""
Setup configuration for Personal Security Software
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f 
                       if line.strip() and not line.startswith("#")]

setup(
    name="personal-security-software",
    version="1.0.0",
    author="Personal Security Software Team",
    author_email="security@example.com",
    description="Face recognition-based security software for personal computers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/personal-security-software",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/personal-security-software/issues",
        "Documentation": "https://github.com/yourusername/personal-security-software/wiki",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Security",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Environment :: Win32 (MS Windows)",
        "Natural Language :: English",
    ],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
            "sphinx>=4.5.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
        "linux": [
            "python-xlib>=0.31",
        ],
    },
    entry_points={
        "console_scripts": [
            "personal-security=main:cli",
            "psec=main:cli",  # Short alias
        ],
    },
    python_requires=">=3.8",
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md"],
    },
    data_files=[
        ("config", ["config/config.yaml", "config/faces.yaml"]),
        ("scripts", ["scripts/setup_windows.bat", "scripts/setup_linux.sh"]),
    ],
    zip_safe=False,
    keywords=[
        "security", "face-recognition", "webcam", "monitoring",
        "intrusion-detection", "privacy", "screen-protection",
        "computer-security", "biometric", "authentication"
    ],
    platforms=["Windows", "Linux"],
)