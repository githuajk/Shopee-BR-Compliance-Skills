"""Shopee BR Compliance Agent — local rule-based listing compliance review.

Public API::

    from compliance_agent import Reviewer, load_rules
    reviewer = Reviewer(load_rules())
    result = reviewer.review(products)
"""
from .engine.loader import load_lexicon, load_rules
from .engine.reviewer import Reviewer, write_result
from .models import Case, Finding, Product, Rule
from .report.markdown import render_report, write_report

__version__ = "0.1.0"

__all__ = [
    "Case", "Finding", "Product", "Reviewer", "Rule",
    "load_lexicon", "load_rules", "render_report", "write_report",
    "write_result",
]
