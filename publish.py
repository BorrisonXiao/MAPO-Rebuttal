#!/usr/bin/env python3
"""Publish committed site/ output to gh-pages using normal Git authentication."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    subprocess.run([sys.executable, 'build.py'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, check=True)
    if git('status', '--porcelain', '--', 'site'):
        raise SystemExit('Commit the generated site/ changes before publishing.')
    git('fetch', 'origin', 'gh-pages')
    tree = git('rev-parse', 'HEAD:site')
    parent = git('rev-parse', 'FETCH_HEAD')
    if tree == git('rev-parse', f'{parent}^{{tree}}'):
        print('The committed site is already published on gh-pages.')
        return
    commit = git('commit-tree', tree, '-p', parent, '-m', 'Update rendered rebuttal viewer')
    # A normal, non-forced push preserves other collaborators' changes.
    git('push', 'origin', f'{commit}:refs/heads/gh-pages')
    print('Published gh-pages. Check the Pages deployment before sharing updated content.')


if __name__ == '__main__':
    main()
