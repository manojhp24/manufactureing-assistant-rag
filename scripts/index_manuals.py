from pathlib import Path

from rag.ingestion.indexer import index_pdfs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANUALS_DIR = PROJECT_ROOT / "data" / "manuals"


manuals = [
    {
        "pdf_path": MANUALS_DIR / "HP200_Operations_Rev1_0.pdf",
        "machine_id": "M-HP200",
        "document_id": "HP-OPS-01",
        "revision": "1.0",
    },
    {
        "pdf_path": MANUALS_DIR / "HP200_Maintenance_Rev1_0.pdf",
        "machine_id": "M-HP200",
        "document_id": "HP-MNT-01",
        "revision": "1.0",
    },
    {
        "pdf_path": MANUALS_DIR / "AC90_Operations_Maintenance_Rev1_0.pdf",
        "machine_id": "M-AC90",
        "document_id": "AC-OM-01",
        "revision": "1.0",
    },
]


if __name__ == "__main__":

    results = index_pdfs(manuals)

    print("\nINDEXING RESULTS")

    for result in results:
        print(result)
