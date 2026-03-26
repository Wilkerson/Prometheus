"""Validacao de arquivos aceitos pelo sistema."""

# Formatos aceitos (baseado na lista do Gemini File Search)
FORMATOS_ACEITOS = {
    # Documentos
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Dados
    ".json": "application/json",
    ".xml": "application/xml",
    ".csv": "text/csv",
    ".sql": "application/sql",
    ".zip": "application/zip",
    # Texto
    ".txt": "text/plain",
    ".html": "text/html",
    ".md": "text/markdown",
    # Codigo
    ".py": "text/x-python",
    ".java": "text/x-java",
    ".js": "text/x-javascript",
    ".cs": "text/x-csharp",
    ".go": "text/x-go",
    ".rs": "text/x-rust",
    ".cpp": "text/x-cpp",
    ".c": "text/x-c",
    # Jupyter
    ".ipynb": "application/vnd.jupyter",
}

EXTENSOES_ACEITAS = list(FORMATOS_ACEITOS.keys())
MIME_TYPES_ACEITOS = list(FORMATOS_ACEITOS.values())

# String para o atributo accept do input file no HTML
ACCEPT_HTML = ",".join(EXTENSOES_ACEITAS + MIME_TYPES_ACEITOS)

# Labels amigaveis para exibir no erro
EXTENSOES_LABEL = ", ".join(EXTENSOES_ACEITAS)


def validar_arquivo(arquivo):
    """Valida se o arquivo tem extensao/tipo aceito. Retorna mensagem de erro ou None."""
    if not arquivo:
        return None

    import os
    _, ext = os.path.splitext(arquivo.name.lower())

    if ext not in FORMATOS_ACEITOS:
        return (
            f"Formato '{ext}' nao e aceito. "
            f"Formatos permitidos: {EXTENSOES_LABEL}"
        )

    return None
