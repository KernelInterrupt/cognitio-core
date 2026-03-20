We are building a system to help users read research papers more effectively.

This is NOT a chatbot.
This is NOT a summarization tool.

The goal is:
- Guide user attention during reading
- Highlight important parts
- Provide contextual annotations tied to specific paragraphs

The system should simulate a "guided reading process" instead of generating one-shot answers.

The backend should support:

1. Paper ingestion
   - Input: PDF or parsed text
   - Output: structured paragraphs with IDs

2. Attention guidance pipeline
   - Process paper sequentially (paragraph by paragraph)
   - For each paragraph:
       - decide importance level
       - optionally generate annotation

3. Annotation system
   Each annotation should include:
   - target_paragraph_id
   - type (summary | intuition | critique | highlight)
   - content (user language, e.g. Chinese)
   - importance score

4. Highlight system
   - Mark paragraphs with importance levels
   - Support multiple levels (skip / normal / important / critical)

5. Streaming process
   - The system should simulate a reading process:
       "reading paragraph 3"
       "generating annotation"
   - Output should be incremental (not one-shot)

6. Editing sandbox (important)
   - Single virtual file for each annoation (file.tex or similar)
   - AI can read/write this file
   - Compile step returns errors

The AI should behave like a reading guide, not an answer generator.

It should:
- decide where the user should focus
- avoid over-explaining everything
- prioritize attention allocation over information generation

Bad behavior:
- explaining every paragraph
- generating long summaries
- acting like ChatGPT

Good behavior:
- selective highlighting
- minimal but precise annotations
- guiding reading flow


