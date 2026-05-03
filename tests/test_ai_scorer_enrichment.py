import asyncio
import unittest
from unittest import mock

import ai_scorer


class AIScorerEnrichmentTests(unittest.TestCase):
    def test_build_scoring_prompt_includes_enriched_context(self):
        rows = [{
            "id": 7,
            "title": "Need better reporting",
            "content": "Reports are manual",
            "enriched_content": "Comments:\n- Every week I copy the same dashboard",
        }]

        prompt = ai_scorer._build_scoring_prompt(rows)

        self.assertIn("[ID:7] Need better reporting", prompt)
        self.assertIn("Reports are manual", prompt)
        self.assertIn("Every week I copy the same dashboard", prompt)

    def test_parse_flagged_ids_handles_json_array(self):
        self.assertEqual(ai_scorer._parse_flagged_ids("```json\n[1, 3]\n```"), [1, 3])

    def test_parse_summary_response_extracts_id_summary_map(self):
        text = '{"7": "用户痛点：慢\\n现有方案缺口：散\\n可做产品机会：自动汇总"}'

        parsed = ai_scorer._parse_summary_response(text)

        self.assertEqual(parsed[7], "用户痛点：慢\n现有方案缺口：散\n可做产品机会：自动汇总")

    def test_summarize_ai_flagged_persists_model_summaries(self):
        rows = [{
            "id": 7,
            "title": "Need better reporting",
            "content": "Reports are manual",
            "enriched_content": "Comments:\n- Every week I copy the same dashboard",
        }]

        async def run():
            with mock.patch.dict("os.environ", {"MINIMAX_API_KEY": "test-key"}, clear=True), \
                 mock.patch.object(ai_scorer.db, "get_ai_summary_candidates", return_value=rows), \
                 mock.patch.object(ai_scorer, "_call_minimax_summaries", return_value={7: "用户痛点：慢"}), \
                 mock.patch.object(ai_scorer.db, "update_ai_summary") as update_ai_summary:
                messages = [message async for message in ai_scorer.summarize_ai_flagged()]
            return messages, update_ai_summary

        messages, update_ai_summary = asyncio.run(run())

        self.assertTrue(any("AI总结" in message for message in messages))
        update_ai_summary.assert_called_once_with(7, "用户痛点：慢")


if __name__ == "__main__":
    unittest.main()
