class Cjson < Formula
  desc "Ultralightweight JSON parser in ANSI C"
  homepage "https://github.com/DaveGamble/cJSON"
  url "https://github.com/DaveGamble/cJSON/archive/refs/tags/v1.7.19.tar.gz"
  sha256 "7fa616e3046edfa7a28a32d5f9eacfd23f92900fe1f8ccd988c1662f30454562"
  license "MIT"
  compatibility_version 1

  depends_on "cmake" => :build

  # CMake 4 build patch
  patch do
    url "https://github.com/DaveGamble/cJSON/commit/a29814f285cc531c00223743ad3c55cd38c0dc56.patch?full_index=1"
    sha256 "98485b6f2635d2d6f69c7d1ebb3f316661023f7570b12b89e0e535ddba88981e"
    type :backport
    resolves "https://github.com/DaveGamble/cJSON/pull/986"
  end

  def install
    args = %W[
      -DENABLE_CJSON_UTILS=ON
      -DENABLE_CJSON_TEST=Off
      -DBUILD_SHARED_AND_STATIC_LIBS=ON
      -DCMAKE_INSTALL_RPATH=#{rpath}
    ]
    system "cmake", "-S", ".", "-B", "build", *args, *std_cmake_args
    system "cmake", "--build", "build"
    system "cmake", "--install", "build"
  end

  test do
    (testpath/"test.c").write <<~C
      #include <cjson/cJSON.h>

      int main()
      {
        char *s = "{\\"key\\":\\"value\\"}";
        cJSON *json = cJSON_Parse(s);
        if (!json) {
            return 1;
        }
        cJSON *item = cJSON_GetObjectItem(json, "key");
        if (!item) {
            return 1;
        }
        cJSON_Delete(json);
        return 0;
      }
    C
    system ENV.cc, "test.c", "-L#{lib}", "-lcjson", "-o", "test"
    system "./test"
  end
end
