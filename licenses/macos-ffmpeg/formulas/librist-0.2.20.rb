class Librist < Formula
  desc "Reliable Internet Stream Transport (RIST)"
  homepage "https://code.videolan.org/rist/"
  url "https://code.videolan.org/rist/librist/-/archive/v0.2.20/librist-v0.2.20.tar.gz"
  sha256 "9e40eeb87f014790531ad41326cc271b930a65962e4b15231b301fc59b29fe31"
  license "BSD-2-Clause"
  compatibility_version 1
  head "https://code.videolan.org/rist/librist.git", branch: "master"

  livecheck do
    url :stable
    regex(/^v?(\d+(?:\.\d+)+)$/i)
  end

  depends_on "meson" => :build
  depends_on "ninja" => :build
  depends_on "pkgconf" => :build
  depends_on "cjson"
  depends_on "gmp"
  depends_on "gnutls"
  depends_on "libmicrohttpd"
  depends_on "lz4"
  depends_on "nettle"

  def install
    ENV.append "LDFLAGS", "-Wl,-rpath,#{rpath}"

    # Use gnutls as it is already a dependency via libmicrohttpd.
    # Also aligns with Debian and Fedora.
    args = %w[
      --default-library=both
      -Dfallback_builtin=false
      -Duse_nettle=true
      -Duse_mbedtls=false
    ]

    system "meson", "setup", "build", *args, *std_meson_args
    system "meson", "compile", "-C", "build", "--verbose"
    system "meson", "install", "-C", "build"
  end

  test do
    assert_match "Starting ristsender", shell_output("#{bin}/ristsender 2>&1", 1)
  end
end
