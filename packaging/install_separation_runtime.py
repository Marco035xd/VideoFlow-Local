"""Install one ONNX Runtime wheel into VideoFlow's virtual environment."""
import argparse
import importlib.metadata
import os
import subprocess
import sys
import tempfile

RUNTIMES = {
    'directml': ('onnxruntime-directml', '1.24.4'),
    'cuda': ('onnxruntime-gpu', '1.31.0'),
    'cpu': ('onnxruntime', '1.31.0'),
}


def install(runtime):
    installed = {}
    for name, _ in RUNTIMES.values():
        try:
            installed[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    if not runtime:
        runtime = 'cuda' if 'onnxruntime-gpu' in installed else 'directml' if os.name == 'nt' else 'cpu'
    package, version = RUNTIMES[runtime]
    if installed == {package: version}:
        return
    requirement = f'{package}=={version}'
    pip = [sys.executable, '-m', 'pip']
    # Fetch the replacement wheel before removing a runtime that shares its package directory.
    with tempfile.TemporaryDirectory(prefix='videoflow-runtime-') as wheels:
        subprocess.run([*pip, 'download', '--only-binary=:all:', '--dest', wheels, requirement], check=True)
        if installed:
            subprocess.run([*pip, 'uninstall', '-y', *installed], check=True)
        subprocess.run([*pip, 'install', '--no-index', '--find-links', wheels, requirement], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', nargs='?', choices=tuple(RUNTIMES))
    args = parser.parse_args()
    install(args.runtime)
