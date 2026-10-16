#!/bin/bash
set -euo pipefail
# Usage: bash build-native.sh <llama-source> <srt-source> <openssl-keg> <build-dir> <sdk26-path>
llama_source=$(cd "$1" && pwd)
srt_source=$(cd "$2" && pwd)
openssl_keg=$(cd "$3" && pwd)
mkdir -p "$4"
build_dir=$(cd "$4" && pwd)
sdk=$(cd "$5" && pwd)
common=(-G 'Unix Makefiles' -DCMAKE_MAKE_PROGRAM=/usr/bin/make -DCMAKE_C_COMPILER=/usr/bin/clang -DCMAKE_CXX_COMPILER=/usr/bin/clang++ -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=26.0 "-DCMAKE_OSX_SYSROOT=$sdk")
cmake -S "$llama_source" -B "$build_dir/llama" "${common[@]}" -DCMAKE_C_FLAGS=-Werror=unguarded-availability -DCMAKE_CXX_FLAGS=-Werror=unguarded-availability -DGGML_OPENMP=OFF -DGGML_NATIVE=OFF -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_METAL=ON -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_APP=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_TOOLS=OFF
cmake --build "$build_dir/llama" --target llama mtmd --parallel 6
cmake -S "$srt_source" -B "$build_dir/srt" "${common[@]}" -DENABLE_APPS=OFF -DENABLE_TESTING=OFF -DENABLE_SHARED=ON -DENABLE_STATIC=OFF -DUSE_OPENSSL_PC=OFF "-DOPENSSL_ROOT_DIR=$openssl_keg" "-DOPENSSL_INCLUDE_DIR=$openssl_keg/include" "-DOPENSSL_SSL_LIBRARY=$openssl_keg/lib/libssl.3.dylib" "-DOPENSSL_CRYPTO_LIBRARY=$openssl_keg/lib/libcrypto.3.dylib"
cmake --build "$build_dir/srt" --parallel 6
