# -*- mode: python -*-

block_cipher = None


a = Analysis(['src\\__main__.py'],
             pathex=['C:\\Users\\Jake\\PyCharmProjects\\fsim2\\src'],
             binaries=[],
             datas=[('src\\data', 'data'),
                    ('src\\mods', 'mods'),
                    ('venv\\Lib\\site-packages\\mimesis\\data\\en', 'mimesis\\data\\en')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
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
          name='fsim2',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True,
          icon=None)

app = BUNDLE(exe,
         name='fsim2.app',
         icon=None,
         bundle_identifier=None)