"""
Interface Web - Geração de Certificados Digitais Simulados (ICP-Brasil)
----------------------------------------------------------------------
Aplicação Flask que oferece uma interface gráfica (no navegador) para:
  - Aba "Gerar Certificado": formulário para gerar o par de chaves RSA e o
    certificado X.509, com visualização dos detalhes, da versão DECODIFICADA
    do certificado (estilo OpenSSL), LISTAGEM dos certificados gerados e um
    MODAL com todas as informações de cada um, além do download dos arquivos.
  - Aba "Explicação": conteúdo didático sobre certificados digitais, X.509
    e a ICP-Brasil.

Reaproveita a lógica de geração já existente em gerar_certificado.py.
Os arquivos gerados também são salvos em disco na pasta ./saida (volume Docker).

ATENÇÃO: certificado AUTOASSINADO e SIMULADO, apenas para fins educacionais.
"""

import io
import os
import datetime

from flask import Flask, render_template, request, jsonify, send_file
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID

# Reutiliza as funções da atividade original (CLI)
from gerar_certificado import gerar_par_de_chaves, criar_certificado

app = Flask(__name__)

# Pasta onde os arquivos .pem são gravados em disco (mapeada por volume no Docker).
SAIDA_DIR = os.environ.get("SAIDA_DIR", "/app/saida")
os.makedirs(SAIDA_DIR, exist_ok=True)

# Histórico (em memória) dos certificados gerados nesta sessão do servidor.
# Cada item guarda os dados completos para exibir na listagem e no modal.
_historico = []

# Mantém o último gerado (compatibilidade com os botões de download "padrão").
_ultimo_resultado = {"chave_pem": None, "cert_pem": None}


def _dn_para_texto(nome: x509.Name) -> str:
    """Converte um Distinguished Name em string legível (C=.., ST=.., ...)."""
    return ", ".join(f"{attr.rfc4514_attribute_name}={attr.value}" for attr in nome)


def _detalhes_certificado(certificado, tamanho_bits):
    """Monta um dicionário legível com os detalhes principais do certificado."""
    def attr(oid):
        valores = certificado.subject.get_attributes_for_oid(oid)
        return valores[0].value if valores else ""

    nb = certificado.not_valid_before_utc
    na = certificado.not_valid_after_utc
    return {
        "pais": attr(NameOID.COUNTRY_NAME),
        "estado": attr(NameOID.STATE_OR_PROVINCE_NAME),
        "cidade": attr(NameOID.LOCALITY_NAME),
        "organizacao": attr(NameOID.ORGANIZATION_NAME),
        "nome_comum": attr(NameOID.COMMON_NAME),
        "serial": format(certificado.serial_number, "x"),
        "algoritmo_assinatura": certificado.signature_hash_algorithm.name.upper(),
        "tamanho_chave": tamanho_bits,
        "valido_de": nb.strftime("%d/%m/%Y %H:%M:%S UTC"),
        "valido_ate": na.strftime("%d/%m/%Y %H:%M:%S UTC"),
        "dias_validade": (na - nb).days,
    }


def _hex_agrupado(dados: bytes) -> str:
    """Formata bytes como 'AA:BB:CC...' (estilo OpenSSL)."""
    return ":".join(f"{b:02X}" for b in dados)


def _texto_certificado(certificado) -> str:
    """
    Gera uma representação textual DECODIFICADA do certificado, no estilo do
    comando 'openssl x509 -text', para o usuário entender o conteúdo.
    """
    pub = certificado.public_key()
    numeros = pub.public_numbers()
    nb = certificado.not_valid_before_utc
    na = certificado.not_valid_after_utc

    linhas = []
    linhas.append("Certificado X.509:")
    linhas.append(f"    Versão            : {certificado.version.name} (v3)")
    linhas.append(f"    Número de série   : {certificado.serial_number}")
    linhas.append(f"    Algoritmo assin.  : SHA256withRSA")
    linhas.append(f"    Emissor (Issuer)  : {_dn_para_texto(certificado.issuer)}")
    linhas.append(f"    Titular (Subject) : {_dn_para_texto(certificado.subject)}")
    linhas.append("    Validade:")
    linhas.append(f"        Não antes de  : {nb.strftime('%d/%m/%Y %H:%M:%S UTC')}")
    linhas.append(f"        Não depois de : {na.strftime('%d/%m/%Y %H:%M:%S UTC')}")
    linhas.append("    Chave pública:")
    linhas.append(f"        Algoritmo     : RSA")
    linhas.append(f"        Tamanho       : {pub.key_size} bits")
    linhas.append(f"        Expoente (e)  : {numeros.e}")

    linhas.append("    Extensões:")
    for ext in certificado.extensions:
        nome = ext.oid._name or ext.oid.dotted_string
        critico = "crítica" if ext.critical else "não crítica"
        valor = ext.value
        if isinstance(valor, x509.BasicConstraints):
            detalhe = f"CA={valor.ca}"
        elif isinstance(valor, x509.KeyUsage):
            usos = []
            if valor.digital_signature: usos.append("assinatura digital")
            if valor.content_commitment: usos.append("não-repúdio")
            if valor.key_encipherment: usos.append("cifragem de chave")
            if valor.data_encipherment: usos.append("cifragem de dados")
            detalhe = ", ".join(usos)
        elif isinstance(valor, x509.SubjectAlternativeName):
            detalhe = ", ".join(str(g.value) for g in valor)
        else:
            detalhe = str(valor)
        linhas.append(f"        - {nome} ({critico}): {detalhe}")

    linhas.append("    Impressões digitais (fingerprints):")
    linhas.append(f"        SHA-256       : {_hex_agrupado(certificado.fingerprint(hashes.SHA256()))}")
    linhas.append(f"        SHA-1         : {_hex_agrupado(certificado.fingerprint(hashes.SHA1()))}")

    return "\n".join(linhas)


@app.after_request
def _cors(resp):
    """Permite que a interface funcione mesmo aberta de outra origem (ex.: painel de preview)."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/gerar", methods=["POST"])
def gerar():
    """Recebe os dados do formulário, gera o certificado e o adiciona ao histórico."""
    try:
        dados_form = request.get_json(force=True)

        bits = int(dados_form.get("bits", 2048))
        dias = int(dados_form.get("dias", 365))
        senha = (dados_form.get("senha") or "").strip() or None

        dados = {
            "pais": (dados_form.get("pais") or "BR").strip(),
            "estado": (dados_form.get("estado") or "").strip(),
            "cidade": (dados_form.get("cidade") or "").strip(),
            "organizacao": (dados_form.get("organizacao") or "").strip(),
            "nome_comum": (dados_form.get("nome_comum") or "").strip(),
            "email": (dados_form.get("email") or "").strip(),
        }

        if bits < 2048:
            return jsonify({"ok": False, "erro": "O tamanho da chave deve ser de no mínimo 2048 bits."}), 400
        if len(dados["pais"]) != 2:
            return jsonify({"ok": False, "erro": "O país deve ter exatamente 2 letras (ex.: BR)."}), 400
        for campo in ("estado", "cidade", "organizacao", "nome_comum", "email"):
            if not dados[campo]:
                return jsonify({"ok": False, "erro": f"O campo '{campo}' é obrigatório."}), 400

        # Tarefa 1 e 2
        chave_privada = gerar_par_de_chaves(bits)
        certificado = criar_certificado(chave_privada, dados, dias)

        # Serialização (PEM)
        cifra = serialization.BestAvailableEncryption(senha.encode("utf-8")) if senha else serialization.NoEncryption()
        chave_pem = chave_privada.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=cifra,
        )
        cert_pem = certificado.public_bytes(serialization.Encoding.PEM)

        # Compatibilidade com download "padrão"
        _ultimo_resultado["chave_pem"] = chave_pem
        _ultimo_resultado["cert_pem"] = cert_pem

        # Salva em disco (último gerado) na pasta ./saida
        with open(os.path.join(SAIDA_DIR, "certificate.pem"), "wb") as f:
            f.write(cert_pem)
        with open(os.path.join(SAIDA_DIR, "private_key.pem"), "wb") as f:
            f.write(chave_pem)

        detalhes = _detalhes_certificado(certificado, bits)
        cid = detalhes["serial"]  # identificador único (número de série em hex)
        criado_em = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        item = {
            "id": cid,
            "criado_em": criado_em,
            "detalhes": detalhes,
            "chave_protegida": bool(senha),
            "cert_texto": _texto_certificado(certificado),
            "cert_pem": cert_pem.decode("utf-8"),
            "chave_pem": chave_pem.decode("utf-8"),
            "arquivos": [
                {"nome": "certificate.pem", "tipo": "Certificado digital (público)",
                 "tamanho": len(cert_pem), "caminho": "saida/certificate.pem",
                 "download": f"/download/{cid}/cert"},
                {"nome": "private_key.pem",
                 "tipo": "Chave privada" + (" (protegida por senha)" if senha else " (sem senha)"),
                 "tamanho": len(chave_pem), "caminho": "saida/private_key.pem",
                 "download": f"/download/{cid}/chave"},
            ],
            # Bytes para download por id (não enviados ao navegador na listagem)
            "_cert_bytes": cert_pem,
            "_chave_bytes": chave_pem,
        }
        _historico.insert(0, item)  # mais recente primeiro

        return jsonify({"ok": True, "id": cid})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "erro": f"Erro ao gerar: {e}"}), 500


def _resumo(item):
    """Versão enxuta de um item para a listagem (sem PEMs grandes)."""
    d = item["detalhes"]
    return {
        "id": item["id"],
        "criado_em": item["criado_em"],
        "nome_comum": d["nome_comum"],
        "organizacao": d["organizacao"],
        "localidade": f'{d["cidade"]}/{d["estado"]}',
        "tamanho_chave": d["tamanho_chave"],
        "valido_ate": d["valido_ate"],
        "chave_protegida": item["chave_protegida"],
    }


def _publico(item):
    """Versão completa de um item para o modal (sem os bytes internos)."""
    return {k: v for k, v in item.items() if not k.startswith("_")}


@app.route("/historico")
def historico():
    """Lista resumida de todos os certificados gerados nesta sessão."""
    return jsonify({"ok": True, "itens": [_resumo(i) for i in _historico]})


@app.route("/certificado/<cid>")
def certificado(cid):
    """Detalhes completos de um certificado específico (para o modal)."""
    for item in _historico:
        if item["id"] == cid:
            return jsonify({"ok": True, "item": _publico(item)})
    return jsonify({"ok": False, "erro": "Certificado não encontrado."}), 404


@app.route("/download/<cid>/<tipo>")
def download_id(cid, tipo):
    """Baixa a chave ou o certificado de um item específico do histórico."""
    for item in _historico:
        if item["id"] == cid:
            if tipo == "cert":
                return send_file(io.BytesIO(item["_cert_bytes"]), mimetype="application/x-pem-file",
                                 as_attachment=True, download_name="certificate.pem")
            if tipo == "chave":
                return send_file(io.BytesIO(item["_chave_bytes"]), mimetype="application/x-pem-file",
                                 as_attachment=True, download_name="private_key.pem")
    return "Arquivo não encontrado.", 404


@app.route("/download/<tipo>")
def download(tipo):
    """Baixa o último certificado/chave gerados (compatibilidade)."""
    if tipo == "chave" and _ultimo_resultado["chave_pem"]:
        return send_file(io.BytesIO(_ultimo_resultado["chave_pem"]), mimetype="application/x-pem-file",
                         as_attachment=True, download_name="private_key.pem")
    if tipo == "cert" and _ultimo_resultado["cert_pem"]:
        return send_file(io.BytesIO(_ultimo_resultado["cert_pem"]), mimetype="application/x-pem-file",
                         as_attachment=True, download_name="certificate.pem")
    return "Nenhum arquivo disponível. Gere um certificado primeiro.", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
