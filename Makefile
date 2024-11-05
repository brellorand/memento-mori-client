init:
	pip install -r requirements-dev.txt --require-virtualenv
	pre-commit install --install-hooks

dist:
	pyinstaller bin/game.py --name mm-client-game.exe --collect-all UnityPy --onefile

tag:
	bin/tag.py
