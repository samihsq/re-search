// API configuration for production deployment
const getApiBaseUrl = () => {
  // In production, nginx proxies /api to the backend
  // So we can use relative URLs
  if (process.env.NODE_ENV === 'production') {
    return '';  // Use relative URLs in production
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

export default API_BASE_URL; 