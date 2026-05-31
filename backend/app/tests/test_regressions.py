import os
import tempfile
import unittest
from asyncio import run
from io import BytesIO

from fastapi import HTTPException, UploadFile


_TEMP_DIR = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEMP_DIR.name}/citemind-test.db"

from sqlalchemy import delete, func, inspect, select

from backend.app.agent.intent import QueryIntent, detect_query_intent, extract_requested_count
from backend.app.core.config import get_settings
from backend.app.db.database import SessionLocal, init_db
from backend.app.db.database import engine
from backend.app.models.citation import Citation
from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.eval_result import EvalResult
from backend.app.models.query_log import QueryLog
from backend.app.routes.documents import delete_document, reset_demo_data, upload_document
from backend.app.routes.query import query_documents
from backend.app.schemas.eval import EvalRunRequest
from backend.app.schemas.query import QueryRequest
from backend.app.services.document_loader import load_document_content
from backend.app.services.embeddings import embed_chunks
from backend.app.services.evaluator import evaluate
from backend.app.services.retriever import (
    is_noisy_chunk,
    keyword_score,
    retrieve_context_for_intent,
)
from backend.app.services.vector_store import vector_store


init_db()


class CiteMindRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        settings = get_settings()
        settings.openai_api_key = None
        settings.retrieval_mode = "vector"
        settings.page_index_min_chunks = 8
        vector_store.records = []
        with SessionLocal() as db:
            for model in (EvalResult, QueryLog, Citation, DocumentChunk, Document):
                db.execute(delete(model))
            db.commit()

    def test_intent_count_noise_and_keyword_helpers(self) -> None:
        self.assertEqual(
            detect_query_intent("make study notes from this pdf"),
            QueryIntent.STUDY_NOTES,
        )
        self.assertEqual(
            extract_requested_count("give me exactly 10 important topics"),
            10,
        )
        self.assertTrue(
            is_noisy_chunk(
                "Copyright 2026. All rights reserved. ISBN 1234567890. "
                "Publisher contact and permissions information."
            )
        )
        self.assertGreater(
            keyword_score("aws iam security", "AWS IAM provides security controls."),
            0,
        )

    def test_local_schema_has_hash_embedding_and_pageindex_columns(self) -> None:
        inspector = inspect(engine)
        document_columns = {
            column["name"]
            for column in inspector.get_columns("documents")
        }
        chunk_columns = {
            column["name"]
            for column in inspector.get_columns("document_chunks")
        }

        self.assertIn("content_hash", document_columns)
        self.assertIn("page_index_tree_json", document_columns)
        self.assertIn("embedding_json", chunk_columns)

    def test_summary_retrieval_stays_scoped_to_selected_document(self) -> None:
        original_records = list(vector_store.records)
        vector_store.records = []
        try:
            doc_one_chunks = [
                "LangGraph agents coordinate workflow architecture and tool use. " * 12,
                "Retrieval, evaluation, monitoring, and deployment improve LLM apps. " * 12,
            ]
            doc_two_chunks = [
                "Convolutional neural networks and backpropagation train vision models. " * 12,
            ]
            vector_store.add_document(1, doc_one_chunks, embed_chunks(doc_one_chunks))
            vector_store.add_document(2, doc_two_chunks, embed_chunks(doc_two_chunks))

            records = retrieve_context_for_intent(
                "give me 5 key topics",
                [1],
                QueryIntent.TOPICS,
                5,
            )

            self.assertTrue(records)
            self.assertTrue(all(record.document_id == 1 for record in records))
        finally:
            vector_store.records = original_records

    def test_upload_reuses_same_file_hash_and_delete_cleans_chunks(self) -> None:
        content = (
            b"LangGraph helps teams build document-aware agent workflows. "
            b"Retrieval and evaluation keep answers grounded.\n"
        ) * 20

        with SessionLocal() as db:
            first = run(
                upload_document(
                    UploadFile(filename="sample.md", file=BytesIO(content)),
                    db,
                )
            )
            second = run(
                upload_document(
                    UploadFile(filename="same-content-different-name.md", file=BytesIO(content)),
                    db,
                )
            )

        self.assertEqual(first.id, second.id)

        with SessionLocal() as db:
            document_count = db.scalar(select(func.count()).select_from(Document))
            chunks = list(db.scalars(select(DocumentChunk)))
        chunk_count = len(chunks)
        self.assertEqual(document_count, 1)
        self.assertGreater(chunk_count or 0, 0)
        self.assertTrue(all(chunk.embedding_json for chunk in chunks))

        with SessionLocal() as db:
            delete_response = delete_document(first.id, db)
        self.assertEqual(delete_response["status"], "deleted")

        with SessionLocal() as db:
            document_count = db.scalar(select(func.count()).select_from(Document))
            chunk_count = db.scalar(select(func.count()).select_from(DocumentChunk))
        self.assertEqual(document_count, 0)
        self.assertEqual(chunk_count, 0)
        self.assertEqual(vector_store.document_records(first.id), [])

    def test_demo_reset_clears_persisted_data_and_loads_sample_document(self) -> None:
        with SessionLocal() as db:
            stale_document = Document(
                title="stale.md",
                abstract="Old demo data",
                content_hash="stale-hash",
            )
            db.add(stale_document)
            db.commit()
            db.refresh(stale_document)
            db.add(
                DocumentChunk(
                    document_id=stale_document.id,
                    chunk_index=0,
                    text="Old persisted chunk.",
                    embedding_json="[1.0, 0.0]",
                )
            )
            db.add(Citation(document_id=stale_document.id, quote="Old quote."))
            db.add(QueryLog(query="old query", answer="old answer"))
            db.add(
                EvalResult(
                    query="old query",
                    answer="old answer",
                    faithfulness_score=0.1,
                    answer_relevance_score=0.1,
                    context_relevance_score=0.1,
                    citation_coverage_score=0.1,
                )
            )
            db.commit()
            vector_store.add_document(
                stale_document.id,
                ["Old persisted chunk."],
                [[1.0, 0.0]],
            )

            response = reset_demo_data(db)

        with SessionLocal() as db:
            documents = list(db.scalars(select(Document)))
            chunks = list(db.scalars(select(DocumentChunk)))
            query_count = db.scalar(select(func.count()).select_from(QueryLog))
            eval_count = db.scalar(select(func.count()).select_from(EvalResult))
            citation_count = db.scalar(select(func.count()).select_from(Citation))

        self.assertEqual(response.title, "sample_ai_report.md")
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].id, response.id)
        self.assertEqual(documents[0].title, "sample_ai_report.md")
        self.assertGreater(len(chunks), 0)
        self.assertTrue(all(chunk.document_id == response.id for chunk in chunks))
        self.assertTrue(all(chunk.embedding_json for chunk in chunks))
        self.assertEqual(query_count, 0)
        self.assertEqual(eval_count, 0)
        self.assertEqual(citation_count, 0)
        self.assertTrue(
            all(record.text != "Old persisted chunk." for record in vector_store.records)
        )
        self.assertEqual(
            len(vector_store.document_records(response.id)),
            len(chunks),
        )

    def test_epub_raw_package_bytes_are_rejected(self) -> None:
        with self.assertRaises(HTTPException):
            load_document_content(
                b"PK META-INF/container.xml mimetypeapplication/epub+zip",
                "broken.epub",
            )

    def test_unreadable_pdf_bytes_are_rejected(self) -> None:
        with self.assertRaises(HTTPException):
            load_document_content(b"%PDF-1.4 broken obj stream", "broken.pdf")

    def test_query_response_shape_and_selected_document_scope(self) -> None:
        content_one = (
            b"LangGraph coordinates agent workflows, tool use, retrieval, "
            b"monitoring, and evaluation for LLM applications. "
        ) * 25
        content_two = (
            b"Deep learning models use backpropagation, neural network layers, "
            b"and optimization for image classification. "
        ) * 25

        with SessionLocal() as db:
            first = run(
                upload_document(
                    UploadFile(filename="langgraph.md", file=BytesIO(content_one)),
                    db,
                )
            )
            second = run(
                upload_document(
                    UploadFile(filename="deep-learning.md", file=BytesIO(content_two)),
                    db,
                )
            )

        with SessionLocal() as db:
            response = query_documents(
                QueryRequest(
                    query="Give me exactly 5 important topics from this PDF.",
                    document_ids=[first.id],
                ),
                db,
            )

        self.assertGreater(second.id, first.id)
        self.assertEqual(response.document_ids_used, [first.id])
        self.assertEqual(response.retrieval_strategy, "vector")
        self.assertEqual(
            response.retrieval_comparison["baseline_chunks"],
            response.retrieved_chunk_count,
        )
        self.assertEqual(response.retrieval_comparison["pageindex_chunks"], 0)
        self.assertEqual(response.intent, QueryIntent.TOPICS.value)
        self.assertEqual(response.requested_count, 5)
        self.assertFalse(response.used_llm)
        self.assertEqual(response.retrieved_chunk_count, len(response.retrieved_chunks))
        self.assertIn("5 Important Topics:", response.answer)
        self.assertTrue(response.retrieved_chunks)
        self.assertTrue(
            all(chunk.document_id == first.id for chunk in response.retrieved_chunks)
        )

    def test_pageindex_tree_is_stored_for_long_opt_in_upload(self) -> None:
        settings = get_settings()
        settings.retrieval_mode = "pageindex"
        settings.page_index_min_chunks = 2
        content = (
            b"PageIndex headings help long reports expose strategic sections. "
            b"Vector retrieval still remains the baseline comparison path. "
        ) * 35

        with SessionLocal() as db:
            uploaded = run(
                upload_document(
                    UploadFile(filename="long-report.md", file=BytesIO(content)),
                    db,
                )
            )
            document = db.get(Document, uploaded.id)

        self.assertIsNotNone(document)
        self.assertIsNotNone(document.page_index_tree_json)
        self.assertIn("PageIndex headings", document.page_index_tree_json or "")

    def test_pageindex_mode_uses_stored_tree_and_reports_comparison(self) -> None:
        settings = get_settings()
        settings.retrieval_mode = "pageindex"
        settings.page_index_min_chunks = 1
        content = (
            b"Vector baseline discusses generic retrieval architecture. " * 30
            + b"PageIndex tree highlights financial risk controls and audit evidence. " * 30
        )

        with SessionLocal() as db:
            uploaded = run(
                upload_document(
                    UploadFile(filename="risk-report.md", file=BytesIO(content)),
                    db,
                )
            )
            response = query_documents(
                QueryRequest(
                    query="What does the report say about financial risk controls?",
                    document_ids=[uploaded.id],
                ),
                db,
            )

        self.assertEqual(response.retrieval_strategy, "pageindex")
        self.assertGreater(response.retrieval_comparison["baseline_chunks"], 0)
        self.assertGreater(response.retrieval_comparison["pageindex_chunks"], 0)
        self.assertTrue(
            any("financial risk controls" in chunk.text for chunk in response.retrieved_chunks)
        )

    def test_structured_eval_rewards_cited_topic_answer(self) -> None:
        request = EvalRunRequest(
            query="Give me exactly 3 important topics.",
            answer=(
                "Overview:\nThis document explains agent workflows. [Document 1, chunk 0]\n\n"
                "3 Important Topics:\n"
                "1. Agent workflows: Agents coordinate steps. [Document 1, chunk 0]\n"
                "2. Retrieval: Context grounds answers. [Document 1, chunk 1]\n"
                "3. Evaluation: Checks improve quality. [Document 1, chunk 2]\n\n"
                "Final Takeaway:\nUse retrieval and evaluation together. [Document 1, chunk 2]"
            ),
            contexts=[
                "Agents coordinate workflow steps for LLM applications.",
                "Retrieval provides context that grounds answers.",
                "Evaluation checks improve answer quality.",
            ],
            citations=[
                {"document_id": 1, "chunk_index": 0, "text": "Agents coordinate workflow steps."},
                {"document_id": 1, "chunk_index": 1, "text": "Retrieval grounds answers."},
                {"document_id": 1, "chunk_index": 2, "text": "Evaluation checks quality."},
            ],
        )

        scores = evaluate(request)

        self.assertGreaterEqual(scores["answer_relevance_score"], 0.9)
        self.assertEqual(scores["citation_coverage_score"], 1.0)
        self.assertGreaterEqual(scores["context_relevance_score"], 0.7)

    def test_structured_eval_penalizes_noisy_uncited_topic_answer(self) -> None:
        request = EvalRunRequest(
            query="Give me exactly 3 important topics.",
            answer=(
                "Overview:\nCopyright and publisher details.\n\n"
                "3 Important Topics:\n"
                "1. Copyright: All rights reserved.\n"
                "2. ISBN: Publisher metadata.\n"
                "3. Contact: OReilly.com contact information.\n\n"
                "Final Takeaway:\nPublisher boilerplate."
            ),
            contexts=[
                "Copyright all rights reserved ISBN publisher contact permissions.",
                "Praise for this book and acknowledgements.",
            ],
            citations=[],
        )

        scores = evaluate(request)

        self.assertLess(scores["answer_relevance_score"], 0.9)
        self.assertEqual(scores["citation_coverage_score"], 0.0)
        self.assertLess(scores["context_relevance_score"], 0.8)


if __name__ == "__main__":
    unittest.main()
