import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyekonlib",
    version="0.3",
    author="Hillel ch.",
    #author_email="author@example.com",
    description="Server and client modules for Ekon/Connect/Airconet+",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hllhll/pyekonlib",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Communications',
        'Topic :: Internet :: Proxy Servers',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: MIT License',  # Again, pick a license
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>=3.8',
)