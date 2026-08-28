"""
简历文件上传与解析 API
"""

from fastapi import APIRouter, HTTPException, UploadFile, File

router = APIRouter(prefix="/api/resume", tags=["简历上传"])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".docx", ".pdf"}


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """上传简历文件（.docx / .pdf），自动解析提取文本"""

    # 校验文件扩展名
    filename = file.filename or ""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    ext_with_dot = f".{ext}"
    if ext_with_dot not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式 '.{ext}'，请上传 .docx 或 .pdf 文件",
        )

    # 读取文件内容
    content = await file.read()

    # 校验大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大（{len(content) / 1024 / 1024:.1f}MB），最大支持 5MB",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件内容为空，请重新选择")

    # 根据类型解析
    try:
        if ext == "docx":
            text = _parse_docx(content)
        else:
            text = _parse_pdf(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"文件解析失败，请确认文件未损坏: {str(e)}"
        )

    if not text.strip():
        raise HTTPException(status_code=400, detail="未能从文件中提取到文字内容，请确认文件包含可读文本")

    return {
        "filename": filename,
        "text": text.strip(),
        "char_count": len(text.strip()),
        "file_type": "docx" if ext == "docx" else "pdf",
    }


def _parse_docx(content: bytes) -> str:
    """解析 .docx 文件，提取段落和表格文本（去重）

    段落和表格在 Word 中是平级的两个 block，docx 结构里经常出现：
      · 段落「▌ 个人信息 ─────」（标题占位）
      · 表格 cell 里写姓名/电话/邮箱等实际信息
    这里把段落按行提取，再把表格 cell 按行提取，整体去重，
    保证同一行文本（如「▌ 个人信息 ─────」这种装饰行）只出现一次。
    装饰行（只有 ─/=/_ 等 ≤3 字符无字母数字的字符）会被跳过。
    """
    from io import BytesIO
    from docx import Document

    doc = Document(BytesIO(content))
    parts: list[str] = []
    seen_lines: set[str] = set()

    def _add(text: str) -> None:
        s = (text or "").strip()
        if not s:
            return
        # 跳过装饰行（───、===、___ 等 ≤3 字符且不含字母数字）
        if len(s) <= 3 and not any(c.isalnum() for c in s):
            return
        if s in seen_lines:
            return
        seen_lines.add(s)
        parts.append(s)

    # 段落
    for para in doc.paragraphs:
        _add(para.text)

    # 表格 — cell.text 会把 cell 内多段落用 \n 拼起来，按行拆开加入
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for line in (cell.text or "").split("\n"):
                    _add(line)

    return "\n".join(parts)


def _parse_pdf(content: bytes) -> str:
    """解析 PDF 文件，逐页提取文本"""
    from io import BytesIO
    import pdfplumber

    parts = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text.strip())

    return "\n".join(parts)
