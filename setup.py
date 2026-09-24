from setuptools import setup, find_packages
setup(name="drugdisc", version="0.1.0",
      description="MEGA27-12 structure-based 3D drug discovery (real AutoDock Vina docking)",
      packages=find_packages(include=["drugdisc*"]), python_requires=">=3.9")
