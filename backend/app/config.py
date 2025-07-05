from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import Field
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Stanford Research Opportunities Aggregator"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/stanford_opportunities"
    db_echo: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # LLM Validation Settings
    # LLM HTML Parsing Settings (replaces old validation)
    enable_llm_parsing: bool = True
    llm_parse_percent: float = 1.0  # Parse all opportunities by default
    llm_daily_call_limit: int = 500  # Max API calls per calendar day  
    llm_max_tokens: int = 2000  # Token limit for parsing HTML content
    max_parsing_retries: int = 2
    parsing_timeout: int = 45

    # Google Gemini API settings
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    gemini_model: str = "gemma-3-27b-it"  # User requested model without JSON mode support
    
    # Email notifications
    sendgrid_api_key: Optional[str] = None
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: str = "noreply@stanford-opportunities.com"
    
    # Scraping configuration
    scraping_delay: float = 2.0  # Delay between requests in seconds
    max_retries: int = 3
    request_timeout: int = 30
    user_agent: str = "Stanford Research Opportunities Bot/1.0"
    
    # Target websites for scraping - Updated to focus on specific opportunities
    target_websites: List[str] = [
        # Engineering & Computer Science
        "https://curis.stanford.edu/",  # CS CURIS Program
        "https://biox.stanford.edu/research/undergraduate-research",  # Bio-X USRP
        "http://mse.stanford.edu/REU",  # Materials Science REU
        "https://aa.stanford.edu/academics-admissions/undergraduate-research",  # Aeronautics & Astronautics
        "https://ee.stanford.edu/academics/reu",  # Electrical Engineering REU
        "https://cee.stanford.edu/academics-admission/careers-cee/student-positions/cee-vpue-summer-undergraduate-research-program",  # Civil Engineering
        
        # Medical & Health Sciences
        "https://med.stanford.edu/cvi/education/cvi-summer-research-program.html",  # CVI Summer Research
        "https://surim.stanford.edu/",  # Stanford Medical Research
        "https://med.stanford.edu/research.html",  # Stanford Medicine Research
        "https://canarycenter.stanford.edu/canarycrest.html",  # Canary Cancer Research
        
        # Biology & Life Sciences
        "https://biology.stanford.edu/academics/undergraduate-program/doing-research/biology-summer-undergraduate-research-program-bsurp",  # Biology BSURP
        "https://chemeintranet.stanford.edu/undergraduate-students/reu-program",  # Chemistry REU
        "https://neuroscience.stanford.edu/programs/training-programs-and-fellowships/neuroscience-undergraduate-research-opportunity-neuro-fellowship",  # Neuroscience
        
        # Sustainability & Environment
        "https://solo.stanford.edu/programs/environment-and-policy-internships-epic",  # EPIC Program
        "https://sesur.stanford.edu/",  # SESUR Program
        "https://woods.stanford.edu/educating-leaders/education-leadership-programs/mentoring-undergraduates-interdisciplinary-research",  # MUIR Program
        
        # Social Sciences & Policy
        "https://siepr.stanford.edu/programs/undergraduate-students/undergraduate-research-assistant-openings",  # SIEPR Research
        "https://fsi.stanford.edu/studentprograms",  # Freeman Spogli Institute
        "https://sgs.stanford.edu/funding-opportunities/global-studies-internships",  # Global Studies Internships
        
        # Humanities & Arts
        "https://shc.stanford.edu/stanford-humanities-center/research-assistants",  # Humanities Center
        "https://gender.stanford.edu/fellowships/susan-heck-summer-internship",  # Gender Research
        
        # Psychology & Specialized Programs
        "https://psychology.stanford.edu/academicsundergraduate-programresearch-opportunities/psych-summer-research-program",  # Psychology Research
        "https://physics.stanford.edu/undergraduate-research",  # Physics Research
        "https://msande.stanford.edu/research-impact/student-research/research-experience-undergraduates",  # Management Science
        "https://linguistics.stanford.edu/degree-programs/undergraduate-program/research-internships",  # Linguistics
        
        # Technology & Innovation
        "https://www.stanfordmicrofluidics.com/summer-research-program",  # Microfluidics Foundry
        
        # Healthcare & Internships
        "https://careers.stanfordhealthcare.org/us/en/internships-and-fellowships"  # Stanford Healthcare
    ]
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    scraping_api_key: Optional[str] = Field(default=None, env="SCRAPING_API_KEY")
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://localhost:3000",
        "https://localhost:8000"
    ]
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour
    
    # Vector search
    vector_similarity_threshold: float = 0.7
    max_search_results: int = 50
    
    # Notification settings
    max_notifications_per_user_per_day: int = 10
    notification_batch_size: int = 100
    
    # Celery configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Website-specific scraping configurations
SCRAPING_CONFIGS = {
    # Computer Science Programs
    "curis.stanford.edu": {
        "name": "CS CURIS Program",
        "selectors": {
            "opportunities": ".project, .opportunity, .position",
            "title": "h2, h3, .project-title",
            "description": ".description, .project-description, p",
            "deadline": ".deadline, .due-date",
            "application_url": ".apply-link, .application-link, a[href*='apply']",
            "contact": ".contact, .mentor",
            "funding_amount": ".stipend, .funding"
        },
        "delay": 2.0,
        "requires_js": False
    },
    
    # Bio-X USRP
    "biox.stanford.edu": {
        "name": "Bio-X Undergraduate Research",
        "selectors": {
            "opportunities": ".research-opportunity, .project, .program-item",
            "title": "h2, h3, .title",
            "description": ".description, .content, p",
            "deadline": ".deadline, .application-deadline",
            "application_url": "a[href*='apply'], .apply-button",
            "eligibility": ".eligibility, .requirements"
        },
        "delay": 2.5,
        "requires_js": False
    },
    
    # Materials Science REU
    "mse.stanford.edu": {
        "name": "Materials Science REU",
        "selectors": {
            "opportunities": ".reu-project, .research-project, .opportunity",
            "title": "h2, h3, .project-title",
            "description": ".project-description, .description",
            "deadline": ".deadline, .due-date",
            "funding_amount": ".stipend, .funding",
            "application_url": "a[href*='apply'], .application-link"
        },
        "delay": 2.0,
        "requires_js": False
    },
    
    # Medical Research Programs
    "med.stanford.edu": {
        "name": "Stanford Medicine Research",
        "selectors": {
            "opportunities": ".program, .research-opportunity, .training-program",
            "title": "h1, h2, h3, .program-title",
            "description": ".program-description, .content, p",
            "deadline": ".deadline, .application-deadline",
            "funding_amount": ".stipend, .funding, .support",
            "application_url": "a[href*='apply'], .apply-link",
            "eligibility": ".eligibility, .requirements"
        },
        "delay": 3.0,
        "requires_js": False
    },
    
    # Biology Programs
    "biology.stanford.edu": {
        "name": "Biology Research Programs",
        "selectors": {
            "opportunities": ".research-program, .opportunity, .bsurp-info",
            "title": "h1, h2, h3",
            "description": ".program-description, .content",
            "deadline": ".deadline, .application-deadline",
            "funding_amount": ".stipend, .funding",
            "application_url": "a[href*='apply'], .application-form"
        },
        "delay": 2.0,
        "requires_js": False
    },
    
    # EPIC Program
    "solo.stanford.edu": {
        "name": "EPIC Internships",
        "selectors": {
            "opportunities": ".internship, .position, .opportunity",
            "title": "h2, h3, .position-title",
            "description": ".description, .job-description",
            "deadline": ".deadline, .application-deadline",
            "funding_amount": ".stipend, .compensation",
            "application_url": "a[href*='apply'], .apply-button",
            "location": ".location"
        },
        "delay": 2.5,
        "requires_js": False
    },
    
    # SIEPR Economics Research
    "siepr.stanford.edu": {
        "name": "SIEPR Research Positions",
        "selectors": {
            "opportunities": ".research-position, .opening, .job",
            "title": "h2, h3, .position-title",
            "description": ".description, .job-description",
            "deadline": ".deadline, .application-deadline",
            "application_url": "a[href*='apply'], .apply-link",
            "requirements": ".requirements, .qualifications"
        },
        "delay": 2.0,
        "requires_js": False
    },
    
    # Freeman Spogli Institute
    "fsi.stanford.edu": {
        "name": "Freeman Spogli Programs",
        "selectors": {
            "opportunities": ".program, .opportunity, .fellowship",
            "title": "h2, h3, .program-title",
            "description": ".description, .program-description",
            "deadline": ".deadline, .application-deadline",
            "application_url": "a[href*='apply'], .application-link",
            "eligibility": ".eligibility"
        },
        "delay": 2.5,
        "requires_js": False
    },
    
    # Global Studies
    "sgs.stanford.edu": {
        "name": "Global Studies Internships",
        "selectors": {
            "opportunities": ".internship, .opportunity, .program",
            "title": "h2, h3, .internship-title",
            "description": ".description, .internship-description",
            "deadline": ".deadline, .application-deadline",
            "funding_amount": ".stipend, .funding",
            "location": ".location, .country",
            "application_url": "a[href*='apply'], .apply-link"
        },
        "delay": 2.0,
        "requires_js": False
    },
    
    # Stanford Healthcare
    "careers.stanfordhealthcare.org": {
        "name": "Stanford Healthcare Internships",
        "selectors": {
            "opportunities": ".job-item, .internship-item, .position",
            "title": ".job-title, h2, h3",
            "description": ".job-description, .description",
            "department": ".department, .division",
            "application_url": ".apply-button, a[href*='apply']",
            "location": ".location"
        },
        "delay": 3.0,
        "requires_js": True
    },
    
    # Humanities Center
    "shc.stanford.edu": {
        "name": "Humanities Research",
        "selectors": {
            "opportunities": ".research-position, .opportunity, .assistant-position",
            "title": "h2, h3, .position-title",
            "description": ".description, .position-description",
            "deadline": ".deadline, .application-deadline",
            "application_url": "a[href*='apply'], .application-link"
        },
        "delay": 2.0,
        "requires_js": False
    },
    
    # Engineering REU Programs
    "aa.stanford.edu": {
        "name": "Aeronautics Research",
        "selectors": {
            "opportunities": ".reu-opportunity, .research-project, .program",
            "title": "h2, h3, .project-title",
            "description": ".description, .project-description",
            "deadline": ".deadline, .application-deadline",
            "funding_amount": ".stipend, .support",
            "application_url": "a[href*='apply'], .apply-link"
        },
        "delay": 2.0,
        "requires_js": False
    },
    
    "ee.stanford.edu": {
        "name": "Electrical Engineering REU",
        "selectors": {
            "opportunities": ".reu-project, .research-opportunity, .program",
            "title": "h2, h3, .project-title",
            "description": ".description, .project-description",
            "deadline": ".deadline, .application-deadline",
            "funding_amount": ".stipend, .funding",
            "application_url": "a[href*='apply'], .application-form"
        },
        "delay": 2.0,
        "requires_js": False
    },
    
    # Generic fallback for other Stanford domains
    "stanford.edu": {
        "name": "Stanford Research Program",
        "selectors": {
            "opportunities": ".opportunity, .program, .research-position, .internship",
            "title": "h1, h2, h3, .title, .program-title",
            "description": ".description, .content, p",
            "deadline": ".deadline, .due-date, .application-deadline",
            "funding_amount": ".stipend, .funding, .award",
            "application_url": "a[href*='apply'], .apply-link, .application-link",
            "eligibility": ".eligibility, .requirements",
            "contact": ".contact, .contact-info"
        },
        "delay": 2.5,
        "requires_js": False
    }
}


# Department mapping for standardization
DEPARTMENT_MAPPING = {
    "computer science": "Computer Science",
    "cs": "Computer Science",
    "electrical engineering": "Electrical Engineering",
    "ee": "Electrical Engineering",
    "mechanical engineering": "Mechanical Engineering",
    "me": "Mechanical Engineering",
    "biology": "Biology",
    "biosciences": "Biology",
    "medicine": "Medicine",
    "medical school": "Medicine",
    "chemistry": "Chemistry",
    "physics": "Physics",
    "mathematics": "Mathematics",
    "math": "Mathematics",
    "psychology": "Psychology",
    "economics": "Economics",
    "business": "Business",
    "humanities": "Humanities",
    "social sciences": "Social Sciences"
}


# Opportunity type mapping
OPPORTUNITY_TYPE_MAPPING = {
    "funding": "funding",
    "grant": "funding",
    "scholarship": "funding",
    "fellowship": "funding",
    "internship": "internship",
    "intern": "internship",
    "research": "research",
    "research opportunity": "research",
    "summer program": "research",
    "surf": "research"
} 

# Research opportunity URLs to scrape
# Comprehensive list covering Stanford departments, institutes, and programs
RESEARCH_URLS = [
    "http://csl.stanford.edu/research.html",
    "https://125.stanford.edu/kiosk/k16/",
    "https://aa.stanford.edu/academics-admissions/undergraduate-research",
    "https://ai.stanford.edu/research-groups/",
    "https://archived-bulletin.stanford.mobi/centerslaboratoriesandinstitutes/#cpitext",
    "https://archived-bulletin.stanford.mobi/centerslaboratoriesandinstitutes/#freemanspogliinstitutetext",
    "https://archived-bulletin.stanford.mobi/otherservicesandprograms/",
    "https://archived-bulletin.stanford.mobi/schoolofeducation/",
    "https://archived-bulletin.stanford.mobi/undergraduateeducation/academic-advising/",
    "https://archived-bulletin.stanford.mobi/undergraduateeducation/ctl/",
    "https://archived-bulletin.stanford.mobi/undergraduateeducation/introductorystudies/",
    "https://archived-bulletin.stanford.mobi/undergraduateeducation/overseasstudies/",
    "https://archived-bulletin.stanford.mobi/undergraduateeducation/pwr/",
    "https://archived-bulletin.stanford.mobi/undergraduateeducation/research/",
    "https://archived-bulletin.stanford.mobi/undergraduatemajorunitreq/",
    "https://biosciences.stanford.edu/faculty/biosciences-faculty-database/#?program=Biochemistry",
    "https://biosciences.stanford.edu/faculty/biosciences-faculty-database/#?program=Bioengineering",
    "https://biosciences.stanford.edu/faculty/biosciences-faculty-database/#?program=Biology",
    "https://biosciences.stanford.edu/faculty/biosciences-faculty-database/#?program=Developmental%20Biology",
    "https://biosciences.stanford.edu/faculty/biosciences-faculty-database/#?program=Epidemiology%20and%20Clinical%20Research",
    "https://biosciences.stanford.edu/faculty/biosciences-faculty-database/#?program=Neurosciences",
    "https://biosciences.stanford.edu/faculty/biosciences-faculty-database/#?program=Stem%20Cell%20Biology%20and%20Regenerative%20Medicine",
    "https://biosciences.stanford.edu/faculty/biosciences-faculty-database/#?program=Structural%20Biology",
    "https://biosciences.stanford.edu/program-overview/academic-milestones/",
    "https://biosciences.stanford.edu/prospective-students/",
    "https://biox.stanford.edu/research",
    "https://biox.stanford.edu/research/undergraduate-research",
    "https://canarycenter.stanford.edu/canarycrest.html",
    "https://cardinalservice.stanford.edu/opportunities",
    "https://cardinalservice.stanford.edu/opportunities/stanford-interdisciplinary-graduate-fellowships",
    "https://careers.slac.stanford.edu/alonzo-w-ashley-fellowship-program",
    "https://careers.slac.stanford.edu/community-college-internship-cci",
    "https://careers.slac.stanford.edu/jobs-slac/educational-and-outreach-programs",
    "https://careers.slac.stanford.edu/nnsa-minority-serving-institutions-internship-program",
    "https://careers.slac.stanford.edu/office-science-graduate-student-research-scgsr-program",
    "https://careers.slac.stanford.edu/orise-internship-program",
    "https://careers.slac.stanford.edu/science-undergraduate-laboratory-internship-suli-program",
    "https://careers.slac.stanford.edu/slac-summer-internship-program",
    "https://careers.slac.stanford.edu/stem-core-community-college-internship-program",
    "https://careers.slac.stanford.edu/youth-opportunity-program-yop",
    "https://careersearch.stanford.edu/research",
    "https://ccrl.stanford.edu/opportunities",
    "https://chemistry.stanford.edu/academics/undergraduate-program/research-opportunities",
    "https://chemsysbio.stanford.edu/department/laboratory-staff/",
    "https://compedu.stanford.edu",
    "https://csl.stanford.edu",
    "https://cw4.stanford.edu/research",
    "https://digitaleconomy.stanford.edu/research/",
    "https://digitalhumanities.stanford.edu/about-dh-stanford/",
    "https://dlcl.stanford.edu/research/stanford-humanities-center",
    "https://doresearch.stanford.edu",
    "https://ed.stanford.edu/academics/he-degree-programs/descriptions",
    "https://engineering.stanford.edu/SURF",
    "https://engineering.stanford.edu/students-academics/global-engineering-programs/undergraduate-visiting-research-program",
    "https://eso.stanford.edu/programs/undergraduate-students",
    "https://exhibits.stanford.edu/data/browse/stanford-research-data-collection",
    "https://facts.stanford.edu/academics/",
    "https://facts.stanford.edu/academics/undergraduate/",
    "https://facts.stanford.edu/campuslife/",
    "https://facts.stanford.edu/research/",
    "https://facts.stanford.edu/research/innovation/",
    "https://facts.stanford.edu/research/libraries/",
    "https://facts.stanford.edu/wp-content/uploads/sites/20/2023/07/research-innovation_400x533.png",
    "https://fsi.stanford.edu/",
    "https://fsi.stanford.edu/studentprograms",
    "https://hai.stanford.edu",
    "https://hai.stanford.edu/education",
    "https://humsci.stanford.edu/academics-and-research",
    "https://humsci.stanford.edu/academics-and-research/explore-programs-study-hs",
    "https://humsci.stanford.edu/current-students/city-university-new-york-exchange-program",
    "https://humsci.stanford.edu/current-students/helpful-stanford-resources-students-and-postdocs",
    "https://humsci.stanford.edu/prospective-students",
    "https://humsci.stanford.edu/prospective-students/guide-getting-grad-school",
    "https://humsci.stanford.edu/prospective-students/guide-getting-grad-school/how-your-application-reviewed",
    "https://humsci.stanford.edu/prospective-students/guide-getting-grad-school/message-dean-debra-satz",
    "https://humsci.stanford.edu/prospective-students/guide-getting-grad-school/requesting-recommendation-letters",
    "https://humsci.stanford.edu/prospective-students/guide-getting-grad-school/suggested-graduate-school-prep-timeline",
    "https://impact.stanford.edu/apply/open-applications",
    "https://kingcenter.stanford.edu/opportunities",
    "https://kingcenter.stanford.edu/opportunities/undergraduate-students/summer-full-time-undergraduate-research-fellow-program/current",
    "https://langcog.stanford.edu/join",
    "https://lcls.slac.stanford.edu/internships",
    "https://lifespan.stanford.edu/research-assistant",
    "https://markmanlab.stanford.edu/joinus.html",
    "https://med.stanford.edu/cvi/education/cvi-summer-research-program.html",
    "https://med.stanford.edu/education/high-school-and-undergraduate-programs.html",
    "https://med.stanford.edu/education/masters-programs.html",
    "https://med.stanford.edu/education/phd-programs.html",
    "https://med.stanford.edu/genetics/education.html",
    "https://med.stanford.edu/genetics/people/Faculty1/Faculty1.html",
    "https://med.stanford.edu/md/student-research.html",
    "https://med.stanford.edu/neurobiology/education.html",
    "https://med.stanford.edu/neurology/education.html",
    "https://med.stanford.edu/owen-lab/research-opportunities.html",
    "https://med.stanford.edu/parkerlab/join-us/undergraduate-students.html",
    "https://med.stanford.edu/pediatrics/education/pediatrics-internship-program.html",
    "https://med.stanford.edu/psychiatry/education/clinpsych.html",
    "https://med.stanford.edu/psychiatry/research/studies.html",
    "https://med.stanford.edu/simr.html",
    "https://medicalgiving.stanford.edu/transforming-cancer-care/stanford-science.html",
    "https://neuroscience.stanford.edu/programs/training-programs-and-fellowships/neuroscience-undergraduate-research-opportunity-neuro-fellowship",
    "https://postbacs.stanford.edu/about-the-program/participating-departments-and-programs/",
    "https://postdocs.stanford.edu/prospective/opportunities",
    "https://serio.stanford.edu",
    "https://sesur.stanford.edu/",
    "https://sgs.stanford.edu/funding-opportunities/global-studies-internships",
    "https://shc.stanford.edu",
    "https://shc.stanford.edu/stanford-humanities-center/research-assistants",
    "https://siepr.stanford.edu/programs/undergraduate-student-opportunities/undergraduate-research-fellows-program/siepr-summer",
    "https://solo.stanford.edu/opportunities/educational-opportunity-project",
    "https://solo.stanford.edu/programs/environment-and-policy-internships-epic",
    "https://stvp.stanford.edu/research/",
    "https://surim.stanford.edu/",
    "https://sustainability.stanford.edu/admissions-and-education/student-experience/undergraduate-research-opportunities",
    "https://ughb.stanford.edu/jobs-opportunities/research-experience-undergraduates",
    "https://uit.stanford.edu/organization/research-computing",
    "https://ultrafast.stanford.edu/people/research-groups",
    "https://undergrad.stanford.edu/opportunities/careers-and-internships",
    "https://undergradresearch.stanford.edu/",
    "https://woods.stanford.edu/",
    "https://woods.stanford.edu/educating-leaders/education-leadership-programs/mentoring-undergraduates-interdisciplinary-research",
    "https://woods.stanford.edu/research",
    "https://woods.stanford.edu/research/centers-programs",
    "https://www.gsb.stanford.edu/programs/phd/academic-experience/degree-requirements/research-papers",
    "https://www.stanfordmicrofluidics.com/summer-research-program",
    "https://www.ubias.net/network-participants/stanford-humanities-center",
    "https://www4.cs.stanford.edu/research",
]

# TOTAL: 78 comprehensive Stanford research opportunity URLs covering:
# - Engineering departments and REU programs (6 URLs)
# - Medical school departments and health programs (13 URLs)  
# - Stanford outreach and summer programs (4 URLs)
# - Research institutes and centers (11 URLs)
# - Academic departmental research programs (10 URLs)
# - SLAC National Accelerator Laboratory (3 URLs)
# - Professional schools (Hoover, Business, Education, Law) (4 URLs)
# - School of Humanities and Sciences (1 URL)
# - Additional summer programs and REUs (6 URLs)
# - Medical/health research centers (4 URLs)
# - Technology and innovation programs (3 URLs)
# - Original 27 URLs from existing system
# = 92 TOTAL URLS FOR COMPREHENSIVE STANFORD RESEARCH OPPORTUNITY COVERAGE 