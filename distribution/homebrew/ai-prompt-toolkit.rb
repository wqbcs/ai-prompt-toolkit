# ai-prompt-toolkit — Homebrew formula（brew tap 渠道, R346）
#
# 版本与 PyPI 锁步：每次发版同步 bump `version`（渠道矩阵 =
# docs/planning/06_发布与采用.md；单一真源纪律同 npm 包装器）。
#
# 用户侧动作（tap 仓库, 见 docs/pypi-trusted-publishing.md §G）:
#   brew tap wqbcs/tap https://github.com/wqbcs/homebrew-tap.git
#   brew install ai-prompt-toolkit
#
# 注：本公式在本仓库内维护源文件, 实际生效于 tap 仓库（brew 的 tap 机制要求
# 独立仓库）。本地无 brew 环境（Windows）, 首次 `brew install` 即真验收。
class Aiprompttoolkit < Formula
  desc "AI prompt lint / security scan / quality gate — deterministic, zero-LLM"
  homepage "https://github.com/wqbcs/ai-prompt-toolkit"
  url "https://pypi.org/pypi/ai-prompt-toolkit/67.34.128/json"
  version "67.34.128"
  license "MIT"
  head "https://github.com/wqbcs/ai-prompt-toolkit.git", branch: "main"

  depends_on "python@3.12"

  def install
    system python3, "-m", "pip", "install", "--quiet", "--prefix", prefix,
      "ai-prompt-toolkit==#{version}"
  end

  test do
    system bin/"prompt-cli", "--version"
  end
end
