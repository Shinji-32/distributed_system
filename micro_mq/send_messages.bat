@echo off
for /l %%i in (1,1,10) do (
  curl -X POST -H "Content-Type: application/json" -d "{\"msg\":\"msg%%i\"}" http://localhost:8880/entry
)
