from rag.ingestion.indexer import index_pdf
from .models import Manual


def index_manual(manual: Manual):

    try:
        result = index_pdf(
            pdf_path=manual.pdf_file.path,
            machine_id=manual.machine.model_number,
            document_id=manual.document_id,
            revision=manual.revision
        )

        manual.indexing_status = Manual.IndexingStatus.INDEXED
        manual.total_pages = result["total_pages"]
        manual.total_chunks = result["total_chunks"]

        manual.save(update_fields=[
            "indexing_status",
            "total_pages",
            "total_chunks"
        ])

        return result

    except Exception:
        manual.indexing_status = Manual.IndexingStatus.FAILED
        manual.save(update_fields=["indexing_status"])
        raise