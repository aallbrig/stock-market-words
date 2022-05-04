#!/usr/bin/env bash

comm -12i \
  <(curl https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt) \
  <(cat /usr/share/dict/words) \
  | tee static/api/all-exchanges.txt
