# Program JSON schema (one file per program: data/programs/<slug>.json)

{
  "slug": "mdiv",                      // ats | bts | mbs | mts | bdiv | mdiv | thm-nc | thd-nc | dmin | thd-puritan | thd-church-history
  "name": "Master of Divinity",        // exactly as in the guide header (minus the word "Program")
  "credit_hours": 116,                 // from the header line
  "admission": "Baccalaureate degree (in any field) or equivalent",   // header "Admission requirements:" text, cleaned
  "requirements": [                    // the general lines after the course list, in order, cleaned
    "Complete the Comprehensive Final Exam",
    "All written assignments should follow current MLA formatting.",
    "..."
  ],
  "course_list": [                     // the overview list at the top, in order
    { "code": "BS100", "title": "Bible Study Skills", "credits": 2, "group": null }
    // "group": if the guide groups courses under a heading (e.g. "Core Courses",
    // "Concentration: Apologetics", "Electives (choose 2)"), put that heading here, else null
  ],
  "courses": [                         // one entry per course DETAIL block, in document order
    {
      "code": "BS100",
      "title": "Bible Study Skills",
      "credits": 2,
      "scripture_reading": null,       // the "Read: Genesis - Malachi (...)" line text if present, without "Read:"
      "sections": [
        {
          "n": 1,                      // the assignment number as printed (1., 2., ...); null for un-numbered blocks like "Review:"
          "type": "lectures",          // lectures | readings | assignment | review
          "instruction": "Listen, outline, and take notes on the following lectures:",
          "items": [
            { "title": "Why Study the Bible?", "by": "Dr. R.C. Sproul", "extent": "27 min", "minutes": 27, "pages": null, "note": null }
          ],
          "total": "27 hours"          // the "Total:" line for this section if printed, else null
        },
        {
          "n": 4, "type": "readings",
          "instruction": "Read and provide chapter summaries:",
          "items": [
            { "title": "The Bible Handbook: Part I, Chapters 8-10", "by": "Joseph Angus", "extent": "204 pp.", "minutes": null, "pages": 204, "note": null }
          ],
          "total": "319 pages"
        },
        { "n": 5, "type": "assignment", "instruction": "Complete a 5 page inductive Bible study on a selected passage of Scripture.", "items": [], "total": null }
      ]
    }
  ]
}

Rules
- "lectures" = a numbered task whose items are audio/video lectures (durations in [..]).
- "readings" = a numbered task whose items are books/articles (page counts in [..], or no count).
- "assignment" = a task with no item list (write a paper, complete a study, read Psalm 119 and list...).
- "review" = an un-numbered "Review:" list of resources.
- minutes: convert durations to integer minutes (e.g. "1h20m" -> 80, "2.5h" -> 150, "12 hours" -> 720, "[1hour 17min]" -> 77). pages: integer from [..]. extent: a clean human string ("1 h 20 min", "204 pp."). If no figure printed, extent/minutes/pages are null.
- "by": the speaker/author after the dash, with honorifics as printed ("Dr. R.C. Sproul"). If none, null.
- Parenthetical qualifiers like "(video)", "(5 in all)", "(pp. 20-26 of The Self-Interpreting Bible)" stay in the title or go in "note" — keep the information, never drop it.
- Fix OCR errors so the text matches the actual page: "J.1. Packer" -> "J.I. Packer", "lan Murray" -> "Iain Murray" ONLY if the image shows "Iain"; "[SOmin]" -> 50 min; "Part |" -> "Part I"; "II!" -> "III"; "aS page" -> "a 5 page"; truncated titles like "The Doctrine of Si" must be read from the page image. Never invent text: when the image is genuinely unreadable, keep your best reading and add "note": "uncertain OCR".
- Drop page furniture: running headers ("The Log College & Seminary"), page numbers, stray OCR garbage lines.
- Keep the exact document order of courses and items.
- Output must be valid JSON (no comments).
