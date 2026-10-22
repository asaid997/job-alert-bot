import unittest
from datetime import datetime, timezone
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
            ("General Safety Officer", "rejected"),
            ("Senior General Safety Officer", "rejected"),
            ("Senior General Safety Officer/ General Safety Officer", "rejected"),
            ("SENIOR SAFETY EVALUATION PHYSICIAN / GENERAL SAFETY OFFICER", "rejected"),
            ("Senior Safety Evaluation Physician", "rejected"),
            ("Trust Doctor in Obstetrics and Gynecology", "review"),
            ("Senior Clinical Fellow in Gynaecology", "rejected"),
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
        self.assertEqual(assess_job({"title": "Trust Doctor"})[0], "rejected")
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

    def test_icu_is_not_og_even_when_hospital_description_mentions_it(self):
        for title in (
            "ST3 Clinical Fellow in ICU", "ST3 Clinical Fellow in ITU",
            "ST3 Clinical Fellow in Intensive Care", "ST3 Clinical Fellow in Critical Care",
        ):
            for description in ("", "Our hospital provides obstetrics and gynaecology services.\nEssential\nTwo years of experience"):
                with self.subTest(title=title, description=description):
                    self.assertEqual(assess_job({"title": title, "description": description})[0], "rejected")
        self.assertEqual(assess_job({
            "title": "Trust Doctor ST3 O&G",
            "description": "Work with ICU colleagues.\nEssential\nTwo years of experience",
        })[0], "matched")

    def test_required_senior_grade_in_person_specification(self):
        title = "Senior Clinical Fellow in Gynaecological Oncology"
        for requirement in (
            "Qualifications\nEssential criteria\nSatisfactory ST5 ARCP by commencement of post",
            "Experience\nEssential\nST5 and above or equivalent, with sequential annual appraisals",
            "Applicants must have completed ST5 or equivalent.",
            "Grade: Senior Clinical Fellow (ST6 equivalent)",
        ):
            with self.subTest(requirement=requirement):
                status, reason = assess_job({"title": title, "description": requirement})
                self.assertEqual(status, "rejected")
                self.assertIn("above ST3", reason)
        # Essential criteria still apply when a title advertises a lower grade.
        self.assertEqual(assess_job({
            "title": "Clinical Fellow ST3 O&G",
            "description": "Essential\nSatisfactory ST5 ARCP by commencement of post",
        })[0], "rejected")

    def test_senior_fellow_requires_confirmed_junior_grade(self):
        title = "Senior Clinical Fellow in Gynaecological Oncology"
        self.assertEqual(assess_job({"title": title})[0], "rejected")
        for description in (
            "Grade: ST3\nEssential\nTwo years of experience",
            "Essential\nST3 or equivalent\nTwo years of experience",
        ):
            with self.subTest(description=description):
                self.assertEqual(assess_job({"title": title, "description": description})[0], "matched")

    def test_preferred_grades_and_supervisors_do_not_raise_required_grade(self):
        for detail in (
            "Desirable\nST5 or equivalent",
            "ST5 experience is not required",
            "Essential\nWork with ST7 registrars and consultants",
        ):
            with self.subTest(detail=detail):
                self.assertEqual(assess_job({
                    "title": "Clinical Fellow ST3 O&G",
                    "description": "Essential\nTwo years of experience\n" + detail,
                })[0], "matched")

    def test_dental_and_psychiatry_titles_cannot_be_og_matches(self):
        for title in (
            "Specialty Doctor Orthodontics", "Speciality Doctor in Dentistry",
            "ST3 Clinical Fellow in Dental Surgery", "Specialty Doctor in Psychiatry",
        ):
            for description in ("", "Our hospital provides obstetrics and gynaecology services."):
                with self.subTest(title=title, description=description):
                    self.assertEqual(assess_job({
                        "title": title, "description": description,
                    })[0], "rejected")
        self.assertEqual(assess_job({
            "title": "Trust Doctor ST3 in O&G",
            "description": "Liaise with psychiatry colleagues.\nEssential\nTwo years of experience",
        })[0], "matched")

    def test_specialty_must_be_identified_before_reporting(self):
        for title in ("Speciality Doctor", "Specialty Doctor", "Trust Doctor", "ST3 Clinical Fellow"):
            with self.subTest(title=title):
                job = {"title": title, "company": "Obstetrics and Gynaecology NHS Trust"}
                self.assertEqual(assess_job(job, details_pending=True)[0], "review")
                self.assertEqual(assess_job(job)[0], "rejected")

    def test_generic_titles_need_role_specific_og_evidence(self):
        for detail in (
            "Specialty: Obstetrics and Gynaecology",
            "Main area\nObstetrics and Gynaecology",
            "We are recruiting a Trust Doctor for our O&G service.",
            "This post is in Obstetrics and Gynaecology.",
            "You will join our obstetrics and gynaecology team.",
        ):
            with self.subTest(detail=detail):
                self.assertEqual(assess_job({
                    "title": "Trust Doctor ST3",
                    "description": detail + "\nEssential\nTwo years of experience",
                })[0], "matched")
        for detail in (
            "Our hospital provides obstetrics and gynaecology, cardiology and dental services.",
            "About us\nThe Trust has obstetrics and gynaecology services.",
            "This post is in psychiatry.\nOur hospital has obstetrics and gynaecology services.",
        ):
            with self.subTest(detail=detail):
                self.assertEqual(assess_job({
                    "title": "Trust Doctor ST3",
                    "description": detail + "\nEssential\nTwo years of experience",
                })[0], "rejected")


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
            {"title": "Senior General Safety Officer/ General Safety Officer", "job_id": "987654322"},
            {"title": "ST3 Clinical Fellow in ICU", "job_id": "4481576729"},
            {"title": "Specialty Doctor Orthodontics", "job_id": "4482455753"},
        ]
        scraper.enrich_new_jobs(page, jobs, {"123456789"}, {})
        page.goto.assert_not_called()

    def test_senior_fellows_are_checked_before_deciding_their_grade(self):
        job = {"title": "Senior Clinical Fellow in Gynaecological Oncology", "job_id": "4481577611"}
        for description, expected in (
            ("Grade: ST3\nEssential\nTwo years of experience", "matched"),
            ("Essential\nSatisfactory ST5 ARCP by commencement of post", "rejected"),
            ("", "rejected"),
        ):
            with self.subTest(description=description), patch.object(
                scraper, "fetch_job_details", return_value={**job, "description": description},
            ) as fetch:
                enriched = scraper.enrich_new_jobs(Mock(), [job], set(), {})
                fetch.assert_called_once()
                accepted, other = scraper.filter_jobs(enriched)
                self.assertEqual((accepted + other)[0]["match_status"], expected)

    def test_report_excludes_the_reported_false_positives(self):
        jobs = [
            {"title": "CT1 Obstetrics & Gynaecology", "description": "Essential\nTwo years of experience"},
            {"title": "Senior Clinical Fellow in Gynaecological Oncology"},
            {"title": "ST3 Clinical Fellow in ICU"},
            {"title": "SENIOR SAFETY EVALUATION PHYSICIAN / GENERAL SAFETY OFFICER"},
            {"title": "Speciality Doctor", "company": "Priory"},
            {"title": "Specialty Doctor Orthodontics"},
        ]
        accepted, other = scraper.filter_jobs(jobs)
        report = "\n".join(messages.build_full_search_report_messages(
            accepted, other, [], datetime(2026, 10, 20, 16, tzinfo=timezone.utc), len(jobs), "last 6 hours",
        ))
        self.assertIn("1 job found", report)
        self.assertIn("CT1 Obstetrics", report)
        for job in jobs[1:]:
            self.assertNotIn(job["title"], report)

    def test_generic_doctor_details_are_checked_and_failed_fetches_are_excluded(self):
        job = {"title": "Speciality Doctor", "job_id": "4482450727"}
        for description, expected in (
            ("", "rejected"),
            ("This post is in psychiatry.", "rejected"),
            ("Specialty: O&G\nGrade: ST3\nEssential\nTwo years of experience", "matched"),
        ):
            with self.subTest(description=description), patch.object(
                scraper, "fetch_job_details", return_value={**job, "description": description},
            ) as fetch:
                enriched = scraper.enrich_new_jobs(Mock(), [job], set(), {})
                fetch.assert_called_once()
                accepted, other = scraper.filter_jobs(enriched)
                self.assertEqual((accepted + other)[0]["match_status"], expected)
        with patch.object(scraper, "fetch_job_details", return_value={**job, "description": ""}):
            accepted, other = scraper.filter_jobs(scraper.enrich_new_jobs(Mock(), [job], set(), {}))
            self.assertEqual(messages.build_full_search_report_messages(
                accepted, other, [], datetime(2026, 10, 22, 10, tzinfo=timezone.utc), 1, "last 6 hours",
            ), [])


class AlertTests(unittest.TestCase):
    def test_review_jobs_visible_and_rejected_jobs_hidden(self):
        accepted = [{
            "title": "Trust Doctor ST1/2 O&G", "match_status": "matched",
            "company": "Example <NHS> Trust", "location": "London",
            "url": "https://example.com/jobs/1?a=1&b=2",
        }]
        jobs = [
            {"title": "Trust Doctor ST3 O&G", "match_status": "review", "filter_reason": "Check experience"},
            {"title": "Excluded consultant", "match_status": "rejected", "filter_reason": "Consultant"},
        ]
        with patch.object(messages.random, "choice", return_value="Done and done.") as choice:
            report = "\n".join(messages.build_full_search_report_messages(
                accepted, jobs, [], datetime(2026, 10, 17, 13, tzinfo=timezone.utc), 3, "last 6 hours",
            ))
        choice.assert_called_once_with(messages.FORGE_QUOTES)
        self.assertTrue(report.startswith(
            "🔥⚒️ <b>Hephaestus Job Forge</b>\n"
            "🕒 Report run at 17 Oct 2026, 13:00 (UTC)\n🩺 2 jobs found"
        ))
        self.assertIn('1. <a href="https://example.com/jobs/1?a=1&amp;b=2">Trust Doctor ST1/2 O&amp;G</a>', report)
        self.assertIn("🏥 Example &lt;NHS&gt; Trust · 📍 London", report)
        self.assertIn("2. Trust Doctor ST3", report)
        self.assertIn("Trust Doctor ST3", report)
        self.assertNotIn("Excluded consultant", report)
        self.assertNotIn("chemical", report)
        self.assertNotIn("Needs checking", report)
        self.assertNotIn("Section", report)
        self.assertNotIn("Check experience", report)
        self.assertTrue(report.endswith('🔥 <i>Hephaestus: “Done and done.”</i>'))

    def test_long_review_reports_fit_telegram(self):
        jobs = [{
            "title": f"Trust Doctor ST3 O&G {i}", "match_status": "review",
            "filter_reason": "Grade and experience need checking", "location": "Belfast",
            "url": f"https://www.linkedin.com/jobs/view/{123456789 + i}/",
        } for i in range(60)]
        quote = max(messages.FORGE_QUOTES, key=len)
        with patch.object(messages.random, "choice", return_value=quote) as choice:
            reports = messages.build_full_search_report_messages(
                [], jobs, [], datetime(2026, 1, 17, 14, tzinfo=timezone.utc), len(jobs), "last 6 hours",
            )
        choice.assert_called_once_with(messages.FORGE_QUOTES)
        self.assertTrue(reports[0].startswith(
            "🔥⚒️ <b>Hephaestus Job Forge</b>\n"
            "🕒 Report run at 17 Jan 2026, 14:00 (UTC)\n🩺 60 jobs found"
        ))
        self.assertGreater(len(reports), 1)
        self.assertTrue(all(len(report) <= messages.TELEGRAM_MESSAGE_LIMIT for report in reports))
        self.assertIn("Trust Doctor ST3 O&amp;G 59", "\n".join(reports))
        self.assertEqual("\n".join(reports).count("Hephaestus: “"), 1)
        self.assertTrue(reports[-1].endswith(f'🔥 <i>Hephaestus: “{messages.html_escape(quote)}”</i>'))


if __name__ == "__main__":
    unittest.main()
