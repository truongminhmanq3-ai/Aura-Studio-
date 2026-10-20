class Srt < Formula
  desc "Secure Reliable Transport"
  homepage "https://www.srtalliance.org/"
  url "https://github.com/Haivision/srt/archive/refs/tags/v1.5.7.tar.gz"
  sha256 "017cd1e437ef2073a4dd10ddf7b55e86bc3d6ebac0393d13bd22f6a57055d32b"
  license "MPL-2.0"
  revision 1
  compatibility_version 1
  head "https://github.com/Haivision/srt.git", branch: "master"

  livecheck do
    url :stable
    strategy :github_latest
  end

  depends_on "cmake" => :build
  depends_on "pkgconf" => :build
  depends_on "openssl@4"

  deny_network_access!

  def install
    openssl = Formula["openssl@4"]

    args = %W[
      -DWITH_OPENSSL_INCLUDEDIR=#{openssl.opt_include}
      -DWITH_OPENSSL_LIBDIR=#{openssl.opt_lib}
      -DCMAKE_INSTALL_BINDIR=bin
      -DCMAKE_INSTALL_LIBDIR=lib
      -DCMAKE_INSTALL_INCLUDEDIR=include
    ]

    system "cmake", "-S", ".", "-B", "build", *args, *std_cmake_args
    system "cmake", "--build", "build"
    system "cmake", "--install", "build"
  end

  test do
    cmd = "#{bin}/srt-live-transmit file:///dev/null file://con/ 2>&1"
    assert_match "Unsupported source type", shell_output(cmd, 1)
  end
end
