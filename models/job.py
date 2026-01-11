"""Job data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    """Represents a job posting from any company."""

    # Required fields
    id: str                      # Unique ID from the company's system
    title: str
    company: str                 # Company name (e.g., "Amazon", "Google")
    url: str                     # Direct link to the job posting

    # Location
    location: str                # Full location string
    city: Optional[str] = None
    country: str = "Germany"

    # Dates
    posted_date: Optional[str] = None      # When the job was posted
    updated_time: Optional[str] = None     # Last update (e.g., "16 days ago")

    # Metadata
    source: str = ""             # Scraper that found this job
    scraped_at: datetime = field(default_factory=datetime.now)

    # Optional details
    description: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None         # full-time, part-time, intern, etc.
    department: Optional[str] = None       # Department/team name

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "location": self.location,
            "city": self.city,
            "country": self.country,
            "posted_date": self.posted_date,
            "updated_time": self.updated_time,
            "source": self.source,
            "scraped_at": self.scraped_at.isoformat(),
            "description": self.description,
            "salary": self.salary,
            "job_type": self.job_type,
            "department": self.department,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Create a Job from a dictionary."""
        scraped_at = data.get("scraped_at")
        if isinstance(scraped_at, str):
            scraped_at = datetime.fromisoformat(scraped_at)
        elif scraped_at is None:
            scraped_at = datetime.now()

        return cls(
            id=data["id"],
            title=data["title"],
            company=data["company"],
            url=data["url"],
            location=data.get("location", ""),
            city=data.get("city"),
            country=data.get("country", "Germany"),
            posted_date=data.get("posted_date"),
            updated_time=data.get("updated_time"),
            source=data.get("source", ""),
            scraped_at=scraped_at,
            description=data.get("description"),
            salary=data.get("salary"),
            job_type=data.get("job_type"),
            department=data.get("department"),
        )

    def __str__(self) -> str:
        return f"[{self.company}] {self.title} - {self.city or self.location}"
