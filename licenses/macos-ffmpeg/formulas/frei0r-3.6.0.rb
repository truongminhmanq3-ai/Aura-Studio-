class Frei0r < Formula
  desc "Minimalistic plugin API for video effects"
  homepage "https://frei0r.dyne.org/"
  url "https://github.com/dyne/frei0r/archive/refs/tags/v3.6.0.tar.gz"
  sha256 "425ddc9358151c52775a00b14e9dbd4044fc1f3aa931beef2aa3633707ba1eb8"
  license "GPL-2.0-or-later"
  compatibility_version 1

  depends_on "cmake" => :build

  deny_network_access!

  def install
    # Skip the Linux-only `shadert0y` filter, which needs OpenGL/EGL from `mesa`
    inreplace "src/filter/CMakeLists.txt", "add_subdirectory (shadert0y)", ""

    args = %w[
      -DWITHOUT_OPENCV=ON
      -DWITHOUT_GAVL=ON
      -DWITHOUT_CAIRO=ON
    ]

    system "cmake", "-S", ".", "-B", "build", *args, *std_cmake_args
    system "cmake", "--build", "build"
    system "cmake", "--install", "build"
  end

  test do
    (testpath/"test.c").write <<~C
      #include <frei0r.h>

      int main()
      {
        int mver = FREI0R_MAJOR_VERSION;
        if (mver != 0) {
          return 0;
        } else {
          return 1;
        }
      }
    C
    system ENV.cc, "-L#{lib}", "test.c", "-o", "test"
    system "./test"
  end
end
