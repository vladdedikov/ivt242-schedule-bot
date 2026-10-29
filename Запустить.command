
#!/bin/zsh
cd "${0:A:h}" || exit 1
if [[ -f config.json ]]; then
  /usr/bin/python3 bot.py
else
  /usr/bin/python3 bot.py --setup
fi
read '?Нажми Enter, чтобы закрыть окно…'
