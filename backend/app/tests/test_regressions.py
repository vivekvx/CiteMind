import os
import tempfile
import unittest
from asyncio import run
from io import BytesIO
from unittest.mock import patch

from fastapi import HTTPException, UploadFile


_TEMP_DIR = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEMP_DIR.name}/citemind-test.db"

from sqlalchemy import delete, func, inspect, select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.db import database as database_module
from backend.app.agent.intent import (
    QueryIntent,
    detect_query_intent,
    extract_requested_count,
    extract_word_limit,
)
from backend.app.core.config import get_settings
from backend.app.db.database import SessionLocal, database_status, init_db
from backend.app.db.database import engine
from backend.app.models.citation import Citation
from backend.app.models.document import Document
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.eval_result import EvalResult
from backend.app.models.query_log import QueryLog
from backend.app.core.rate_limit import rate_limiter
from backend.app.routes.documents import delete_document, reset_demo_data, upload_document
from backend.app.routes.health import health_check, llm_health_check
from backend.app.routes.query import query_documents
from backend.app.schemas.eval import EvalRunRequest
from backend.app.schemas.query import QueryRequest
from backend.app.services import document_loader
from backend.app.services import reranker as reranker_module
from backend.app.services.document_loader import load_document_content
from backend.app.services.embeddings import embed_chunks
from backend.app.services.evaluator import evaluate
from backend.app.services.llm_provider import get_llm_provider
from backend.app.services.retriever import (
    extract_section_title,
    is_noisy_chunk,
    keyword_score,
    retrieve_context_for_intent,
)
from backend.app.services.answer_generator import generate_answer_result
from backend.app.services.vector_store import VectorRecord, vector_store


init_db()


class CiteMindRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        settings = get_settings()
        settings.openai_api_key = None
        settings.llm_api_key = None
        settings.llm_base_url = None
        settings.llm_chat_model = None
        settings.retrieval_mode = "vector"
        settings.reranker_mode = "none"
        settings.reranker_top_k = 30
        settings.reranker_final_k = 5
        settings.document_parser = "pymupdf"
        settings.llama_cloud_api_key = None
        settings.page_index_min_chunks = 8
        settings.max_upload_bytes = 10_000_000
        settings.rate_limit_enabled = True
        settings.rate_limit_requests_per_minute = 20
        rate_limiter._requests.clear()
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
        self.assertEqual(extract_word_limit("give me summary in 100 words"), 100)
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

    def test_retrieval_feature_defaults_are_opted_out(self) -> None:
        settings = get_settings()

        self.assertEqual(settings.reranker_mode, "none")
        self.assertEqual(settings.reranker_top_k, 30)
        self.assertEqual(settings.reranker_final_k, 5)
        self.assertEqual(settings.document_parser, "pymupdf")
        self.assertIsNone(settings.llama_cloud_api_key)

    def test_local_database_status_allows_sqlite_for_development(self) -> None:
        status = database_status()

        self.assertEqual(status["backend"], "sqlite")
        self.assertFalse(status["persistent"])
        self.assertTrue(status["production_safe"])

    def test_vercel_sqlite_database_is_reported_and_blocked_as_unsafe(self) -> None:
        original_vercel = os.environ.get("VERCEL")
        original_configured_url = database_module.configured_database_url
        os.environ["VERCEL"] = "1"
        database_module.configured_database_url = "sqlite:///./citemind.db"
        try:
            status = database_module.database_status()

            self.assertEqual(status["backend"], "sqlite")
            self.assertFalse(status["persistent"])
            self.assertFalse(status["production_safe"])
            self.assertEqual(health_check()["status"], "degraded")
            with self.assertRaises(HTTPException) as error:
                database_module.require_production_database()
            self.assertEqual(error.exception.status_code, 503)
            self.assertIn("Persistent DATABASE_URL", error.exception.detail)
        finally:
            if original_vercel is None:
                os.environ.pop("VERCEL", None)
            else:
                os.environ["VERCEL"] = original_vercel
            database_module.configured_database_url = original_configured_url

    def test_generic_llm_provider_overrides_openai_defaults(self) -> None:
        settings = get_settings()
        settings.openai_api_key = "openai-key"
        settings.openai_chat_model = "gpt-4o-mini"
        settings.llm_api_key = "generic-key"
        settings.llm_base_url = "https://api.deepseek.com"
        settings.llm_chat_model = "deepseek-chat"

        provider = get_llm_provider()

        self.assertTrue(provider.configured)
        self.assertEqual(provider.api_key, "generic-key")
        self.assertEqual(provider.chat_model, "deepseek-chat")
        self.assertEqual(
            provider.chat_completions_url,
            "https://api.deepseek.com/chat/completions",
        )

    def test_generic_llm_provider_normalizes_base_url_trailing_slash(self) -> None:
        settings = get_settings()
        settings.llm_api_key = "generic-key"
        settings.llm_base_url = "https://openrouter.ai/api/v1/"
        settings.llm_chat_model = "deepseek/deepseek-chat-v3.1:free"

        provider = get_llm_provider()

        self.assertEqual(
            provider.chat_completions_url,
            "https://openrouter.ai/api/v1/chat/completions",
        )

    def test_openai_settings_remain_default_llm_provider(self) -> None:
        settings = get_settings()
        settings.openai_api_key = "openai-key"
        settings.openai_chat_model = "gpt-4o-mini"

        provider = get_llm_provider()

        self.assertTrue(provider.configured)
        self.assertEqual(provider.api_key, "openai-key")
        self.assertEqual(provider.chat_model, "gpt-4o-mini")
        self.assertEqual(
            provider.chat_completions_url,
            "https://api.openai.com/v1/chat/completions",
        )

    def test_llm_health_reports_generic_missing_key(self) -> None:
        response = llm_health_check()

        self.assertFalse(response["configured"])
        self.assertFalse(response["ok"])
        self.assertEqual(response["base_url"], "https://api.openai.com/v1")
        self.assertEqual(
            response["chat_completions_url"],
            "https://api.openai.com/v1/chat/completions",
        )
        self.assertEqual(response["error"], "missing_llm_api_key")

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

    def test_upload_rejects_files_over_configured_size(self) -> None:
        settings = get_settings()
        settings.max_upload_bytes = 8

        with SessionLocal() as db:
            with self.assertRaises(HTTPException) as error:
                run(
                    upload_document(
                        UploadFile(filename="large.md", file=BytesIO(b"too much content")),
                        db,
                    )
                )

        self.assertEqual(error.exception.status_code, 413)

    def test_rate_limiter_blocks_after_configured_limit(self) -> None:
        rate_limiter.check("client-a", limit=2, window_seconds=60)
        rate_limiter.check("client-a", limit=2, window_seconds=60)

        with self.assertRaises(HTTPException) as error:
            rate_limiter.check("client-a", limit=2, window_seconds=60)

        self.assertEqual(error.exception.status_code, 429)

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

    def test_query_logging_failure_does_not_break_answer(self) -> None:
        with SessionLocal() as db:
            document = Document(
                title="readonly-log.md",
                abstract="Transformer models use attention layers.",
                content_hash="readonly-log",
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            chunks = [
                "Transformer models use attention layers for grounded language modeling. " * 12,
            ]
            vector_store.add_document(document.id, chunks, embed_chunks(chunks))
            original_commit = db.commit

            def fail_commit() -> None:
                raise SQLAlchemyError("readonly demo database")

            db.commit = fail_commit  # type: ignore[method-assign]
            try:
                response = query_documents(
                    QueryRequest(
                        query="What do transformer models use?",
                        document_ids=[document.id],
                    ),
                    db,
                )
            finally:
                db.commit = original_commit  # type: ignore[method-assign]

        self.assertEqual(response.query_id, 0)
        self.assertIn("Transformer", response.answer)
        self.assertTrue(response.retrieved_chunks)

    def test_first_mention_query_returns_exact_sentence(self) -> None:
        chunks = [
            "Table of contents Transformer 9 Attention 12.",
            (
                "Input tokens are converted into embedding vectors. "
                "This embedding is then fed into the transformer for processing."
            ),
            "Attention mechanisms are explained after the transformer overview.",
        ]
        vector_store.add_document(8, chunks, embed_chunks(chunks))

        question = (
            "Find the very first time the term 'Transformer' or 'Attention' is used "
            "in this document. Quote the exact sentence it appears in"
        )
        records = retrieve_context_for_intent(question, [8], QueryIntent.NORMAL_QA, 10)
        answer, used_llm = generate_answer_result(
            question,
            records,
            QueryIntent.NORMAL_QA,
            10,
            None,
        )

        self.assertFalse(used_llm)
        self.assertEqual(records[0].chunk_index, 1)
        self.assertIn(
            "This embedding is then fed into the transformer for processing.",
            answer,
        )
        self.assertNotIn("Table of contents", answer)
        self.assertIn("[Document 8, chunk 1]", answer)

    def test_section_title_query_retrieves_heading_context_and_quotes_first_sentence(self) -> None:
        chunks = [
            "Table of Contents\nWhy AI Agents Are the Future ........ 12\nOther Section ........ 20",
            "Earlier material discusses unrelated automation history.",
            (
                "12 | Why AI Agents Are the Future\n"
                "AI agents are becoming practical collaborators for complex work. "
                "They can plan, use tools, and adapt to feedback."
            ),
            "The next paragraph continues the section with more implementation detail.",
        ]
        vector_store.add_document(7, chunks, embed_chunks(chunks))

        question = (
            "What is the very first sentence written on the page under the section "
            "titled 'Why AI Agents Are the Future'?"
        )
        records = retrieve_context_for_intent(question, [7], QueryIntent.DEFINITION, 10)
        answer, used_llm = generate_answer_result(
            question,
            records,
            QueryIntent.DEFINITION,
            10,
            None,
        )

        self.assertEqual(extract_section_title(question), "Why AI Agents Are the Future")
        self.assertEqual(records[0].chunk_index, 2)
        self.assertFalse(used_llm)
        self.assertIn(
            "AI agents are becoming practical collaborators for complex work.",
            answer,
        )
        self.assertNotIn("Table of Contents", answer)
        self.assertIn("[Document 7, chunk 2]", answer)

    def test_flashrank_mode_reranks_broad_vector_candidates_and_reports_counts(self) -> None:
        settings = get_settings()
        settings.reranker_mode = "flashrank"
        settings.reranker_top_k = 30
        settings.reranker_final_k = 2
        content = (
            b"Table of Contents\nAgent Memory ........ 9\nAgent Safety ........ 12\n\n"
            + b"Agent memory stores durable user preferences for later tasks. " * 40
            + b"Agent safety validates tool calls before execution. " * 40
        )

        class FakeRanker:
            def rerank(self, query: str, records: list[VectorRecord], top_n: int) -> list[VectorRecord]:
                return sorted(
                    records,
                    key=lambda record: (
                        "durable user preferences" not in record.text,
                        "Table of Contents" in record.text,
                        record.chunk_index,
                    ),
                )[:top_n]

        with patch.object(reranker_module, "_get_flashrank_ranker", return_value=FakeRanker()):
            with SessionLocal() as db:
                uploaded = run(
                    upload_document(
                        UploadFile(filename="agents.md", file=BytesIO(content)),
                        db,
                    )
                )
                response = query_documents(
                    QueryRequest(
                        query="Where does the document discuss durable user preferences?",
                        document_ids=[uploaded.id],
                    ),
                    db,
                )

        self.assertEqual(response.retrieval_strategy, "flashrank")
        self.assertGreater(response.retrieval_comparison["baseline_chunks"], 0)
        self.assertGreater(response.retrieval_comparison["reranker_input_chunks"], 0)
        self.assertEqual(response.retrieval_comparison["reranked_chunks"], 2)
        self.assertLessEqual(response.retrieved_chunk_count, 2)
        self.assertIn("durable user preferences", response.retrieved_chunks[0].text)
        self.assertNotIn("Table of Contents", response.retrieved_chunks[0].text)

    def test_flashrank_missing_package_falls_back_without_crashing(self) -> None:
        settings = get_settings()
        settings.reranker_mode = "flashrank"

        with patch.object(reranker_module, "_get_flashrank_ranker", return_value=None):
            records = [
                VectorRecord(1, 0, "Table of Contents\nAgent Memory ........ 9", [1.0, 0.0]),
                VectorRecord(1, 1, "Agent memory stores durable user preferences.", [0.9, 0.1]),
            ]
            reranked, metadata = reranker_module.rerank_with_optional_flashrank(
                "durable user preferences",
                records,
                1,
            )

        self.assertEqual(reranked, records[:1])
        self.assertEqual(metadata["strategy"], "vector")
        self.assertEqual(metadata["reranked_chunks"], 0)

    def test_llama_parse_requires_api_key_when_enabled(self) -> None:
        settings = get_settings()
        settings.document_parser = "llama_parse"
        settings.llama_cloud_api_key = None

        with self.assertRaises(HTTPException) as error:
            load_document_content(b"%PDF-1.4 fake", "paper.pdf")

        self.assertEqual(error.exception.status_code, 400)
        self.assertIn("LLAMA_CLOUD_API_KEY", error.exception.detail)

    def test_llama_parse_markdown_output_flows_into_document_loader(self) -> None:
        settings = get_settings()
        settings.document_parser = "llama_parse"
        settings.llama_cloud_api_key = "test-key"

        class FakeParsedDocument:
            text = "# Main Heading\n\nParsed table content and credits."

        class FakeParser:
            def __init__(self, api_key: str, result_type: str) -> None:
                self.api_key = api_key
                self.result_type = result_type

            async def aload_data(self, file_path: str) -> list[FakeParsedDocument]:
                return [FakeParsedDocument()]

        with patch.object(document_loader, "LlamaParse", FakeParser):
            text = load_document_content(b"%PDF-1.4 fake", "paper.pdf")

        self.assertIn("# Main Heading", text)
        self.assertIn("Parsed table content", text)

    def test_markitdown_parser_flows_into_document_loader(self) -> None:
        import fitz
        if document_loader.MarkItDown is None:
            self.skipTest("MarkItDown is not installed.")

        settings = get_settings()
        settings.document_parser = "markitdown"

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Hello CiteMind!")
        pdf_bytes = doc.write()
        doc.close()

        try:
            text = load_document_content(pdf_bytes, "paper.pdf")
            self.assertIn("Hello CiteMind!", text)
        except HTTPException as error:
            if "MissingDependencyException" in error.detail or "dependencies" in error.detail:
                self.skipTest("MarkItDown is missing optional PDF dependencies.")
            raise

    def test_summary_query_preserves_word_limit_and_uses_smaller_context(self) -> None:
        content = (
            b"Transformer models use attention layers for language modeling. "
            b"Attention helps models connect distant words and concepts. "
            b"Embeddings represent tokens as vectors for neural networks. "
            b"Training updates model weights from large text datasets. "
            b"Evaluation checks whether generated answers are useful and grounded. "
        ) * 80

        with SessionLocal() as db:
            uploaded = run(
                upload_document(
                    UploadFile(filename="summary.md", file=BytesIO(content)),
                    db,
                )
            )
            response = query_documents(
                QueryRequest(
                    query="Give me summary in 100 words.",
                    document_ids=[uploaded.id],
                ),
                db,
            )

        self.assertEqual(response.intent, QueryIntent.SUMMARY.value)
        self.assertEqual(response.word_limit, 100)
        self.assertLessEqual(response.retrieved_chunk_count, 6)

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
