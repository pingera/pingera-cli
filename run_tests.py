
#!/usr/bin/env python3
"""
Test runner for PingeraCLI
"""

import subprocess
import sys
import os


def run_tests():
    """Run pytest with coverage"""
    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Install test requirements if needed
    print("Installing test requirements...")
    subprocess.run([
        sys.executable, '-m', 'pip', 'install', '-r', 'tests/requirements.txt'
    ], check=False)
    
    # Run tests with coverage
    print("\nRunning tests...")
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',
        '--cov=pingera_cli',
        '--cov-report=term-missing',
        '--cov-report=html'
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("📊 Coverage report saved to htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    run_tests()
