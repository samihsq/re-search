import React, { useState, useEffect, useCallback, useRef } from "react";
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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Skeleton,
  Card,
  CardContent,
  Autocomplete,
} from "@mui/material";
import {
  Search as SearchIcon,
  AutoAwesome as AIIcon,
  Clear as ClearIcon,
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  Analytics as AnalyticsIcon,
  AccessTime as AccessTimeIcon,
  School as SchoolIcon,
} from "@mui/icons-material";
import {
  apiService,
  Opportunity,
  LLMSearchResponse,
  OpportunityStats,
} from "../services/api";
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

  // Helper function to safely parse dates for comparison
  const isValidDate = (dateString?: string): boolean => {
    if (!dateString) return false;
    const date = new Date(dateString);
    return !isNaN(date.getTime());
  };

  const compareDates = (
    dateString1: string | undefined,
    dateString2: string | undefined,
    operator: ">=" | "<="
  ): boolean => {
    if (!dateString1 || !dateString2) return false;
    if (!isValidDate(dateString1) || !isValidDate(dateString2)) return false;

    const date1 = new Date(dateString1);
    const date2 = new Date(dateString2);

    return operator === ">=" ? date1 >= date2 : date1 <= date2;
  };
  const [isSearching, setIsSearching] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const cooldownTimer = useRef<NodeJS.Timeout>();
  const [error, setError] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [submittedSearchTerm, setSubmittedSearchTerm] = useState(""); // For displaying the searched term
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [deadlineFilter, setDeadlineFilter] = useState("");
  const [deadlineBeforeFilter, setDeadlineBeforeFilter] = useState("");
  const [useAISearch, setUseAISearch] = useState(false);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [llmSearchResult, setLlmSearchResult] =
    useState<LLMSearchResponse | null>(null);
  const [stats, setStats] = useState<OpportunityStats | null>(null);

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
  const [availableTypes, setAvailableTypes] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<string[]>([]);

  const loadFilterOptions = useCallback(async () => {
    try {
      // Load a larger sample to get all available filter options
      const result = await apiService.getOpportunities({
        limit: 1000,
        include_inactive: false,
      });

      // Guard against unexpected API responses
      if (!result || !result.opportunities) {
        console.error(
          "loadFilterOptions: API did not return a valid result.",
          result
        );
        setAvailableDepartments([]);
        setAvailableTags([]);
        return;
      }

      const departments = Array.from(
        new Set(
          (result.opportunities || [])
            .map((opp) => opp.department)
            .filter((dept): dept is string => Boolean(dept))
        )
      ).sort();

      const types = Array.from(
        new Set(
          (result.opportunities || [])
            .map((opp) => opp.category)
            .filter((tag): tag is string => Boolean(tag))
        )
      ).sort();

      const tags = Array.from(
        new Set(
          (result.opportunities || [])
            .flatMap((opp) => opp.tags || [])
            .filter((tag): tag is string => Boolean(tag))
        )
      ).sort();

      setAvailableDepartments(departments);
      setAvailableTypes(types);
      setAvailableTags(tags);
    } catch (err) {
      console.error("Error loading filter options:", err);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const statsData = await apiService.getOpportunityStats();
      setStats(statsData);
    } catch (err) {
      console.error("Load stats error:", err);
    }
  }, []);

  // Fetch filter options once on component mount
  useEffect(() => {
    loadFilterOptions();
    loadStats();
  }, [loadFilterOptions, loadStats]);

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

        // Guard against unexpected API responses
        if (!opportunitiesResult) {
          console.error(
            "loadOpportunities: getOpportunities did not return a result.",
            opportunitiesResult
          );
        }
        if (!statsResult) {
          console.error(
            "loadOpportunities: getStats did not return a result.",
            statsResult
          );
        }

        // Handle both array and paginated response formats safely
        const opportunities = Array.isArray(opportunitiesResult)
          ? opportunitiesResult
          : opportunitiesResult?.opportunities || [];

        setOpportunities(opportunities);
        setTotalItems(statsResult?.total_active || 0);
        setTotalPages(
          Math.ceil((statsResult?.total_active || 0) / itemsPerPage)
        );

        if (resetPage) {
          setCurrentPage(1);
        }
      } catch (err) {
        console.error("Error loading opportunities:", err);
        setError("Failed to load opportunities. Please try again later.");
        setOpportunities([]);
      } finally {
        setLoading(false);
      }
    },
    [currentPage, itemsPerPage]
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

  // Clear timer on component unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (cooldownTimer.current) {
        clearInterval(cooldownTimer.current);
      }
    };
  }, []);

  const handleSearch = async () => {
    if (isSearching || cooldown > 0) {
      return;
    }
    const wasAISearch = useAISearch; // Capture state at the moment of search
    const currentSearchTerm = searchInputRef.current?.value || "";
    if (
      !currentSearchTerm.trim() &&
      !departmentFilter &&
      selectedTypes.length === 0 &&
      selectedTags.length === 0 &&
      !deadlineFilter &&
      !deadlineBeforeFilter
    ) {
      // No filters applied, exit search mode and load regular paginated result
      setIsSearchMode(false);
      setAllSearchResults([]);
      setCurrentPage(1);
      loadOpportunities(true);
      return;
    }

    setSubmittedSearchTerm(currentSearchTerm); // Set the submitted term only on search

    try {
      setIsSearching(true);
      setError(null);
      setLlmSearchResult(null);

      // Consolidate all search parameters
      const searchParams: any = {
        search: currentSearchTerm.trim(),
        department: departmentFilter,
        deadline_after: deadlineFilter,
        deadline_before: deadlineBeforeFilter,
        category: selectedTypes.join(","),
        tags: selectedTags.join(","),
        limit: 5000, // Fetch all matching results up to a high limit
      };

      if (useAISearch) {
        // Use LLM RAG search - analyzes all opportunities
        setIsGeneratingSummary(true);

        const result: LLMSearchResponse = await apiService.llmSearch({
          query: currentSearchTerm,
          limit: 1000, // Analyzes all opportunities, returns top 1000 ranked results
          include_inactive: false,
        });

        setIsGeneratingSummary(false);
        setLlmSearchResult(result); // Store the full LLM response

        let filteredResults = result.opportunities || [];

        // Apply additional filters to AI search results
        if (
          departmentFilter ||
          selectedTypes.length > 0 ||
          selectedTags.length > 0 ||
          deadlineFilter ||
          deadlineBeforeFilter
        ) {
          // Further client-side filtering
          // This is applied AFTER getting results from AI search
          filteredResults = filteredResults.filter((opp) => {
            const matchesDepartment =
              !departmentFilter || opp.department === departmentFilter;
            const matchesTypes =
              selectedTypes.length === 0 ||
              (opp.category && selectedTypes.includes(opp.category));
            const matchesTags =
              selectedTags.length === 0 ||
              (opp.tags && opp.tags.some((tag) => selectedTags.includes(tag)));
            const matchesDeadline =
              (!deadlineFilter ||
                compareDates(opp.deadline, deadlineFilter, ">=")) &&
              (!deadlineBeforeFilter ||
                compareDates(opp.deadline, deadlineBeforeFilter, "<="));
            return (
              matchesDepartment &&
              matchesTypes &&
              matchesTags &&
              matchesDeadline
            );
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
        const result = await apiService.getOpportunities(searchParams);

        // Handle both array and paginated response formats
        const allOpportunities = Array.isArray(result)
          ? result
          : result.opportunities || [];

        let filteredResults = allOpportunities;

        // Apply filters
        if (
          departmentFilter ||
          selectedTypes.length > 0 ||
          selectedTags.length > 0 ||
          deadlineFilter ||
          deadlineBeforeFilter
        ) {
          filteredResults = result.opportunities.filter((opp) => {
            const matchesDepartment =
              !departmentFilter || opp.department === departmentFilter;
            const matchesTypes =
              selectedTypes.length === 0 ||
              (opp.category && selectedTypes.includes(opp.category));
            const matchesTags =
              selectedTags.length === 0 ||
              (opp.tags && opp.tags.some((tag) => selectedTags.includes(tag)));
            const matchesDeadline =
              (!deadlineFilter ||
                compareDates(opp.deadline, deadlineFilter, ">=")) &&
              (!deadlineBeforeFilter ||
                compareDates(opp.deadline, deadlineBeforeFilter, "<="));
            return (
              matchesDepartment &&
              matchesTypes &&
              matchesTags &&
              matchesDeadline
            );
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
      setIsSearching(false);
      if (wasAISearch) {
        setCooldown(10);
        cooldownTimer.current = setInterval(() => {
          setCooldown((prev) => {
            if (prev <= 1) {
              clearInterval(cooldownTimer.current!);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      }
    }
  };

  const handleClearSearch = () => {
    setSubmittedSearchTerm(""); // Clear submitted term
    setDepartmentFilter("");
    setSelectedTypes([]);
    setSelectedTags([]);
    setDeadlineFilter("");
    setDeadlineBeforeFilter("");
    setUseAISearch(false);
    setCurrentPage(1);
    setIsSearchMode(false);
    setAllSearchResults([]);
    setIsGeneratingSummary(false);
    setLlmSearchResult(null); // Clear LLM result on clear
    if (searchInputRef.current) {
      searchInputRef.current.value = "";
    }
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
            : useAISearch && searchInputRef.current?.value
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
      {/* <Typography variant="h4" component="h1" gutterBottom>
        Research Opportunities
      </Typography> */}

      {/* Statistics Cards */}
      {stats ? (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={6} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Box>
                    <Typography color="text.secondary" gutterBottom>
                      Total Opportunities
                    </Typography>
                    <Typography variant="h4">{stats.total_active}</Typography>
                  </Box>
                  <TrendingUpIcon color="primary" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={6} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Box>
                    <Typography color="text.secondary" gutterBottom>
                      Active Opportunities
                    </Typography>
                    <Typography variant="h4" color="success.main">
                      {stats.status_breakdown?.active || 0}
                    </Typography>
                  </Box>
                  <AnalyticsIcon color="success" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={6} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Box>
                    <Typography color="text.secondary" gutterBottom>
                      Recent (7 days)
                    </Typography>
                    <Typography variant="h4" color="info.main">
                      {stats.recent_new_opportunities}
                    </Typography>
                  </Box>
                  <AccessTimeIcon color="info" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={6} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Box>
                    <Typography color="text.secondary" gutterBottom>
                      Funded Opportunities
                    </Typography>
                    <Typography variant="h4" color="warning.main">
                      {stats.funded_opportunities}
                    </Typography>
                  </Box>
                  <SchoolIcon color="warning" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      ) : (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {[...Array(4)].map((_, index) => (
            <Grid item xs={6} sm={6} md={3} key={index}>
              <Skeleton variant="rectangular" height={120} />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Search and Filter Controls */}
      <Paper
        elevation={1}
        sx={{ p: 3, borderRadius: "16px", mb: 4, overflow: "hidden" }}
      >
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={useAISearch}
                  onChange={(e) => setUseAISearch(e.target.checked)}
                />
              }
              label={
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  {useAISearch ? <AIIcon /> : <SearchIcon />}
                  {useAISearch ? "AI-assisted Search" : "Simple Text Search"}
                </Box>
              }
            />
          </Grid>
          <Grid item xs={12} md={8}>
            <TextField
              fullWidth
              variant="outlined"
              label={
                useAISearch
                  ? "Ask AI about research opportunities"
                  : "Search by keyword"
              }
              placeholder={
                useAISearch
                  ? "e.g., 'machine learning projects for undergraduates'"
                  : "e.g., 'biology', 'computer vision'"
              }
              inputRef={searchInputRef}
              onKeyPress={(e) => {
                if (e.key === "Enter") {
                  handleSearch();
                }
              }}
              InputProps={{
                startAdornment: (
                  <SearchIcon sx={{ mr: 1, color: "action.active" }} />
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleSearch}
              disabled={isSearching || cooldown > 0}
              sx={{ height: "56px" }}
            >
              {isSearching ? (
                <CircularProgress size={24} color="inherit" />
              ) : cooldown > 0 ? (
                `Wait (${cooldown}s)`
              ) : (
                "Search"
              )}
            </Button>
          </Grid>
          <Grid item xs={12} md={2}>
            <Button
              fullWidth
              variant="outlined"
              onClick={handleClearSearch}
              startIcon={<ClearIcon />}
              sx={{ height: "56px" }}
            >
              Clear
            </Button>
          </Grid>
        </Grid>
        <Accordion
          sx={{ mt: 2, boxShadow: "none", "&:before": { display: "none" } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Advanced Filters</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={4}>
                <Autocomplete
                  options={availableDepartments}
                  getOptionLabel={(option) => option}
                  value={departmentFilter || null}
                  onChange={(event, newValue) => {
                    setDepartmentFilter(newValue || "");
                  }}
                  renderInput={(params) => (
                    <TextField {...params} label="Department" />
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                <Autocomplete
                  multiple
                  options={availableTypes}
                  getOptionLabel={(option) => option}
                  value={selectedTypes}
                  onChange={(event, newValue) => {
                    setSelectedTypes(newValue);
                  }}
                  renderInput={(params) => (
                    <TextField {...params} label="Type" />
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                <Autocomplete
                  multiple
                  options={availableTags}
                  getOptionLabel={(option) => option}
                  value={selectedTags}
                  onChange={(event, newValue) => {
                    setSelectedTags(newValue);
                  }}
                  renderInput={(params) => (
                    <TextField {...params} label="Tags" />
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={6}>
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
              <Grid item xs={12} sm={6} md={6}>
                <TextField
                  fullWidth
                  label="Deadline Before"
                  type="date"
                  value={deadlineBeforeFilter}
                  onChange={(e) => setDeadlineBeforeFilter(e.target.value)}
                  InputLabelProps={{
                    shrink: true,
                  }}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      </Paper>

      {/* AI Search Summary */}
      {(isGeneratingSummary || (llmSearchResult && useAISearch)) && (
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
                  <MarkdownText>{llmSearchResult.ai_explanation}</MarkdownText>
                  <Box sx={{ mt: 2, mb: 2 }}></Box>
                  <Chip
                    label={`${llmSearchResult.total_found} results found`}
                    color="primary"
                    size="small"
                  />
                </>
              ) : null}
            </Box>
          </Box>
        </Paper>
      )}

      {isSearchMode && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" component="h2">
            Search Results for: "
            <span style={{ fontStyle: "italic" }}>{submittedSearchTerm}</span>"
          </Typography>
        </Box>
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
            {useAISearch && searchInputRef.current?.value && isSearchMode
              ? `${totalItems} AI-curated opportunities found`
              : `${totalItems} opportunities found`}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Showing page {currentPage} of {totalPages} ({opportunities.length}{" "}
            items on this page)
          </Typography>
          {isSearchMode && (
            <Typography variant="body2" color="text.secondary">
              <strong>Filters:</strong>{" "}
              <Chip
                label={
                  [
                    submittedSearchTerm && `Search: "${submittedSearchTerm}" `,
                    departmentFilter && `Department: ${departmentFilter} `,
                    selectedTypes.length > 0 &&
                      `Type: ${selectedTypes.join(", ")} `,
                    selectedTags.length > 0 &&
                      `Tags: ${selectedTags.join(", ")} `,
                    deadlineFilter && `Deadline after: ${deadlineFilter}`,
                    deadlineBeforeFilter &&
                      `Deadline before: ${deadlineBeforeFilter}`,
                  ]
                    .filter(Boolean)
                    .join("• ") || "None"
                }
                onDelete={handleClearSearch}
                sx={{
                  height: "auto",
                  p: 1,
                  "& .MuiChip-label": { whiteSpace: "normal" },
                }}
              />
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
