"""本地文件存储：把上传的原始文档持久化到磁盘，供详情页查看。
生产环境可替换为 MinIO / S3。"""
import os

# 存储根目录：apps/api/storage/documents
_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "documents"))


def save_document(company_id: str, doc_id: str, content: bytes, suffix: str = ".pdf") -> str:
    """保存文档内容到 {company_id}/{doc_id}{suffix}，返回绝对路径。"""
    folder = os.path.join(_BASE, company_id)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{doc_id}{suffix}")
    with open(path, "wb") as f:
        f.write(content)
    return path


def delete_document_file(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
