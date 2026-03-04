from setuptools import setup, Extension
from Cython.Build import cythonize
from Cython.Compiler import Options
import platform
import sys

# Optimization settings
compiler_directives = {
    "optimize.use_switch": True,
    "optimize.unpack_method_calls": True,
    "language_level": "3",
    "binding": False,  # Reduces symbols
    "embedsignature": False,  # Reduces symbols
}

# Platform detection
system = platform.system()
machine = platform.machine()

if system == "Windows":
    name = "BHYG-Windows"
    extra_compile_args = ["/O2"]  # MSVC optimization
elif system == "Linux":
    name = "BHYG-Linux"
    extra_compile_args = ["-O3", "-ffast-math"]
elif system == "Darwin":
    if "arm" in machine:
        name = "BHYG-macOS-Apple_Silicon"
    else:
        name = "BHYG-macOS-Intel"
    extra_compile_args = ["-O3", "-ffast-math", "-mmacosx-version-min=10.9"]
else:
    name = "BHYG"
    extra_compile_args = []

# Extension modules
extensions = [
    Extension("api", ["api.py"], extra_compile_args=extra_compile_args),
    Extension("main", ["main.py"], extra_compile_args=extra_compile_args),
    Extension(
        "bilibili_util", ["bilibili_util.py"], extra_compile_args=extra_compile_args
    ),
]

setup(
    name=name,
    ext_modules=cythonize(
        extensions,
        compiler_directives=compiler_directives,
        annotate=False,
        quiet=True,
    ),
)
