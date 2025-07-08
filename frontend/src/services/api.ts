import axios from 'axios';

// Dynamic API base URL that works both locally and in production
const getApiBaseUrl = () => {
  // In production (GitHub Pages), use the working AWS API endpoint
  if (process.env.NODE_ENV === 'production') {
    // Updated URL to new backend deployment with /dev stage
    return 'https://umi2dnhsp2.execute-api.us-west-2.amazonaws.com/dev';  // New backend endpoint
  }
  // If we're in development and on localhost, use localhost
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  // Otherwise, use the same host as the frontend
  return '';  // Use relative paths for same-host deployment
};

const API_BASE_URL = getApiBaseUrl();

// API Key for authentication (should be environment variable in production)
const API_KEY = process.env.REACT_APP_API_KEY || 'dev-api-key-change-in-production';

// Create axios instance with enhanced timeout for LLM operations
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for LLM operations
});

// Add request interceptor for debugging and authentication
api.interceptors.request.use(
  (config) => {
    // Add API key header for authentication
    config.headers['X-API-Key'] = API_KEY;
    
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    console.log('Headers:', config.headers);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      console.error('Authentication failed: Invalid API key');
    } else if (error.response?.status === 403) {
      console.error('Access forbidden: Origin not allowed');
    } else if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK') {
      console.error(`Backend API connection failed. Trying to connect to: ${API_BASE_URL}`);
      console.error('Make sure the backend server is running with: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000');
    }
    return Promise.reject(error);
  }
);

// Enhanced interfaces
export interface Opportunity {
  id: number;
  title: string;
  description?: string;
  department?: string;
  deadline?: string;
  location?: string;
  requirements?: string;
  eligibility_requirements?: string;
  contact_email?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  scraped_at?: string;
  // New fields from actual API response
  opportunity_type?: string;
  tags?: string[];
  source_url?: string;
  application_url?: string;
  funding_amount?: string;
  scraper_used?: string;
  llm_parsed?: boolean;
  parsing_confidence?: number;
  llm_error?: string;
  processed_at?: string;
  // Computed fields for backward compatibility
  category?: string;
  url?: string;
}

export interface PaginatedOpportunities {
  opportunities: Opportunity[];
  total: number;
  skip: number;
  limit: number;
}

export interface LLMSearchRequest {
  query: string;
  limit?: number;
  include_inactive?: boolean;
}

export interface LLMSearchResponse {
  opportunities: Opportunity[];
  total_found: number;
  ai_explanation: string;
  search_query: string;
  processing_time: number;
}

export interface AllPagesSearchRequest {
  search_term?: string;
  category?: string;
  deadline_after?: string;
  deadline_before?: string;
  include_inactive?: boolean;
  limit?: number;
}

export interface AllPagesSearchResponse {
  opportunities: Opportunity[];
  total_found: number;
  search_params: {
    search_term?: string;
    category?: string;
    deadline_after?: string;
    deadline_before?: string;
    include_inactive?: boolean;
    limit?: number;
  };
  processing_time: number;
}

export interface ScrapingResponse {
  message: string;
  total_scraped: number;
  new_opportunities: number;
  updated_opportunities: number;
  processing_time: number;
  errors: string[];
}

export interface OpportunityStats {
  total_opportunities: number;
  active_opportunities: number;
  inactive_opportunities: number;
  recent_opportunities: number;
  upcoming_deadlines: number;
  categories: Array<{
    category: string;
    count: number;
  }>;
  last_updated: string;
}

class ApiService {
  // Transform backend opportunity response to frontend format
  private transformOpportunity(backendOpp: any): Opportunity {
    return {
      ...backendOpp,
      // Map opportunity_type to category for backward compatibility
      category: backendOpp.opportunity_type || backendOpp.category,
      // Map source_url or application_url to url for backward compatibility
      url: backendOpp.application_url || backendOpp.source_url || backendOpp.url,
      // Ensure tags is always an array
      tags: Array.isArray(backendOpp.tags) ? backendOpp.tags : [],
      // Map scraped_at to created_at and updated_at for backward compatibility
      created_at: backendOpp.created_at || backendOpp.scraped_at,
      updated_at: backendOpp.updated_at || backendOpp.scraped_at,
    };
  }

  // Transform array of opportunities
  private transformOpportunities(opportunities: any[]): Opportunity[] {
    return opportunities.map(opp => this.transformOpportunity(opp));
  }

  // Enhanced get opportunities with increased pagination
  async getOpportunities(params?: {
    skip?: number;
    limit?: number; // Now supports up to 10,000
    search?: string;
    category?: string;
    deadline_after?: string;
    deadline_before?: string;
    sort_by?: string;
    sort_order?: string;
    include_inactive?: boolean;
  }): Promise<PaginatedOpportunities> {
    const response = await api.get('/api/opportunities', { params });
    
    // Handle case where API returns direct array or paginated response
    if (Array.isArray(response.data)) {
      return {
        opportunities: this.transformOpportunities(response.data),
        total: response.data.length,
        skip: 0,
        limit: response.data.length
      };
    }
    
    return {
      ...response.data,
      opportunities: this.transformOpportunities(response.data.opportunities || [])
    };
  }

  async getOpportunity(id: number): Promise<Opportunity> {
    const response = await api.get(`/api/opportunities/${id}`);
    return this.transformOpportunity(response.data);
  }

  async createOpportunity(opportunity: Partial<Opportunity>): Promise<Opportunity> {
    const response = await api.post('/api/opportunities', opportunity);
    return this.transformOpportunity(response.data);
  }

  async updateOpportunity(id: number, opportunity: Partial<Opportunity>): Promise<Opportunity> {
    const response = await api.put(`/api/opportunities/${id}`, opportunity);
    return this.transformOpportunity(response.data);
  }

  async deleteOpportunity(id: number): Promise<void> {
    await api.delete(`/api/opportunities/${id}`);
  }

  // New LLM-powered search (RAG)
  async llmSearch(request: LLMSearchRequest): Promise<LLMSearchResponse> {
    // Use query parameters instead of POST body since backend expects URL params
    const params = new URLSearchParams();
    params.append('query', request.query);
    if (request.limit) {
      params.append('limit', request.limit.toString());
    }
    if (request.include_inactive !== undefined) {
      params.append('use_vector_search', 'false'); // Backend param name
    }
    
    const response = await api.post(`/api/opportunities/search/llm?${params.toString()}`);
    
    // The backend returns different field names, so we need to transform them
    const backendData = response.data;
    return {
      opportunities: this.transformOpportunities(backendData.results || []),
      total_found: backendData.total_found || 0,
      ai_explanation: backendData.ai_explanation || "AI analysis completed",
      search_query: backendData.query || request.query,
      processing_time: backendData.processing_time || 0
    };
  }

  // New all-pages search
  async searchAllPages(request: AllPagesSearchRequest): Promise<AllPagesSearchResponse> {
    const response = await api.post('/api/opportunities/search/all-pages', request);
    return {
      ...response.data,
      opportunities: this.transformOpportunities(response.data.opportunities || [])
    };
  }

  // New scraping endpoints
  async startScraping(): Promise<ScrapingResponse> {
    const response = await api.post('/api/opportunities/scrape/start');
    return response.data;
  }

  async startEnhancedScraping(): Promise<ScrapingResponse> {
    const response = await api.post('/api/opportunities/scrape-enhanced');
    return response.data;
  }

  // Enhanced statistics
  async getStats(): Promise<OpportunityStats> {
    const response = await api.get('/api/opportunities/stats');
    return response.data;
  }

  // Admin database management endpoints
  async deleteAllOpportunities(confirmation: string): Promise<{ message: string; deleted_count: number }> {
    const response = await api.delete('/api/opportunities/admin/delete-all', {
      data: { confirmation }
    });
    return response.data;
  }

  async deleteInactiveOpportunities(): Promise<{ message: string; deleted_count: number }> {
    const response = await api.delete('/api/opportunities/admin/delete-inactive');
    return response.data;
  }

  async bulkDeactivateOpportunities(opportunity_ids: number[]): Promise<{ 
    message: string; 
    updated_count: number; 
    opportunity_ids: number[] 
  }> {
    const response = await api.post('/api/opportunities/admin/bulk-deactivate', {
      opportunity_ids
    });
    return response.data;
  }

  async resetDatabase(confirmation: string): Promise<{ message: string; deleted_count: number }> {
    const response = await api.post('/api/opportunities/admin/reset-database', {
      confirmation
    });
    return response.data;
  }
}

export const apiService = new ApiService(); 