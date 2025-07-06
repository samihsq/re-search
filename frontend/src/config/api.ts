// API configuration for production deployment
const getApiBaseUrl = () => {
  // In production (GitHub Pages), use the deployed AWS API
  if (process.env.NODE_ENV === 'production') {
    return 'https://nzl4dbhfje.execute-api.us-west-2.amazonaws.com';  // Your deployed API
  }
  // In development, use localhost
  return process.env.REACT_APP_API_URL || 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

export const API_ENDPOINTS = {
  opportunities: `${API_BASE_URL}/api/opportunities`,
  scraping: `${API_BASE_URL}/api/opportunities/scrape`,
  stats: `${API_BASE_URL}/api/opportunities/stats`,
  search: `${API_BASE_URL}/api/opportunities/search`,
  health: `${API_BASE_URL}/health`,
  ping: `${API_BASE_URL}/ping`,
  docs: `${API_BASE_URL}/docs`,
  // Add other endpoints as needed
};

export default API_ENDPOINTS; 