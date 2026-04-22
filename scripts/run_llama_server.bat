echo Assumes you have "gemma-3n-E2B-it_Q4.gguf" in the same dir as this script
echo Download it from the provided source

.\llama.cpp\build\bin\llama-server.exe -m .\gemma-3n-E2B-it_Q4.gguf --jinja -c 0