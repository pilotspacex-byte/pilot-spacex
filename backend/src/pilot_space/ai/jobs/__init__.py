"""Background job handlers for AI-driven tasks.

Jobs:
- DigestJobHandler: Generates workspace digest suggestions hourly
"""

from pilot_space.ai.jobs.digest_job import DigestJobHandler

__all__ = ["DigestJobHandler"]
