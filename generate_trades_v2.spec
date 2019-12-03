# -*- mode: python -*-

block_cipher = None


a = Analysis(['generate_trades_v2.py'],
             pathex=['...'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['alabaster', 'altgraph', 'astroid', 'atomicwrites', 'attrs', 'Babel', 'backcall', 'bleach', 'certifi', 'chardet', 'cloudpickle', 'colorama', 'decorator', 'defusedxml', 'docutils', 'entrypoints', 'et-xmlfile', 'fancycompleter', 'future', 'idna', 'imagesize', 'ipdb', 'ipykernel', 'ipython', 'ipython-genutils', 'isort', 'jedi', 'Jinja2', 'jsonschema', 'jupyter-client', 'jupyter-core', 'keyring', 'lazy-object-proxy', 'macholib', 'MarkupSafe', 'mccabe', 'mistune', 'more-itertools', 'nbconvert', 'nbformat', 'numpydoc', 'packaging', 'pandocfilters', 'parso', 'pdbpp', 'pefile', 'pickleshare', 'pluggy', 'prompt-toolkit', 'psutil', 'py', 'pycodestyle', 'pyflakes', 'Pygments', 'PyInstaller', 'pylint', 'pyodbc', 'pyparsing', 'pypiwin32', 'PyQt5', 'pyreadline', 'pytest', 'python-dateutil', 'pywin32', 'pywin32-ctypes', 'pyzmq', 'QtAwesome', 'qtconsole', 'QtPy', 'requests', 'rope', 'scipy', 'simplegeneric', 'sip', 'snowballstemmer', 'Sphinx', 'sphinxcontrib-websupport', 'spyder', 'spyder-kernels', 'testpath', 'tornado', 'traitlets', 'typed-ast', 'urllib3', 'wcwidth', 'webencodings', 'wmctrl', 'workdays', 'wrapt'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='generate_trades_v2',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
