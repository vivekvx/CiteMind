# Sample AI Research Report

Artificial intelligence systems are increasingly used to summarize documents, answer domain questions, and support research workflows. Retrieval-augmented generation improves answer quality by grounding model responses in source material instead of relying only on model memory.

Citation-first research assistants should return both an answer and the evidence used to produce it. This makes the workflow easier to audit, especially when users need to compare claims against original documents.

RAG evaluation commonly checks faithfulness, answer relevance, context relevance, and citation coverage. Faithfulness measures whether the answer is supported by retrieved context. Answer relevance measures whether the answer addresses the query. Context relevance measures whether retrieved passages are useful for the query. Citation coverage measures whether answer claims are connected to cited evidence.

For local demos, heuristic evaluation can provide rough scores without requiring an external model. In production, LLM-based judges can provide more flexible grading when prompts and rubrics are carefully designed.
