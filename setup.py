from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-freecad",
    version="1.0.0",
    description="CLI harness for FreeCAD parametric 3D CAD modeler",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-freecad=cli_anything.freecad.freecad_cli:main",
        ],
    },
    python_requires=">=3.10",
)
