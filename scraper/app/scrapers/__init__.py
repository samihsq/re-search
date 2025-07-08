# Web scrapers for Stanford websites 
from .base_scraper import BaseScraper
from .undergrad_research_scraper import UndergradResearchScraper
from .stanford_program_scraper import StanfordProgramScraper

__all__ = [
    'BaseScraper',
    'UndergradResearchScraper',
    'StanfordProgramScraper'
] 