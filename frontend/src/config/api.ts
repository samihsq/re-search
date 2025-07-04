const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  opportunities: `${API_BASE_URL}/api/opportunities`,
  scraping: `${API_BASE_URL}/api/opportunities/scrape`,
  stats: `${API_BASE_URL}/api/opportunities/stats`,
  search: `${API_BASE_URL}/api/opportunities/search`,
  health: `${API_BASE_URL}/health`,
  // Add other endpoints as needed
};

export default API_BASE_URL; 