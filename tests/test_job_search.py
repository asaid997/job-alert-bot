import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from job_filters import assess_job, experience_requirement
import linkedin_scraper as scraper
import messages


class MedicalMatchingTests(unittest.TestCase):
    def test_grade_and_role_boundaries(self):
        cases = [
            ("Trust Doctor ST1/2 Obstetrics and Gynaecology", "matched"),
            ("Senior House Officer in Obstetrics & Gynecology", "matched"),
            ("Junior Clinical Fellow in O & G", "matched"),
            ("Senior Clinical Fellow ST3 Obstetrics", "matched"),
            ("Trust Grade ST 3+ Obs & Gynae", "matched"),
            ("Clinical Fellow ST3–5 Gynaecology", "matched"),
            ("Clinical Fellow ST3-ST8 Obstetrics", "matched"),
            ("Trust Doctor ST1-ST3 O&G", "matched"),
            ("Clinical Fellow ST4+ Gynaecology", "rejected"),
            ("Clinical Fellow ST4–ST6 Obstetrics", "rejected"),
            ("Locum Consultant in Obstetrics", "rejected"),
            ("Specialist Grade Doctor in Gynaecology", "rejected"),
            ("Nurse Practitioner in Gynaecology", "rejected"),
            ("Midwife in Obstetrics", "rejected"),
            ("Physician Associate in O&G", "rejected"),
            ("Trust Doctor in Obstetrics and Gynecology", "review"),
            ("Senior Clinical Fellow in Gynaecology", "review"),
            ("Specialty Doctor in Obstetrics", "review"),
            ("Registrar in O&G", "review"),
            ("Junior Chemical Engineer", "rejected"),
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                status, _ = assess_job({
                    "title": title,
                    "description": "Essential\nAt least two years of clinical experience.",
                })
                self.assertEqual(status, expected)

    def test_experience_boundaries(self):
        cases = [
            ("Essential\n0–5 years of experience", "matched"),
            ("At least 5 years of postgraduate experience required", "matched"),
            ("Minimum 5+ years of experience", "matched"),
            ("Minimum 6 years of postgraduate experience", "rejected"),
            ("A minimum of six years' experience is required", "rejected"),
            ("Must have 72 months of clinical experience", "rejected"),
            ("Must have 60 months of clinical experience", "matched"),
            ("Essential\n3–7 years’ experience", "matched"),
            ("Essential\n6-8 years experience", "rejected"),
            ("More than 5 years of experience required", "rejected"),
            ("A minimum of 5.5 years experience", "rejected"),
            ("No previous experience required", "matched"),
            ("Desirable\nSix years of experience", "review"),
            ("Desirable\nAt least six years of experience", "review"),
            ("Six years of experience preferred", "review"),
            ("Six years of experience, not essential", "review"),
            ("Six years of experience is not required", "review"),
            ("Essential\nTwo years of clinical experience\nDesirable\nSix years of experience", "review"),
            ("At least four years of postgraduate experience, including two years of O&G experience", "matched"),
            ("Our department has 20 years of experience", "review"),
            ("A 12 month contract with experience in O&G", "review"),
            ("", "review"),
        ]
        for description, expected in cases:
            with self.subTest(description=description):
                self.assertEqual(experience_requirement(description)[0], expected)

    def test_details_do_not_confuse_colleagues_with_applicant(self):
        job = {
            "title": "Trust Doctor ST1/2 in O&G",
            "description": "Work with consultants and ST7 registrars.\nEssential\nTwo years of experience",
        }
        self.assertEqual(assess_job(job)[0], "matched")
        job["title"] = "Trust Doctor ST5 in O&G"
        job["description"] = "This post is supported by ST1 doctors.\nEssential\nTwo years of experience"
        self.assertEqual(assess_job(job)[0], "rejected")

    def test_uncertain_and_unrelated_jobs(self):
        self.assertEqual(assess_job({"title": "Trust Doctor ST3 in O&G"})[0], "review")
        self.assertEqual(assess_job({"title": "Trust Doctor"})[0], "review")
        self.assertEqual(assess_job({
            "title": "Junior Clinical Fellow Cardiology", "company": "O&G NHS Trust",
            "description": "Essential\nTwo years of cardiology experience",
        })[0], "rejected")
        self.assertEqual(assess_job({
            "title": "Trust Doctor ST3 in O&G", "closed": True,
        })[0], "rejected")

    def test_grade_in_role_description(self):
        self.assertEqual(assess_job({
            "title": "Senior Clinical Fellow in O&G",
            "description": "Job title: Clinical Fellow ST3+\nEssential\nTwo years of experience",
        })[0], "matched")


class SearchPipelineTests(unittest.TestCase):
    def test_country_searches_have_no_city_or_seniority_restriction(self):
        links = scraper.make_search_links()
        self.assertTrue(any("ST3" in link["title"] for link in links))
        self.assertTrue(any("gynecology" in link["title"] for link in links))
        for link in links:
            query = parse_qs(urlparse(link["url"]).query)
            self.assertEqual(query["geoId"], ["101165590"])
            self.assertEqual(link["region"], "United Kingdom")
            self.assertNotIn("distance", query)
            self.assertNotIn("f_E", query)
            self.assertNotIn("f_WT", query)

    def test_all_dates_backfill(self):
        with patch.object(scraper, "TIME_RANGE", ""):
            query = parse_qs(urlparse(scraper.make_search_links()[0]["url"]).query)
            self.assertNotIn("f_TPR", query)
            self.assertEqual(scraper.time_range_label(), "all posting dates")

    def test_fetch_details_and_duplicate_avoidance(self):
        page = Mock()
        page.locator.return_value.first.inner_text.return_value = "Essential\nTwo years of experience"
        page.get_by_text.return_value.count.return_value = 0
        job = {"title": "Trust Doctor ST3 O&G", "job_id": "123456789"}
        detail_cache = {}
        jobs = scraper.enrich_new_jobs(page, [job, job], set(), detail_cache)
        page.goto.assert_called_once()
        accepted, rejected = scraper.filter_jobs(jobs[:1])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected, [])
        self.assertEqual(accepted[0]["match_status"], "matched")

    def test_unavailable_details_are_reviewed(self):
        page = Mock()
        page.goto.side_effect = TimeoutError()
        job = {"title": "Trust Doctor ST3 O&G", "job_id": "123456789"}
        result = scraper.enrich_new_jobs(page, [job], set(), {})
        accepted, other = scraper.filter_jobs(result)
        self.assertEqual(accepted, [])
        self.assertEqual(other[0]["match_status"], "review")

    def test_known_and_excluded_jobs_do_not_fetch_details(self):
        page = Mock()
        jobs = [
            {"title": "Trust Doctor ST3 O&G", "job_id": "123456789"},
            {"title": "Consultant O&G", "job_id": "987654321"},
        ]
        scraper.enrich_new_jobs(page, jobs, {"123456789"}, {})
        page.goto.assert_not_called()


class AlertTests(unittest.TestCase):
    def test_review_jobs_visible_and_rejected_jobs_hidden(self):
        jobs = [
            {"title": "Trust Doctor ST3 O&G", "match_status": "review", "filter_reason": "Check experience"},
            {"title": "Excluded consultant", "match_status": "rejected", "filter_reason": "Consultant"},
        ]
        report = "\n".join(messages.build_full_search_report_messages(
            [], jobs, [], datetime(2026, 10, 17), 2, "last 1 day",
        ))
        self.assertIn("Needs checking", report)
        self.assertIn("Trust Doctor ST3", report)
        self.assertNotIn("Excluded consultant", report)
        self.assertNotIn("chemical", report)

    def test_long_review_reports_fit_telegram(self):
        jobs = [{
            "title": f"Trust Doctor ST3 O&G {i}", "match_status": "review",
            "filter_reason": "Grade and experience need checking", "location": "Belfast",
            "url": f"https://www.linkedin.com/jobs/view/{123456789 + i}/",
        } for i in range(60)]
        reports = messages.build_full_search_report_messages(
            [], jobs, [], datetime(2026, 10, 17), len(jobs), "last 1 day",
        )
        self.assertGreater(len(reports), 1)
        self.assertTrue(all(len(report) <= messages.TELEGRAM_MESSAGE_LIMIT for report in reports))
        self.assertIn("Trust Doctor ST3 O&amp;G 59", "\n".join(reports))


if __name__ == "__main__":
    unittest.main()
