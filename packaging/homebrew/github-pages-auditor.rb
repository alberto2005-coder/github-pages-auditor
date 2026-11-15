# Plantilla de fórmula para un tap propio (alberto2005-coder/homebrew-tap).
# Rellena url/sha256 con el sdist publicado en PyPI y genera los "resource" de las dependencias con:
#   brew update-python-resources github-pages-auditor
class GithubPagesAuditor < Formula
  include Language::Python::Virtualenv

  desc "Audita los repos de un usuario de GitHub: Pages, releases y calidad"
  homepage "https://github.com/alberto2005-coder/github-pages-auditor"
  url "https://files.pythonhosted.org/packages/source/g/github-pages-auditor/github_pages_auditor-1.4.0.tar.gz"
  sha256 "REEMPLAZAR_CON_EL_SHA256_DEL_SDIST"
  license "MIT"

  depends_on "python@3.13"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "github-pages-auditor", shell_output("#{bin}/github-pages-auditor -V")
  end
end
