"""Export a .docx to PDF via Microsoft Word COM automation (pywin32).

Usage:
    python export_pdf.py <input.docx> <output.pdf>

Requires: Microsoft Word installed, pywin32 available.
This tool performs a read-only open of the source document.
"""
import os
import sys


def export_docx_to_pdf(docx_path: str, pdf_path: str) -> None:
    import win32com.client  # imported lazily so the module can be inspected without Word

    docx_abs = os.path.abspath(docx_path)
    pdf_abs = os.path.abspath(pdf_path)
    if not os.path.isfile(docx_abs):
        raise FileNotFoundError(docx_abs)

    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    try:
        word.DisplayAlerts = 0
    except Exception:
        pass
    try:
        doc = word.Documents.Open(
            docx_abs,
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
        )
        # wdExportFormatPDF = 17
        doc.ExportAsFixedFormat(
            OutputFileName=pdf_abs,
            ExportFormat=17,
            OpenAfterExport=False,
            OptimizeFor=0,
            Range=0,
            Item=0,
            IncludeDocProps=True,
            KeepIRM=True,
            CreateBookmarks=1,
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False,
        )
        doc.Close(False)
    finally:
        word.Quit()


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    export_docx_to_pdf(sys.argv[1], sys.argv[2])
    print("exported:", os.path.abspath(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
