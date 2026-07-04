# Fixtures de teste

Os PDFs aqui (`*.pdf`) são **NFS-e reais** e contêm dados fiscais de terceiros
(CNPJ, e-mail, endereço). Por isso são **gitignorados** e não vão para o repositório.

`test_danfse_import.py` usa `nfse_speedgov_62.pdf` (uma NFS-e emitida no portal
SpeedGov/Açailândia) e **pula** os testes automaticamente quando o arquivo não existe
(`pytest.mark.skipif`). Para rodar a suíte completa de importação localmente, coloque
o PDF de uma NFS-e emitida com este nome nesta pasta.
