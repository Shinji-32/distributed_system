@echo off
:: Надсилає 10 тестових повідомлень до фасадного сервісу на http://localhost:8880
for /l %%i in (1,1,10) do (
  curl -X POST -F "txt=msg%%i" http://localhost:8880/
)
