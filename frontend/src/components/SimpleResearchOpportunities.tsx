import React, { useState, useEffect, useCallback } from "react";
import {
  Container,
  Typography,
  Box,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Paper,
  Switch,
  FormControlLabel,
  Button,
  Chip,
  Pagination,
} from "@mui/material";
import {
  Search as SearchIcon,
  AutoAwesome as AIIcon,
  Clear as ClearIcon,
} from "@mui/icons-material";
import { apiService, Opportunity, LLMSearchResponse } from "../services/api";
import OpportunityCard from "./OpportunityCard";

// Simple markdown renderer for basic formatting
const MarkdownText: React.FC<{ children: string }> = ({ children }) => {
  const renderMarkdown = (text: string) => {
    if (!text) return text;

    // Split text by markdown patterns while preserving the patterns
    const parts = text.split(/(\*\*.*?\*\*|\*.*?\*)/g);

    return parts.map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        // Bold text
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      } else if (part.startsWith("*") && part.endsWith("*")) {
        // Italic text
        return <em key={index}>{part.slice(1, -1)}</em>;
      } else {
        // Regular text
        return part;
      }
    });
  };

  return <>{renderMarkdown(children)}</>;
};

const SimpleResearchOpportunities: React.FC = () => {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [deadlineFilter, setDeadlineFilter] = useState("");
  const [useAISearch, setUseAISearch] = useState(false);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [llmSearchResult, setLlmSearchResult] =
    useState<LLMSearchResponse | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const itemsPerPage = 50;

  // Search results cache (for pagination through search results)
  const [allSearchResults, setAllSearchResults] = useState<Opportunity[]>([]);
  const [isSearchMode, setIsSearchMode] = useState(false);

  // Available filter options (loaded from first page)
  const [availableDepartments, setAvailableDepartments] = useState<string[]>(
    []
  );
  const [availableTags, setAvailableTags] = useState<string[]>([]);

  const loadFilterOptions = useCallback(async () => {
    try {
      // Load a larger sample to get all available filter options
      const result = await apiService.getOpportunities({
        limit: 1000,
        include_inactive: false,
      });

      const departments = Array.from(
        new Set(
          (result.opportunities || [])
            .map((opp) => opp.department)
            .filter((dept): dept is string => Boolean(dept))
        )
      ).sort();

      const tags = Array.from(
        new Set(
          (result.opportunities || [])
            .map((opp) => opp.category)
            .filter((tag): tag is string => Boolean(tag))
        )
      ).sort();

      setAvailableDepartments(departments);
      setAvailableTags(tags);
    } catch (err) {
      console.error("Error loading filter options:", err);
    }
  }, []);

  const loadOpportunities = useCallback(
    async (resetPage = false) => {
      try {
        setLoading(true);
        setError(null);

        const pageToLoad = resetPage ? 1 : currentPage;
        const skip = (pageToLoad - 1) * itemsPerPage;

        // Get total count from stats endpoint
        const [opportunitiesResult, statsResult] = await Promise.all([
          apiService.getOpportunities({
            skip,
            limit: itemsPerPage,
            include_inactive: false,
          }),
          apiService.getStats(),
        ]);

        // Handle both array and paginated response formats
        const opportunities = Array.isArray(opportunitiesResult)
          ? opportunitiesResult
          : opportunitiesResult.opportunities || [];

        setOpportunities(opportunities);
        setTotalItems(statsResult.total_opportunities);
        setTotalPages(
          Math.ceil(statsResult.total_opportunities / itemsPerPage)
        );

        if (resetPage) {
          setCurrentPage(1);
        }

        // Load filter options from a larger sample if this is the first load
        if (
          currentPage === 1 &&
          (!availableDepartments.length || !availableTags.length)
        ) {
          loadFilterOptions();
        }
      } catch (err) {
        console.error("Error loading opportunities:", err);
        setError("Failed to load opportunities. Please try again later.");
        setOpportunities([]);
      } finally {
        setLoading(false);
      }
    },
    [
      currentPage,
      availableDepartments.length,
      availableTags.length,
      itemsPerPage,
      loadFilterOptions,
    ]
  );

  useEffect(() => {
    if (isSearchMode) {
      // Handle pagination for search results
      const startIndex = (currentPage - 1) * itemsPerPage;
      const endIndex = startIndex + itemsPerPage;
      const paginatedResults = allSearchResults.slice(startIndex, endIndex);
      setOpportunities(paginatedResults);
    } else {
      // Handle pagination for regular browsing
      loadOpportunities();
    }
  }, [currentPage, isSearchMode, allSearchResults, loadOpportunities]);

  const handleSearch = async () => {
    if (
      !searchTerm.trim() &&
      !departmentFilter &&
      !tagFilter &&
      !deadlineFilter
    ) {
      // No filters applied, exit search mode and load regular paginated results
      setIsSearchMode(false);
      setAllSearchResults([]);
      setCurrentPage(1);
      loadOpportunities(true);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (useAISearch && searchTerm.trim()) {
        // Use LLM RAG search - analyzes all opportunities
        setIsGeneratingSummary(true);

        const result: LLMSearchResponse = await apiService.llmSearch({
          query: searchTerm,
          limit: 1000, // Analyzes all opportunities, returns top 1000 ranked results
          include_inactive: false,
        });

        setIsGeneratingSummary(false);
        setLlmSearchResult(result); // Store the full LLM response

        let filteredResults = result.opportunities || [];

        // Apply additional filters to AI search results
        if (departmentFilter || tagFilter || deadlineFilter) {
          filteredResults = filteredResults.filter((opp) => {
            const matchesDepartment =
              !departmentFilter || opp.department === departmentFilter;
            const matchesTag = !tagFilter || opp.category === tagFilter;
            const matchesDeadline =
              !deadlineFilter ||
              (opp.deadline &&
                new Date(opp.deadline) >= new Date(deadlineFilter));
            return matchesDepartment && matchesTag && matchesDeadline;
          });
        }

        // Enter search mode and cache all results
        setIsSearchMode(true);
        setAllSearchResults(filteredResults);
        setTotalItems(filteredResults.length);
        setTotalPages(Math.ceil(filteredResults.length / itemsPerPage));
        setCurrentPage(1);

        // Show first page of results
        const paginatedResults = filteredResults.slice(0, itemsPerPage);
        setOpportunities(paginatedResults);
      } else {
        // Use regular search with filters - searches entire database
        const searchParams: any = {
          skip: 0,
          limit: 10000, // Get all results first
          include_inactive: false,
        };

        if (searchTerm.trim()) {
          searchParams.search = searchTerm;
        }

        const result = await apiService.getOpportunities(searchParams);

        // Handle both array and paginated response formats
        const allOpportunities = Array.isArray(result)
          ? result
          : result.opportunities || [];

        let filteredResults = allOpportunities;

        // Apply filters
        if (departmentFilter || tagFilter || deadlineFilter) {
          filteredResults = filteredResults.filter((opp) => {
            const matchesDepartment =
              !departmentFilter || opp.department === departmentFilter;
            const matchesTag = !tagFilter || opp.category === tagFilter;
            const matchesDeadline =
              !deadlineFilter ||
              (opp.deadline &&
                new Date(opp.deadline) >= new Date(deadlineFilter));
            return matchesDepartment && matchesTag && matchesDeadline;
          });
        }

        // Enter search mode and cache all results
        setIsSearchMode(true);
        setAllSearchResults(filteredResults);
        setTotalItems(filteredResults.length);
        setTotalPages(Math.ceil(filteredResults.length / itemsPerPage));
        setCurrentPage(1);

        // Show first page of results
        const paginatedResults = filteredResults.slice(0, itemsPerPage);
        setOpportunities(paginatedResults);
      }
    } catch (err) {
      console.error("Error searching opportunities:", err);
      setError(
        `${useAISearch ? "AI" : "Text"} search failed. Please try again.`
      );
      setOpportunities([]);
      setTotalItems(0);
      setTotalPages(0);
      setIsSearchMode(false);
      setAllSearchResults([]);
      setIsGeneratingSummary(false);
      setLlmSearchResult(null); // Clear LLM result on error
    } finally {
      setLoading(false);
    }
  };

  const handleClearSearch = () => {
    setSearchTerm("");
    setDepartmentFilter("");
    setTagFilter("");
    setDeadlineFilter("");
    setCurrentPage(1);
    setIsSearchMode(false);
    setAllSearchResults([]);
    setIsGeneratingSummary(false);
    setLlmSearchResult(null); // Clear LLM result on clear
    loadOpportunities(true);
  };

  const handlePageChange = (
    _event: React.ChangeEvent<unknown>,
    page: number
  ) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (loading && currentPage === 1) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, textAlign: "center" }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 2 }}>
          {isGeneratingSummary
            ? "AI is analyzing opportunities and generating insights..."
            : useAISearch && searchTerm
              ? "AI is searching..."
              : "Loading opportunities..."}
        </Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Research Opportunities
      </Typography>

      {/* Search and Filter Controls */}
      <Paper elevation={1} sx={{ p: 3, mb: 4 }}>
        {/* Search Toggle */}
        <Box sx={{ mb: 3, display: "flex", alignItems: "center", gap: 2 }}>
          <FormControlLabel
            control={
              <Switch
                checked={useAISearch}
                onChange={(e) => setUseAISearch(e.target.checked)}
                color="primary"
              />
            }
            label={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                {useAISearch ? <AIIcon /> : <SearchIcon />}
                {useAISearch ? "AI RAG Search" : "Simple Text Search"}
              </Box>
            }
          />
          <Chip
            label={
              useAISearch
                ? "Intelligent semantic search"
                : "Basic keyword matching"
            }
            size="small"
            color={useAISearch ? "secondary" : "default"}
            variant="outlined"
          />
        </Box>

        {/* Search Input */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label={
                useAISearch
                  ? "Ask AI about research opportunities"
                  : "Search opportunities"
              }
              placeholder={
                useAISearch
                  ? "e.g., 'machine learning projects for undergraduates'"
                  : "e.g., 'machine learning', 'biology'"
              }
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === "Enter") {
                  handleSearch();
                }
              }}
              InputProps={{
                startAdornment: useAISearch ? (
                  <AIIcon sx={{ mr: 1, color: "action.active" }} />
                ) : (
                  <SearchIcon sx={{ mr: 1, color: "action.active" }} />
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Box sx={{ display: "flex", gap: 1 }}>
              <Button
                variant="contained"
                onClick={handleSearch}
                disabled={loading}
                sx={{ minWidth: 100 }}
              >
                Search
              </Button>
              <Button
                variant="outlined"
                onClick={handleClearSearch}
                startIcon={<ClearIcon />}
              >
                Clear
              </Button>
            </Box>
          </Grid>
        </Grid>

        {/* Filters */}
        <Grid container spacing={3} sx={{ mt: 1 }}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Department</InputLabel>
              <Select
                value={departmentFilter}
                label="Department"
                onChange={(e) => setDepartmentFilter(e.target.value)}
              >
                <MenuItem value="">All Departments</MenuItem>
                {availableDepartments.map((dept) => (
                  <MenuItem key={dept} value={dept}>
                    {dept}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Tags</InputLabel>
              <Select
                value={tagFilter}
                label="Tags"
                onChange={(e) => setTagFilter(e.target.value)}
              >
                <MenuItem value="">All Tags</MenuItem>
                {availableTags.map((tag) => (
                  <MenuItem key={tag} value={tag}>
                    {tag}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Deadline After"
              type="date"
              value={deadlineFilter}
              onChange={(e) => setDeadlineFilter(e.target.value)}
              InputLabelProps={{
                shrink: true,
              }}
            />
          </Grid>
        </Grid>
      </Paper>

      {/* AI Search Summary */}
      {(llmSearchResult || isGeneratingSummary) && useAISearch && (
        <Paper
          elevation={3}
          sx={{
            p: 4,
            mb: 4,
            background: "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
            border: "1px solid #e3f2fd",
          }}
        >
          <Box
            sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 2 }}
          >
            <AIIcon sx={{ color: "primary.main", fontSize: 28, mt: 0.5 }} />
            <Box sx={{ flex: 1 }}>
              <Typography
                variant="h6"
                gutterBottom
                sx={{ color: "primary.main", fontWeight: "bold" }}
              >
                AI Search Summary
              </Typography>

              {isGeneratingSummary ? (
                <Box
                  sx={{ display: "flex", alignItems: "center", gap: 2, py: 2 }}
                >
                  <CircularProgress size={24} />
                  <Typography
                    variant="body1"
                    sx={{ color: "text.secondary", fontStyle: "italic" }}
                  >
                    AI is analyzing your search and generating a personalized
                    summary...
                  </Typography>
                </Box>
              ) : llmSearchResult ? (
                <>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    <strong>Processing Time:</strong>{" "}
                    {llmSearchResult.processing_time.toFixed(2)}s
                  </Typography>
                  <Typography
                    variant="body1"
                    sx={{ lineHeight: 1.7, color: "text.primary", mb: 2 }}
                  >
                    <strong>AI Explanation:</strong>{" "}
                    <MarkdownText>
                      {llmSearchResult.ai_explanation}
                    </MarkdownText>
                  </Typography>
                  <Chip
                    label={`${llmSearchResult.total_found} results found`}
                    color="primary"
                    size="small"
                  />
                </>
              ) : null}
            </Box>
          </Box>

          {!isGeneratingSummary && llmSearchResult && (
            <Box
              sx={{
                mt: 3,
                pt: 2,
                borderTop: "1px solid rgba(0,0,0,0.1)",
                display: "flex",
                alignItems: "center",
                gap: 1,
                flexWrap: "wrap",
              }}
            >
              <Chip
                icon={<AIIcon />}
                label="AI-Powered Search"
                color="primary"
                variant="outlined"
                size="small"
              />
              <Typography variant="caption" color="text.secondary">
                Results analyzed and summarized by AI for: "{searchTerm}"
              </Typography>
            </Box>
          )}
        </Paper>
      )}

      {/* Results Summary */}
      <Box
        sx={{
          mb: 3,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box>
          <Typography variant="h6">
            {useAISearch && searchTerm && isSearchMode
              ? `${totalItems} AI-curated opportunities found`
              : `${totalItems} opportunities found`}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Showing page {currentPage} of {totalPages} ({opportunities.length}{" "}
            items on this page)
          </Typography>
          {(searchTerm || departmentFilter || tagFilter || deadlineFilter) && (
            <Typography variant="body2" color="text.secondary">
              {searchTerm && `Search: "${searchTerm}" `}
              {departmentFilter && `Department: ${departmentFilter} `}
              {tagFilter && `Tag: ${tagFilter} `}
              {deadlineFilter && `Deadline after: ${deadlineFilter}`}
            </Typography>
          )}
        </Box>

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <Pagination
            count={totalPages}
            page={currentPage}
            onChange={handlePageChange}
            color="primary"
            showFirstButton
            showLastButton
          />
        )}
      </Box>

      {/* Loading indicator for page changes */}
      {loading && currentPage > 1 && (
        <Box sx={{ display: "flex", justifyContent: "center", mb: 3 }}>
          <CircularProgress size={40} />
        </Box>
      )}

      {/* Opportunities Grid */}
      {opportunities.length === 0 && !loading ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="h6" gutterBottom>
            No opportunities found
          </Typography>
          <Typography color="text.secondary">
            Try adjusting your search criteria or check back later for new
            opportunities.
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {opportunities.map((opportunity) => (
            <Grid item xs={12} sm={6} lg={4} key={opportunity.id}>
              <OpportunityCard opportunity={opportunity} />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Bottom Pagination */}
      {totalPages > 1 && !loading && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
          <Pagination
            count={totalPages}
            page={currentPage}
            onChange={handlePageChange}
            color="primary"
            showFirstButton
            showLastButton
            size="large"
          />
        </Box>
      )}
    </Container>
  );
};

export default SimpleResearchOpportunities;
