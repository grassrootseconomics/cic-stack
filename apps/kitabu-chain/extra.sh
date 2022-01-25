VANITY_STRING=${VANITY_STRING:-"Kitabu Sarafu Karibu Sana"}
echo -n "$VANITY_STRING" > .vanity 
truncate .vanity -s 32 && \
hexdump -v -n 32 -e '1/1 "%02x"' .vanity > .extra

WALLET_PASSPHRASE=test eth-keyfile -0 > keyfile_validator.json 
WALLET_PASSPHRASE=test eth-sign-msg -0 -f keyfile_validator.json `cat .extra` > .sig
WALLET_PASSPHRASE=test eth-keyfile -0 -d keyfile_validator.json >> .extra
cat .sig >> .extra
