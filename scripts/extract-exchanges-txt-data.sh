#!/usr/bin/env bash

ALL_EXCHANGES_OUTPUT_FILE=${ALL_EXCHANGES_OUTPUT_FILE:-"static/api/all-exchanges.txt"}

english_dictionary=$(cat /usr/share/dict/words)
all_stocks=$(curl https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt)

comm -12i <(echo "${all_stocks})") <(echo "${english_dictionary}") | tee "${ALL_EXCHANGES_OUTPUT_FILE}"
