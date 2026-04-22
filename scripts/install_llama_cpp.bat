echo You must run this script from within a Visual Studio Command prompt
echo Install either Visual Studio or Visual Studio Build Tools for C++ Desktop Development
echo Then run "x64 Native Tools Command Prompt for VS 2022" from the Windows start menu
echo Important! Change dir to wherever you have this script
echo You also need git installed, obviously

git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
git submodule update --init --recursive

cmake -S . -B build -G Ninja -Wno-dev -DCMAKE_BUILD_TYPE=Release -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON -DLLAMA_CURL=OFF

cmake --build build --config Release

cd ..